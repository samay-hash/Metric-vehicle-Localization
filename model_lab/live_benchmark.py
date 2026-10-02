"""Concurrent, bounded real-feed benchmark. No production events or external intelligence."""
import argparse
import json
import multiprocessing as mp
import os
import struct
import threading
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlsplit
from common import ROOT,REPO,MODELS,RUNS,sha256
from plate_workflow import OCR_MIN_CONFIDENCE, OCR_SELECTION_POLICY


def utc(): return datetime.now(timezone.utc).isoformat()


def atomic_json(path,data):
    tmp=path.with_suffix(f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(data)+'\n')
    tmp.replace(path)


def load_json(path,default=None):
    try: return json.loads(path.read_text())
    except (FileNotFoundError,json.JSONDecodeError): return default


def camera_loop(camera,cfg,credentials,output,gate,deadline,stop,sample_fps,mailbox=None):
    import av
    import cv2
    av.logging.set_level(av.logging.PANIC)
    cv2.setNumThreads(1)
    cam=camera['id'];folder=output/'capture'/cam;folder.mkdir(parents=True,exist_ok=True)
    status_path=folder/'status.json'
    old=load_json(status_path,{})
    state={'camera_id':cam,'name':camera['name'],'attempts':old.get('attempts',0),
           'decoded_frames':old.get('decoded_frames',0),'sampled_frames':old.get('sampled_frames',0),
           'errors':old.get('errors',{}),'state':'ready','last_decoded_monotonic':old.get('last_decoded_monotonic'),
           'first_frame_utc':old.get('first_frame_utc'),'last_frame_utc':old.get('last_frame_utc')}
    def publish():
        state['heartbeat_monotonic']=time.monotonic()
        atomic_json(status_path,state)
    publish();gate.wait()
    origin=urlsplit(cfg['rtsp_origin']);email,password=credentials
    path=cfg['rtsp_path_template'].format(camera_id=quote(cam,safe=''))
    url=f'{origin.scheme}://{quote(email,safe="")}:{quote(password,safe="")}@{origin.netloc}{path}'
    while not stop.is_set() and time.monotonic()<deadline.value:
        container=None
        state['attempts']+=1;state['state']='connecting';publish()
        session=uuid.uuid4().hex[:12]
        try:
            container=av.open(url,options={'rtsp_transport':'tcp','fflags':'nobuffer'},timeout=(6,6))
            stream=container.streams.video[0];stream.codec_context.thread_count=1
            state['codec']=stream.codec_context.name
            last_sample=-1e9;previous_pts=None;state['state']='connected';publish()
            for frame in container.decode(stream):
                now=time.monotonic()
                if stop.is_set() or now>=deadline.value: break
                state['decoded_frames']+=1;state['last_decoded_monotonic']=now
                state['first_frame_utc']=state['first_frame_utc'] or utc();state['last_frame_utc']=utc()
                pts=float(frame.pts*frame.time_base) if frame.pts is not None else None
                if previous_pts is not None and pts is not None and pts<previous_pts:
                    session=uuid.uuid4().hex[:12]
                previous_pts=pts
                if now-last_sample<1/sample_fps:
                    if now-state['heartbeat_monotonic']>=1: publish()
                    continue
                image=frame.to_ndarray(format='bgr24')
                state['sampled_frames']+=1
                metadata={'camera_id':cam,'sequence':state['sampled_frames'],'session':session,
                          'pts_s':pts,'receipt_utc':utc(),'receipt_monotonic':now,
                          'width':frame.width,'height':frame.height}
                if mailbox is not None:
                    if not mailbox.publish(metadata,image):
                        state['handoff_drops']=state.get('handoff_drops',0)+1
                else:
                    ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,98])
                    if not ok: continue
                    header=json.dumps(metadata).encode()
                    tmp=folder/'latest.tmp'
                    with tmp.open('wb') as f:
                        f.write(struct.pack('!I',len(header)));f.write(header);f.write(jpeg.tobytes())
                    tmp.replace(folder/'latest.frame')
                state['state']='receiving'
                if mailbox is None or now-state['heartbeat_monotonic']>=1: publish()
                last_sample=now
            if not stop.is_set() and time.monotonic()<deadline.value:
                state['errors']['stream_ended']=state['errors'].get('stream_ended',0)+1
        except Exception as exc:
            # Raw FFmpeg errors/URLs may contain credentials; save the exception type only.
            code=type(exc).__name__;state['errors'][code]=state['errors'].get(code,0)+1
            state['state']='connection_error';publish()
        finally:
            if container is not None:
                try: container.close()
                except Exception: pass
        if time.monotonic()<deadline.value:
            state['state']='retry_wait';publish()
            stop.wait(min(5,max(0,deadline.value-time.monotonic())))
    state['state']='finished';publish()


def capture_group(cameras,cfg,credentials,output,gate,deadline,stop,sample_fps):
    threads=[threading.Thread(target=camera_loop,args=(c,cfg,credentials,output,gate,deadline,stop,sample_fps),daemon=True) for c in cameras]
    for thread in threads: thread.start()
    for thread in threads: thread.join()


def read_latest(path):
    import cv2
    import numpy as np
    with path.open('rb') as f:
        size=struct.unpack('!I',f.read(4))[0]
        metadata=json.loads(f.read(size));image=cv2.imdecode(np.frombuffer(f.read(),dtype=np.uint8),cv2.IMREAD_COLOR)
    return metadata,image


def inference(cameras,output,gate,deadline,stop,ready,device):
    import cv2
    import numpy as np
    import torch
    from types import SimpleNamespace
    from ultralytics import YOLO
    from ultralytics.trackers.byte_tracker import BYTETracker
    from run_pipeline import clipped_box
    from plate_workflow import quality,PlateReader,BestFrames,Consensus
    torch.set_num_threads(1);cv2.setNumThreads(1)
    vehicle=YOLO(str(MODELS/'yolo11n.pt'));plate=YOLO(str(MODELS/'license-plate-finetune-v1n.pt'))
    reader=PlateReader();best=BestFrames();consensus=Consensus()
    # Prevent one camera's reset from resetting the shared STrack counter used by others.
    class CameraTracker(BYTETracker):
        @staticmethod
        def reset_id(): pass
    tracker_args=SimpleNamespace(track_high_thresh=.25,track_low_thresh=.1,new_track_thresh=.25,
                                 track_buffer=2,match_thresh=.8,fuse_score=True)
    states={c['id']:{'processed_frames':0,'vehicles':0,'vehicle_roi_budget_skipped':0,
                     'plate_boxes':0,'quality_rejected':0,'ocr_reads':0,'ocr_budget_skipped':0,
                     'stale_frames':0,'skipped_sample_sequences':0,'last_sequence':0,
                     'tracker_resets':0,'rectified':0,'two_line_reads':0} for c in cameras}
    trackers={};last_session={};last_pts={};epochs={c['id']:0 for c in cameras};last_example={}
    timings=[];ages=[];read_times=[];confirmed=[]
    for m in (vehicle,plate): m.predict(np.zeros((640,640,3),np.uint8),device=device,imgsz=640,verbose=False)
    ready.set();gate.wait()
    started=time.monotonic()
    output.joinpath('evidence').mkdir(exist_ok=True)
    def publish(final=False):
        atomic_json(output/'inference_status.json',{'cameras':states,'heartbeat_monotonic':time.monotonic(),
            'elapsed_s':time.monotonic()-started,'finished':final,'repeated_candidates':confirmed,
            'processing_ms':{'p50':float(np.percentile(timings,50)),'p95':float(np.percentile(timings,95))} if timings else {},
            'receipt_to_result_ms':{'p50':float(np.percentile(ages,50)),'p95':float(np.percentile(ages,95))} if ages else {},
            'ocr_ms':{'p50':float(np.percentile(read_times,50)),'p95':float(np.percentile(read_times,95))} if read_times else {}})
    with (output/'observations.jsonl').open('w') as log:
        while not stop.is_set() and time.monotonic()<deadline.value:
            did_work=False
            for c in cameras:
                if stop.is_set() or time.monotonic()>=deadline.value: break
                cam=c['id'];state=states[cam]
                try: meta,image=read_latest(output/'capture'/cam/'latest.frame')
                except (FileNotFoundError,ValueError,struct.error): continue
                seq=meta['sequence']
                if seq<=state['last_sequence'] or image is None: continue
                state['skipped_sample_sequences']+=max(0,seq-state['last_sequence']-1)
                state['last_sequence']=seq
                if time.monotonic()-meta['receipt_monotonic']>8:
                    state['stale_frames']+=1;continue
                did_work=True;start=time.monotonic()
                reset=(cam not in trackers or last_session.get(cam)!=meta['session'] or
                       (meta['pts_s'] is not None and cam in last_pts and last_pts[cam] is not None and
                        not 0<meta['pts_s']-last_pts[cam]<=3))
                if reset:
                    trackers[cam]=CameraTracker(tracker_args);epochs[cam]+=1;state['tracker_resets']+=1
                last_session[cam]=meta['session'];last_pts[cam]=meta['pts_s']
                pred=vehicle.predict(image,device=device,imgsz=640,classes=[2,3,5,7],conf=.1,verbose=False)[0]
                boxes=pred.boxes.cpu().numpy();tracks=trackers[cam].update(boxes,image)
                mapping={int(t[-1]):f'{epochs[cam]}:{int(t[4])}' for t in tracks}
                selected=[i for i,b in enumerate(boxes) if float(b.conf[0])>=.25]
                selected.sort(key=lambda i:float(boxes[i].xywh[0,2]*boxes[i].xywh[0,3]),reverse=True)
                state['vehicles']+=len(selected);state['vehicle_roi_budget_skipped']+=max(0,len(selected)-6)
                record={'camera_id':cam,'source':meta,'vehicles':[],'ocr':[],'started_monotonic':start}
                h,w=image.shape[:2];ocr_count=0
                save_example=start-last_example.get(cam,-1e9)>=30
                annotated=image.copy() if save_example else None
                for idx in selected[:6]:
                    bbox=clipped_box(boxes[idx].xyxy[0],w,h);x1,y1,x2,y2=bbox
                    if x2<=x1 or y2<=y1: continue
                    track=mapping.get(idx);crop=image[y1:y2,x1:x2]
                    item={'bbox':bbox,'track_id':track,'confidence':float(boxes[idx].conf[0]),'plates':[]}
                    prediction=plate.predict(crop,device=device,imgsz=640,conf=.35,verbose=False)[0]
                    for pidx,p in enumerate(prediction.boxes.cpu().numpy()):
                        a,b,d,e=clipped_box(p.xyxy[0],x2-x1,y2-y1)
                        if d<=a or e<=b: continue
                        pcrop=crop[b:e,a:d];q=quality(pcrop)
                        if (d-a)*(e-b)>.45*(x2-x1)*(y2-y1): q['reject_reasons'].append('large_fraction_of_vehicle')
                        state['plate_boxes']+=1
                        item['plates'].append({'bbox':[x1+a,y1+b,x1+d,y1+e],'quality':q,'confidence':float(p.conf[0])})
                        if annotated is not None: cv2.rectangle(annotated,(x1+a,y1+b),(x1+d,y1+e),(0,210,255),2)
                        if q['reject_reasons']: state['quality_rejected']+=1;continue
                        # A track may have multiple candidate boxes; separate nearby plate regions.
                        key=(cam,meta['session'],track or f'untracked:{seq}:{idx}')
                        selection=best.consider(key,seq,pcrop,q['score'],start)
                        if selection is None: continue
                        if ocr_count>=2: state['ocr_budget_skipped']+=1;continue
                        score,source_seq,best_crop=selection
                        ocr_start=time.monotonic();reading=reader.read(best_crop);ms=(time.monotonic()-ocr_start)*1000
                        ocr_count+=1;state['ocr_reads']+=1;state['rectified']+=int(reading['geometry']['applied'])
                        state['two_line_reads']+=int(reading['layout']['layout']=='two_lines');read_times.append(ms)
                        filename=f'evidence/{cam}_{meta["session"]}_{source_seq}_{str(key[2]).replace(":","-")}_{pidx}.png'
                        cv2.imwrite(str(output/filename),best_crop)
                        reading.update(track_id=track,selected_source_sequence=source_seq,crop=filename,latency_ms=ms)
                        record['ocr'].append(reading)
                        outcome=consensus.add(key,source_seq,reading['candidate'])
                        if outcome and not any(v['camera_id']==cam and v['key']==str(key) and v['candidate']==outcome['candidate'] for v in confirmed):
                            confirmed.append(dict(outcome,camera_id=cam,key=str(key)))
                    record['vehicles'].append(item)
                    if annotated is not None:
                        cv2.rectangle(annotated,(x1,y1),(x2,y2),(70,210,80),2)
                for key,selection in best.flush_camera(cam,start):
                    if ocr_count>=2:
                        state['ocr_budget_skipped']+=1;continue
                    score,source_seq,best_crop=selection
                    ocr_start=time.monotonic();reading=reader.read(best_crop);ms=(time.monotonic()-ocr_start)*1000
                    ocr_count+=1;state['ocr_reads']+=1;state['rectified']+=int(reading['geometry']['applied'])
                    state['two_line_reads']+=int(reading['layout']['layout']=='two_lines');read_times.append(ms)
                    filename=f'evidence/{cam}_{key[1]}_{source_seq}_{str(key[2]).replace(":","-")}_expired.png'
                    cv2.imwrite(str(output/filename),best_crop)
                    reading.update(track_id=key[2],selected_source_sequence=source_seq,crop=filename,latency_ms=ms,
                                   selection_reason='best_available_crop_after_short_encounter')
                    record['ocr'].append(reading)
                    outcome=consensus.add(key,source_seq,reading['candidate'])
                    if outcome and not any(v['camera_id']==cam and v['key']==str(key) and v['candidate']==outcome['candidate'] for v in confirmed):
                        confirmed.append(dict(outcome,camera_id=cam,key=str(key)))
                if annotated is not None:
                    filename=f'evidence/{cam}_frame_{seq}.jpg';cv2.imwrite(str(output/filename),annotated)
                    record['annotated']=filename;last_example[cam]=start
                state['processed_frames']+=1
                record['processing_ms']=(time.monotonic()-start)*1000
                record['receipt_to_result_ms']=(time.monotonic()-meta['receipt_monotonic'])*1000
                timings.append(record['processing_ms']);ages.append(record['receipt_to_result_ms'])
                log.write(json.dumps(record)+'\n');log.flush();publish()
            if not did_work: stop.wait(.05)
            publish()
    publish(final=True)


def main():
    import requests
    import psutil
    from dotenv import load_dotenv
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--sample-fps',type=float,default=2)
    parser.add_argument('--device',default='mps')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cameras',nargs='*')
    args=parser.parse_args()
    if args.seconds<=0 or args.sample_fps<=0: parser.error('Positive duration and sampling required')
    output=args.output.resolve()
    if output.exists(): parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    load_dotenv(REPO/'backend/.env.registry')
    cfg=json.loads(os.environ['REGISTRY_CONNECTORS_JSON'])['sentinel']
    prefix=cfg['credentials_prefix'];credentials=(os.environ[prefix+'_EMAIL'],os.environ[prefix+'_PASSWORD'])
    if urlsplit(cfg['login_url']).netloc!=urlsplit(cfg['catalogue_url']).netloc: raise ValueError('Origin mismatch')
    session=requests.Session()
    response=session.post(cfg['login_url'],data={'email':credentials[0],'password':credentials[1]},timeout=10,allow_redirects=False)
    if response.status_code not in (200,302,303): raise RuntimeError('Catalogue login failed')
    response=session.get(cfg['catalogue_url'],timeout=10,allow_redirects=False)
    if response.status_code!=200: raise RuntimeError('Catalogue unavailable')
    import re
    cameras=[{'id':str(c['id']),'name':str(c.get('name',c['id']))} for c in response.json()]
    if any(not re.fullmatch('[A-Za-z0-9_-]+',c['id']) for c in cameras): raise ValueError('Unsafe camera identifier')
    if args.cameras:
        if set(args.cameras)-{c['id'] for c in cameras}: raise ValueError('Camera absent from catalogue')
        cameras=[c for c in cameras if c['id'] in args.cameras]
    config={'requested_seconds':args.seconds,'sample_fps_target_per_camera':args.sample_fps,'device':args.device,
            'cameras':cameras,'created_at':utc(),'architecture':'30 concurrent capture threads grouped in processes; one fair shared inference worker',
            'limits':{'max_vehicle_rois_per_frame':6,'max_ocr_reads_per_frame':2,'max_frame_age_s':8,'tracker_gap_reset_s':3},
            'plate_conf':.35,'vehicle_conf':.25,'input_size':640,'ocr_min_confidence':OCR_MIN_CONFIDENCE,
            'ocr_selection_policy':OCR_SELECTION_POLICY,
            'model_hashes':{name:sha256(MODELS/name) for name in ['yolo11n.pt','license-plate-finetune-v1n.pt']},
            'note':'No LLM, ReID or production alerts in this timed ANPR test. Plate candidates require review; no labeled accuracy available.'}
    atomic_json(output/'config.json',config)
    ctx=mp.get_context('spawn');gate=ctx.Event();stop=ctx.Event();ready=ctx.Event();deadline=ctx.Value('d',0)
    worker=ctx.Process(target=inference,args=(cameras,output,gate,deadline,stop,ready,args.device))
    worker.start()
    if not ready.wait(60):
        worker.terminate();worker.join();raise RuntimeError('Inference did not become ready')
    groups=[cameras[i:i+5] for i in range(0,len(cameras),5)];processes=[];restarts=0
    def spawn(group):
        p=ctx.Process(target=capture_group,args=(group,cfg,credentials,output,gate,deadline,stop,args.sample_fps));p.start();return p
    for group in groups: processes.append(spawn(group))
    group_started=[time.monotonic() for _ in groups]
    # Start the shared measurement clock only after launching all capture processes.
    started=time.monotonic();deadline.value=started+args.seconds
    config.update(started_at=utc(),started_monotonic=started);atomic_json(output/'config.json',config);gate.set()
    print(f'START {len(cameras)} concurrent cameras for {args.seconds}s',flush=True)
    aborted=None;last_print=0;low_memory_since=None
    try:
        with (output/'resources.jsonl').open('w') as resources:
            while time.monotonic()<deadline.value:
                now=time.monotonic();elapsed=now-started
                if not worker.is_alive(): aborted='inference_process_exited';break
                statuses=[load_json(output/'capture'/c['id']/'status.json',{}) for c in cameras]
                for i,(group,p) in enumerate(zip(groups,processes)):
                    stuck=now-group_started[i]>25 and any(now-load_json(output/'capture'/c['id']/'status.json',{}).get('heartbeat_monotonic',started)>22 for c in group)
                    if not p.is_alive() or stuck:
                        if p.is_alive(): p.terminate();p.join(2)
                        if p.is_alive(): p.kill();p.join()
                        processes[i]=spawn(group);group_started[i]=now;restarts+=1
                mem=psutil.virtual_memory()
                cpu=psutil.cpu_percent(interval=None)
                tree=[psutil.Process()]+psutil.Process().children(recursive=True)
                rss=0
                for p in tree:
                    try: rss+=p.memory_info().rss
                    except psutil.Error: pass
                sample={'elapsed_s':elapsed,'cpu_percent':cpu,'memory_available_mb':mem.available/2**20,
                        'process_tree_rss_mb':rss/2**20,'receiving_last_5s':sum(s.get('last_decoded_monotonic') is not None and now-s['last_decoded_monotonic']<5 for s in statuses),
                        'cameras_ever_decoded':sum(bool(s.get('decoded_frames')) for s in statuses),'capture_group_restarts':restarts}
                resources.write(json.dumps(sample)+'\n');resources.flush()
                inf=load_json(output/'inference_status.json',{})
                atomic_json(output/'progress.json',dict(sample,inference=inf))
                if elapsed-last_print>=15:
                    print(f'{elapsed:.0f}s: recent feeds={sample["receiving_last_5s"]}, ever decoded={sample["cameras_ever_decoded"]}, processed={sum(s["processed_frames"] for s in inf.get("cameras",{}).values())}, OCR={sum(s["ocr_reads"] for s in inf.get("cameras",{}).values())}, available RAM={sample["memory_available_mb"]:.0f}MB',flush=True)
                    last_print=elapsed
                # Bound a pathological run instead of driving the user's laptop into OOM.
                low_memory_since=(low_memory_since or now) if mem.available<180*2**20 else None
                if low_memory_since and now-low_memory_since>15: aborted='sustained_critical_memory_pressure';break
                stop.wait(1)
    finally:
        measured=time.monotonic()-started;stop.set();worker.join(15)
        if worker.is_alive(): worker.terminate();worker.join(3)
        for p in processes:
            p.join(.1)
            if p.is_alive(): p.terminate();p.join(2)
            if p.is_alive(): p.kill();p.join()
        statuses=[load_json(output/'capture'/c['id']/'status.json',{'camera_id':c['id'],'state':'no_status'}) for c in cameras]
        inf=load_json(output/'inference_status.json',{})
        atomic_json(output/'summary.json',{'started_at':config['started_at'],'finished_at':utc(),
                    'measured_wall_seconds':measured,'requested_seconds':args.seconds,'aborted_reason':aborted,
                    'capture_group_restarts':restarts,'capture':statuses,'inference':inf})
        print(f'FINISHED: {measured:.1f}s, aborted={aborted}, {output}',flush=True)


if __name__=='__main__': main()
