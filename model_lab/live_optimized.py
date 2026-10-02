"""Shared-memory capture, batched plate detection and independent bounded OCR.

All inference is local. JSONL preserves stage events; finalization joins them into
compatible observations plus a versioned JSON report bundle. No production alerts.
"""
import argparse
import json
import multiprocessing as mp
import os
import queue
import time
import threading
from collections import Counter, OrderedDict
from pathlib import Path

from common import ROOT, REPO, MODELS, sha256
from live_benchmark import atomic_json, load_json, utc, camera_loop
from plate_workflow import OCR_MIN_CONFIDENCE, OCR_SELECTION_POLICY
from shared_frames import SharedFrame
from encounter_store import EncounterStore, run_identity


def capture_shared_group(cameras,cfg,credentials,output,gate,deadline,stop,sample_fps,slots):
    threads=[threading.Thread(target=camera_loop,args=(c,cfg,credentials,output,gate,deadline,stop,sample_fps,slots[c['id']]),daemon=True) for c in cameras]
    for thread in threads:thread.start()
    for thread in threads:thread.join()


def percentiles(values):
    import numpy as np
    return {name: float(np.percentile(values, p)) for name, p in [('p50', 50), ('p95', 95), ('p99', 99)]} if values else {}


def ocr_worker(output, jobs, detector_done, ready, status_counter):
    import cv2
    from plate_workflow import PlateReader, Consensus
    cv2.setNumThreads(1)
    reader = PlateReader()
    # Warm the recognizer before the measurement gate opens.
    import numpy as np
    reader.read(np.full((32, 100, 3), 128, dtype=np.uint8))
    consensus = Consensus()
    store = None
    state = {'completed': 0, 'expired': 0, 'errors': 0, 'finished': False, 'repeated_candidates': []}
    ready.set()
    def publish():
        state['heartbeat_monotonic'] = time.monotonic()
        atomic_json(output/'ocr_status.json', state)
    with (output/'ocr_results.jsonl').open('w') as log:
        while True:
            try:
                job = jobs.get(timeout=.2)
            except queue.Empty:
                publish()
                if detector_done.is_set(): break
                continue
            now = time.monotonic()
            delay = (now-job['queued_monotonic'])*1000
            pixels = job.pop('pixels')
            event = dict(job, queue_wait_ms=delay)
            if delay > 8000:
                event.update(event_status='expired', completed_monotonic=now)
                state['expired'] += 1
            else:
                filename = f'evidence/{job["job_id"]}.png'
                if not cv2.imwrite(str(output/filename), pixels):
                    raise OSError('Could not persist OCR evidence')
                start = time.monotonic()
                try:
                    reading = reader.read(pixels)
                    ended = time.monotonic()
                    reading.update(track_id=job['track_id'], selected_source_sequence=job['selected_source']['sequence'],
                        selected_source=job['selected_source'], crop=filename,
                        latency_ms=(ended-start)*1000, queue_wait_ms=delay,
                        receipt_to_ocr_result_ms=(ended-job['selected_source']['receipt_monotonic'])*1000,
                        selection_reason=job['selection_reason'], job_id=job['job_id'])
                    event.update(event_status='completed', completed_monotonic=ended, reading=reading)
                    outcome = consensus.add(tuple(job['track_key']), job['selected_source']['sequence'], reading['candidate'])
                    if outcome:
                        record = dict(outcome, camera_id=job['camera_id'], key=str(job['track_key']))
                        if not any(r['key']==record['key'] and r['candidate']==record['candidate'] for r in state['repeated_candidates']):
                            state['repeated_candidates'].append(record)
                    state['completed'] += 1
                except Exception as exc:
                    event.update(event_status='error', error_type=type(exc).__name__, crop=filename,
                                 completed_monotonic=time.monotonic())
                    state['errors'] += 1
            log.write(json.dumps(event)+'\n'); log.flush()
            if event['event_status']=='completed':
                if store is None:
                    config=load_json(output/'config.json')
                    store=EncounterStore(output/'encounters.sqlite3',run_identity(config),OCR_SELECTION_POLICY)
                store.record_ocr(event)
            status_counter.value += 1
            publish()
    state['finished'] = True
    publish()
    if store is not None: store.close()


def detect(cameras, slots, output, gate, deadline, stop, ready, jobs, done, device, batch_size):
    import cv2
    import numpy as np
    import torch
    from types import SimpleNamespace
    from ultralytics import YOLO
    from ultralytics.trackers.byte_tracker import BYTETracker
    from run_pipeline import clipped_box
    from plate_workflow import BestFrames, quality
    torch.set_num_threads(1); cv2.setNumThreads(1)
    vehicle = YOLO(str(MODELS/'yolo11n.pt'))
    plate = YOLO(str(MODELS/'license-plate-finetune-v1n.pt'))
    class CameraTracker(BYTETracker):
        @staticmethod
        def reset_id(): pass
    tracker_args = SimpleNamespace(track_high_thresh=.25, track_low_thresh=.1, new_track_thresh=.25,
                                   track_buffer=2, match_thresh=.8, fuse_score=True)
    for model in (vehicle, plate):
        model.predict(np.zeros((640,640,3), np.uint8), device=device, imgsz=640, verbose=False)
    # Warm the bounded batch shape too, outside measured time.
    plate.predict([np.zeros((128,256,3), np.uint8) for _ in range(batch_size)],
                  device=device, imgsz=640, rect=False, verbose=False)
    states = {c['id']: dict.fromkeys(['processed_frames','vehicles','vehicle_roi_budget_skipped','plate_boxes',
        'quality_rejected','ocr_reads','ocr_budget_skipped','stale_frames','skipped_sample_sequences',
        'tracker_resets','rectified','two_line_reads','ocr_enqueued','ocr_queue_full','oversize_crop_skipped'], 0) for c in cameras}
    trackers, previous, last_source, epochs, last_example = {}, {}, {}, Counter(), {}
    sources = {c['id']: OrderedDict() for c in cameras}
    best = BestFrames()
    submitted = OrderedDict()
    timings, vehicle_times, plate_times, ages = [], [], [], []
    sequence = 0
    ready.set(); gate.wait()
    store=EncounterStore(output/'encounters.sqlite3',run_identity(load_json(output/'config.json')),OCR_SELECTION_POLICY)
    last_publish = 0.0
    def publish(final=False):
        nonlocal last_publish
        last_publish = time.monotonic()
        atomic_json(output/'inference_status.json', {'cameras':states, 'finished':final,
            'heartbeat_monotonic':last_publish, 'processing_ms':percentiles(timings),
            'vehicle_inference_ms':percentiles(vehicle_times), 'plate_inference_ms':percentiles(plate_times),
            'receipt_to_result_ms':percentiles(ages)})
    def enqueue(key, selection, trigger, reason):
        nonlocal sequence
        cam, session, track = key
        score, selected_sequence, pixels = selection
        source = sources[cam].get((session, selected_sequence))
        identity = (key, selected_sequence)
        if identity in submitted or source is None: return
        if pixels.nbytes > 1024*1024:
            states[cam]['oversize_crop_skipped'] += 1; return
        sequence += 1
        job = {'job_id':f'{cam}_ocr_{sequence:06d}', 'camera_id':cam, 'track_id':track, 'track_key':list(key),
               'trigger_session':trigger['session'], 'trigger_sequence':trigger['sequence'],
               'selected_source':source, 'selection_reason':reason, 'quality_score':score,
               'queued_monotonic':time.monotonic(), 'pixels':pixels}
        try:
            jobs.put_nowait(job)
            states[cam]['ocr_enqueued'] += 1
            submitted[identity] = True
            if len(submitted)>2000: submitted.popitem(last=False)
        except queue.Full:
            states[cam]['ocr_queue_full'] += 1
            states[cam]['ocr_budget_skipped'] += 1
    try:
        with (output/'detection_frames.jsonl').open('w') as log:
            while not stop.is_set() and time.monotonic()<deadline.value:
                # A healthy detector can be idle when every feed is unavailable.
                # Keep its liveness separate from the arrival of camera frames.
                if time.monotonic()-last_publish >= 1: publish()
                did_work = False
                for camera in cameras:
                    if stop.is_set() or time.monotonic()>=deadline.value: break
                    cam = camera['id']; state = states[cam]
                    sample = slots[cam].read(previous.get(cam))
                    if sample is None: continue
                    meta, image = sample
                    prev = last_source.get(cam)
                    previous[cam] = (meta['session'], meta['sequence'])
                    if prev:
                        state['skipped_sample_sequences'] += max(0, meta['sequence']-prev['sequence']-1)
                    last_source[cam] = meta
                    if time.monotonic()-meta['receipt_monotonic']>8:
                        state['stale_frames'] += 1; continue
                    sources[cam][(meta['session'], meta['sequence'])] = meta
                    if len(sources[cam])>128: sources[cam].popitem(last=False)
                    did_work = True; start = time.monotonic()
                    reset = cam not in trackers or prev['session'] != meta['session'] or (
                        prev.get('pts_s') is not None and meta.get('pts_s') is not None and not 0<meta['pts_s']-prev['pts_s']<=3)
                    if reset:
                        trackers[cam] = CameraTracker(tracker_args)
                        epochs[cam] += 1; state['tracker_resets'] += 1
                    t = time.monotonic()
                    pred = vehicle.predict(image, device=device, imgsz=640, classes=[2,3,5,7], conf=.1, verbose=False)[0]
                    boxes = pred.boxes.cpu().numpy()
                    vehicle_ms = (time.monotonic()-t)*1000
                    tracks = trackers[cam].update(boxes, image)
                    mapping = {int(track[-1]):f'{epochs[cam]}:{int(track[4])}' for track in tracks}
                    selected = [i for i,b in enumerate(boxes) if float(b.conf[0])>=.25]
                    selected.sort(key=lambda i:float(boxes[i].xywh[0,2]*boxes[i].xywh[0,3]), reverse=True)
                    state['vehicles'] += len(selected); state['vehicle_roi_budget_skipped'] += max(0,len(selected)-6)
                    record = {'camera_id':cam, 'source':meta, 'vehicles':[], 'ocr':[], 'started_monotonic':start}
                    h,w = image.shape[:2]
                    annotated = image.copy() if start-last_example.get(cam,-1e9)>=30 else None
                    rois = []
                    for idx in selected[:6]:
                        bbox = clipped_box(boxes[idx].xyxy[0], w,h); x1,y1,x2,y2 = bbox
                        if x2<=x1 or y2<=y1: continue
                        item = {'bbox':bbox, 'track_id':mapping.get(idx),
                                'observation_track_id':mapping.get(idx) or f'untracked:{meta["sequence"]}:{idx}',
                                'confidence':float(boxes[idx].conf[0]), 'plates':[]}
                        record['vehicles'].append(item)
                        rois.append((idx,item,image[y1:y2,x1:x2]))
                        if annotated is not None: cv2.rectangle(annotated,(x1,y1),(x2,y2),(70,210,80),2)
                    t = time.monotonic(); plate_batches = 0
                    for offset in range(0,len(rois),batch_size):
                        batch = rois[offset:offset+batch_size]
                        predictions = plate.predict([roi[2] for roi in batch], device=device, imgsz=640,
                                                    conf=.35, rect=False, verbose=False)
                        plate_batches += 1
                        for (idx,item,crop), prediction in zip(batch,predictions):
                            x1,y1,x2,y2 = item['bbox']
                            acceptable = []
                            for p in prediction.boxes.cpu().numpy():
                                a,b,d,e = clipped_box(p.xyxy[0], x2-x1,y2-y1)
                                if d<=a or e<=b: continue
                                pixels = crop[b:e,a:d]; q = quality(pixels)
                                if (d-a)*(e-b)>.45*(x2-x1)*(y2-y1): q['reject_reasons'].append('large_fraction_of_vehicle')
                                state['plate_boxes'] += 1
                                item['plates'].append({'bbox':[x1+a,y1+b,x1+d,y1+e],'quality':q,'confidence':float(p.conf[0])})
                                if annotated is not None: cv2.rectangle(annotated,(x1+a,y1+b),(x1+d,y1+e),(0,210,255),2)
                                if q['reject_reasons']: state['quality_rejected'] += 1
                                else: acceptable.append((q['score'],pixels))
                            # One best plate region per vehicle/frame, before frame selection.
                            if acceptable:
                                score,pixels = max(acceptable,key=lambda value:value[0])
                                key = (cam,meta['session'],item['track_id'] or f'untracked:{meta["sequence"]}:{idx}')
                                selection = best.consider(key,meta['sequence'],pixels,score,start)
                                if selection: enqueue(key,selection,meta,'best_of_distinct_frames')
                    plate_ms = (time.monotonic()-t)*1000
                    for key,selection in best.flush_camera(cam,start):
                        enqueue(key,selection,meta,'best_available_crop_after_short_encounter')
                    if annotated is not None:
                        filename=f'evidence/{cam}_frame_{meta["sequence"]}.jpg'
                        cv2.imwrite(str(output/filename),annotated)
                        record['annotated']=filename; last_example[cam]=start
                    state['processed_frames'] += 1
                    record.update(processing_ms=(time.monotonic()-start)*1000,
                        receipt_to_result_ms=(time.monotonic()-meta['receipt_monotonic'])*1000,
                        vehicle_inference_ms=vehicle_ms, plate_stage_ms=plate_ms, plate_batches=plate_batches)
                    timings.append(record['processing_ms']); ages.append(record['receipt_to_result_ms'])
                    vehicle_times.append(vehicle_ms); plate_times.append(plate_ms)
                    log.write(json.dumps(record)+'\n'); log.flush(); publish()
                    store.record_frame(record)
                if not did_work: stop.wait(.02)
            for cam,meta in last_source.items():
                for key,selection in best.flush_camera(cam,time.monotonic()+10):
                    enqueue(key,selection,meta,'final_best_crop_at_shutdown')
        publish(final=True)
    finally:
        store.close()
        # Ensure queued data reaches the OCR process before signalling end-of-input.
        jobs.close(); jobs.join_thread(); done.set()


def final_observations(output, config):
    records = [json.loads(line) for line in (output/'detection_frames.jsonl').read_text().splitlines()]
    events = [json.loads(line) for line in (output/'ocr_results.jsonl').read_text().splitlines()]
    frames = {(r['camera_id'],r['source']['session'],r['source']['sequence']):r for r in records}
    unmatched = 0
    for event in events:
        if event['event_status']!='completed': continue
        frame = frames.get((event['camera_id'],event['trigger_session'],event['trigger_sequence']))
        if frame is None: unmatched += 1; continue
        frame['ocr'].append(event['reading'])
    with (output/'observations.jsonl').open('w') as log:
        for record in records: log.write(json.dumps(record)+'\n')
    inf = load_json(output/'inference_status.json', {})
    states = inf.get('cameras', {})
    for state in states.values():
        state.update(ocr_reads=0, rectified=0, two_line_reads=0)
    for event in events:
        if event['event_status']=='completed':
            reading = event['reading']; state = states[event['camera_id']]
            state['ocr_reads'] += 1
            state['rectified'] += int(reading['geometry']['applied'])
            state['two_line_reads'] += int(reading['layout']['layout']=='two_lines')
    completed = [e for e in events if e['event_status']=='completed']
    inf['ocr_ms'] = percentiles([e['reading']['latency_ms'] for e in completed])
    inf['ocr_queue_wait_ms'] = percentiles([e['queue_wait_ms'] for e in completed])
    inf['selected_crop_receipt_to_ocr_result_ms'] = percentiles([e['reading']['receipt_to_ocr_result_ms'] for e in completed])
    inf['ocr_event_counts'] = dict(Counter(e['event_status'] for e in events))
    inf['unmatched_ocr_results'] = unmatched
    inf['ocr_completed_after_capture_deadline'] = sum(e['completed_monotonic']>config['started_monotonic']+config['requested_seconds'] for e in completed)
    inf['repeated_candidates'] = load_json(output/'ocr_status.json',{}).get('repeated_candidates',[])
    inf['ocr_unaccounted_jobs'] = sum(s.get('ocr_enqueued',0) for s in states.values())-len(events)
    atomic_json(output/'inference_status.json',inf)
    return inf


def main():
    import requests
    import psutil
    import re
    import shutil
    from dotenv import load_dotenv
    from urllib.parse import urlsplit
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--sample-fps',type=float,default=2)
    parser.add_argument('--device',default='mps')
    parser.add_argument('--plate-batch',type=int,default=4)
    parser.add_argument('--output',required=True,type=Path)
    camera_selection=parser.add_mutually_exclusive_group(required=True)
    camera_selection.add_argument('--cameras',nargs='+')
    camera_selection.add_argument('--all-cameras',action='store_true')
    parser.add_argument('--expected-cameras',type=int)
    parser.add_argument('--capture-group-size',type=int,default=1)
    parser.add_argument('--max-frame-bytes',type=int,default=3840*2160*3)
    parser.add_argument('--watchlist',type=Path,help='Optional local watchlist JSON; records review alerts only, sends no notifications')
    args=parser.parse_args()
    if args.seconds<=0 or args.sample_fps<=0 or not 1<=args.plate_batch<=6: parser.error('Invalid duration, FPS or batch')
    if not 1<=args.capture_group_size<=5 or args.max_frame_bytes<3:parser.error('Invalid capture group size or shared-memory capacity')
    watchlist_rows=json.loads(args.watchlist.read_text()) if args.watchlist else []
    if not isinstance(watchlist_rows,list):parser.error('Watchlist must be a JSON array')
    watch_ids=set()
    for row in watchlist_rows:
        if (not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id']
            or row['id'] in watch_ids or not isinstance(row.get('plate'),str) or not row['plate']
            or not row['plate'].isascii() or not row['plate'].isalnum() or row['plate']!=row['plate'].upper()
            or not isinstance(row.get('enabled',True),bool)):
            parser.error('Each watchlist entry needs a unique string id, explicit uppercase alphanumeric plate and optional boolean enabled')
        watch_ids.add(row['id'])
    output=args.output.resolve()
    if output.exists(): parser.error('Use a fresh output directory')
    load_dotenv(REPO/'backend/.env.registry')
    cfg=json.loads(os.environ['REGISTRY_CONNECTORS_JSON'])['sentinel']
    prefix=cfg['credentials_prefix']; credentials=(os.environ[prefix+'_EMAIL'],os.environ[prefix+'_PASSWORD'])
    if urlsplit(cfg['login_url']).netloc!=urlsplit(cfg['catalogue_url']).netloc: raise ValueError('Origin mismatch')
    session=requests.Session()
    response=session.post(cfg['login_url'],data={'email':credentials[0],'password':credentials[1]},timeout=10,allow_redirects=False)
    if response.status_code not in (200,302,303): raise RuntimeError('Catalogue login failed')
    response=session.get(cfg['catalogue_url'],timeout=10,allow_redirects=False)
    if response.status_code!=200: raise RuntimeError('Catalogue unavailable')
    cameras=[{'id':str(c['id']),'name':str(c.get('name',c['id']))} for c in response.json() if args.all_cameras or str(c['id']) in args.cameras]
    if args.cameras and set(args.cameras)!={c['id'] for c in cameras}: raise ValueError('Requested cameras missing')
    if args.expected_cameras is not None and len(cameras)!=args.expected_cameras:raise ValueError('Catalogue camera count differs from requested benchmark')
    if any(not re.fullmatch('[A-Za-z0-9_-]+',c['id']) for c in cameras): raise ValueError('Unsafe camera identifier')
    output.mkdir(parents=True); (output/'evidence').mkdir(); (output/'code_snapshot').mkdir()
    code_files=['live_optimized.py','live_benchmark.py','shared_frames.py','encounter_store.py','encounter_report.py','cross_camera_report.py','plate_workflow.py','plate_formats.json','run_pipeline.py',
                'report_live.py','report_ocr_preprocessing.py','report_bundle.py','common.py','requirements-lock-macos-arm64.txt']
    for name in code_files:
        if (ROOT/name).exists(): shutil.copy2(ROOT/name,output/'code_snapshot'/name)
    atomic_json(output/'code_manifest.json',{name:sha256(output/'code_snapshot'/name) for name in code_files if (output/'code_snapshot'/name).exists()})
    config={'schema_version':'synetra.run.v2','requested_seconds':args.seconds,'sample_fps_target_per_camera':args.sample_fps,
        'device':args.device,'cameras':cameras,'created_at':utc(),
        'architecture':f'{args.capture_group_size} capture threads per process; bounded native-pixel shared-memory slots; batched plate detector; independent bounded OCR worker',
        'limits':{'max_vehicle_rois_per_frame':6,'plate_batch_size':args.plate_batch,'ocr_queue_capacity':16,
                  'max_ocr_queue_age_s':8,'max_frame_age_s':8,'tracker_gap_reset_s':3,'max_ocr_crop_bytes':1048576,
                  'shared_frame_max_bytes_per_camera':args.max_frame_bytes,'capture_group_size':args.capture_group_size},
        'plate_conf':.35,'vehicle_conf':.25,'input_size':640,'ocr_min_confidence':OCR_MIN_CONFIDENCE,
        'ocr_selection_policy':OCR_SELECTION_POLICY,'roi_policy':'full_frame; no unvalidated camera-specific exclusion',
        'encounter_storage':{'backend':'sqlite_wal','scope':'camera/session/track','watchlist_configured':args.watchlist is not None,
                             'notifications_enabled':False,'idle_close_seconds':10},
        'model_hashes':{name:sha256(MODELS/name) for name in ['yolo11n.pt','license-plate-finetune-v1n.pt']},
        'note':'Real feeds; no cloud intelligence, LLM, ReID, watchlist or production alerts; no labeled accuracy. Detection and OCR latency are separate.'}
    atomic_json(output/'config.json',config)
    ctx=mp.get_context('spawn'); gate=ctx.Event(); stop=ctx.Event(); done=ctx.Event()
    ready=ctx.Event(); ocr_ready=ctx.Event(); deadline=ctx.Value('d',0); counter=ctx.Value('i',0)
    slots={c['id']:SharedFrame(ctx,max_bytes=args.max_frame_bytes) for c in cameras}; jobs=ctx.Queue(maxsize=16)
    worker=ctx.Process(target=detect,args=(cameras,slots,output,gate,deadline,stop,ready,jobs,done,args.device,args.plate_batch))
    ocr=ctx.Process(target=ocr_worker,args=(output,jobs,done,ocr_ready,counter))
    ocr.start(); worker.start()
    processes=[]; restarts=0; aborted=None
    # Bounded model startup, before capture starts.
    startup=time.monotonic()
    while not (ready.is_set() and ocr_ready.is_set()):
        if not worker.is_alive() or not ocr.is_alive() or time.monotonic()-startup>100:
            for p in (worker,ocr):
                if p.is_alive(): p.terminate()
                p.join(3)
            raise RuntimeError('Model worker startup failed; inspect local run log')
        time.sleep(.2)
    groups=[cameras[i:i+args.capture_group_size] for i in range(0,len(cameras),args.capture_group_size)]
    def spawn(group):
        process=ctx.Process(target=capture_shared_group,args=(group,cfg,credentials,output,gate,deadline,stop,args.sample_fps,{c['id']:slots[c['id']] for c in group}))
        process.start(); return process
    for group in groups: processes.append(spawn(group))
    restart_times=[time.monotonic() for group in groups]
    started=time.monotonic(); deadline.value=started+args.seconds
    config.update(started_at=utc(),started_monotonic=started); atomic_json(output/'config.json',config)
    store=EncounterStore(output/'encounters.sqlite3',run_identity(config),OCR_SELECTION_POLICY)
    for row in watchlist_rows:store.add_watchlist(row['id'],row['plate'],row.get('enabled',True))
    store.close()
    gate.set()
    print(f'START optimized: {len(cameras)} cameras, {args.seconds}s, {args.sample_fps} FPS/camera, plate batch {args.plate_batch}',flush=True)
    last_print=0; low_memory_since=None
    try:
        with (output/'resources.jsonl').open('w') as log:
            while time.monotonic()<deadline.value:
                now=time.monotonic(); elapsed=now-started
                if not worker.is_alive(): aborted='detection_worker_exited'; break
                if not ocr.is_alive(): aborted='ocr_worker_exited'; break
                statuses=[load_json(output/'capture'/c['id']/'status.json',{}) for c in cameras]
                by_camera={c['id']:s for c,s in zip(cameras,statuses)}
                for i,(group,p) in enumerate(zip(groups,processes)):
                    stalled=now-restart_times[i]>25 and any(now-by_camera[c['id']].get('heartbeat_monotonic',started)>22 for c in group)
                    if stalled or not p.is_alive():
                        # Own the handoff lock before terminating a stalled decoder, so
                        # termination cannot leave a writer holding the mailbox lock.
                        acquired=[]
                        for c in group:
                            if not slots[c['id']].lock.acquire(timeout=1):
                                aborted='capture_handoff_lock_stalled';break
                            acquired.append(slots[c['id']].lock)
                        try:
                            if not aborted:
                                if p.is_alive(): p.terminate()
                                p.join(2)
                                if p.is_alive(): p.kill(); p.join(2)
                        finally:
                            for lock in acquired:lock.release()
                        if aborted:break
                        processes[i]=spawn(group); restart_times[i]=time.monotonic(); restarts+=1
                if aborted: break
                mem=psutil.virtual_memory(); tree=[psutil.Process()]+psutil.Process().children(recursive=True); rss=0
                for process in tree:
                    try: rss+=process.memory_info().rss
                    except psutil.Error: pass
                inf=load_json(output/'inference_status.json',{})
                if now-inf.get('heartbeat_monotonic',started)>60: aborted='detector_watchdog_timeout'; break
                os_=load_json(output/'ocr_status.json',{})
                if now-os_.get('heartbeat_monotonic',started)>60: aborted='ocr_watchdog_timeout'; break
                sample={'elapsed_s':elapsed,'cpu_percent':psutil.cpu_percent(interval=None),
                    'memory_available_mb':mem.available/2**20,'process_tree_rss_mb':rss/2**20,
                    'receiving_last_5s':sum(s.get('last_decoded_monotonic') is not None and now-s['last_decoded_monotonic']<5 for s in statuses),
                    'cameras_ever_decoded':sum(bool(s.get('decoded_frames')) for s in statuses),
                    'capture_group_restarts':restarts,'processed_frames':sum(s['processed_frames'] for s in inf.get('cameras',{}).values()),
                    'ocr_completed':os_.get('completed',0),'ocr_expired':os_.get('expired',0),
                    'ocr_outstanding':max(0,sum(s.get('ocr_enqueued',0) for s in inf.get('cameras',{}).values())-counter.value)}
                log.write(json.dumps(sample)+'\n'); log.flush()
                atomic_json(output/'progress.json',dict(sample,inference=inf,ocr=os_))
                if elapsed-last_print>=15:
                    print(f'{elapsed:.0f}s feeds={sample["receiving_last_5s"]}/{len(cameras)} frames={sample["processed_frames"]} OCR={sample["ocr_completed"]} outstanding={sample["ocr_outstanding"]} RAM_available={sample["memory_available_mb"]:.0f}MB',flush=True)
                    last_print=elapsed
                low_memory_since=(low_memory_since or now) if mem.available<180*2**20 else None
                if low_memory_since and now-low_memory_since>15: aborted='sustained_critical_memory_pressure'; break
                stop.wait(min(1,max(0,deadline.value-time.monotonic())))
    finally:
        measured=time.monotonic()-started; stop.set()
        # Capture/detection stop at the deadline; admitted OCR may drain afterward.
        worker.join(20)
        if worker.is_alive():
            aborted=aborted or 'detection_shutdown_timeout'; worker.terminate(); worker.join(3)
        done.set(); ocr.join(30)
        if ocr.is_alive():
            aborted=aborted or 'ocr_shutdown_timeout'; ocr.terminate(); ocr.join(3)
        for p in processes:
            p.join(.1)
            if p.is_alive(): p.terminate(); p.join(2)
            if p.is_alive(): p.kill(); p.join(2)
        if worker.exitcode!=0: aborted=aborted or 'detection_worker_failed'
        if ocr.exitcode!=0: aborted=aborted or 'ocr_worker_failed'
        inf=final_observations(output,config)
        store=EncounterStore(output/'encounters.sqlite3',run_identity(config),OCR_SELECTION_POLICY)
        store.finish();atomic_json(output/'encounters.json',store.export());store.close()
        statuses=[load_json(output/'capture'/c['id']/'status.json',{'camera_id':c['id'],'state':'no_status'}) for c in cameras]
        atomic_json(output/'summary.json',{'started_at':config['started_at'],'finished_at':utc(),
            'measured_wall_seconds':measured,'requested_seconds':args.seconds,'aborted_reason':aborted,
            'post_capture_finalize_seconds':time.monotonic()-started-measured,
            'capture_group_restarts':restarts,'capture_restart_scope':f'group_of_up_to_{args.capture_group_size}_cameras',
            'capture':statuses,'inference':inf,'ocr':load_json(output/'ocr_status.json',{}),
            'worker_exit_codes':{'detection':worker.exitcode,'ocr':ocr.exitcode}})
        print(f'FINISHED measured={measured:.2f}s aborted={aborted} output={output}',flush=True)
    if aborted: raise SystemExit(2)


if __name__=='__main__': main()
