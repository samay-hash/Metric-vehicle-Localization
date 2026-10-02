"""Build an evidence-backed report from the completed concurrent benchmark."""
import argparse
import html
import json
from collections import Counter
from pathlib import Path
from common import save_json


def main():
    import numpy as np
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True,type=Path);args=parser.parse_args()
    run=args.run;summary=json.loads((run/'summary.json').read_text());config=json.loads((run/'config.json').read_text())
    observations=[json.loads(line) for line in (run/'observations.jsonl').read_text().splitlines()]
    resources=[json.loads(line) for line in (run/'resources.jsonl').read_text().splitlines()]
    inf=summary['inference'];states=inf.get('cameras',{});duration=summary['measured_wall_seconds']
    capture={c['camera_id']:c for c in summary['capture']};camera_names={c['id']:c['name'] for c in config['cameras']}
    totals={k:sum(s.get(k,0) for s in states.values()) for k in
            ['processed_frames','vehicles','plate_boxes','quality_rejected','ocr_reads','ocr_budget_skipped',
             'vehicle_roi_budget_skipped','tracker_resets','rectified','two_line_reads','stale_frames','skipped_sample_sequences']}
    totals['sampled_frames']=sum(s.get('sampled_frames',0) for s in capture.values())
    totals['decoded_frames']=sum(s.get('decoded_frames',0) for s in capture.values())
    totals['unprocessed_samples']=max(0,totals['sampled_frames']-totals['processed_frames'])
    totals['processed_fps_aggregate']=totals['processed_frames']/duration
    totals['cameras_with_frames']=sum(c.get('decoded_frames',0)>0 for c in capture.values())
    totals['cameras_with_inference']=sum(s.get('processed_frames',0)>0 for s in states.values())
    totals['candidate_reads']=sum(r['candidate'] is not None for o in observations for r in o['ocr'])
    totals['distinct_candidate_frames']=len({(o['camera_id'],r['selected_source_sequence'])
        for o in observations for r in o['ocr'] if r['candidate'] is not None})
    totals['repeated_candidates']=len(inf.get('repeated_candidates',[]))
    quality_reasons=Counter(reason for o in observations for v in o['vehicles'] for p in v['plates'] for reason in p['quality']['reject_reasons'])
    resource_summary={'cpu_percent_p50':float(np.median([r['cpu_percent'] for r in resources])),
                      'process_tree_rss_mb_max':max(r['process_tree_rss_mb'] for r in resources),
                      'memory_available_mb_min':min(r['memory_available_mb'] for r in resources),
                      'recently_receiving_cameras_p50':float(np.median([r['receiving_last_5s'] for r in resources])),
                      'all_cameras_recently_receiving_resource_samples':sum(r['receiving_last_5s']==len(states) for r in resources),
                      'resource_samples':len(resources)}
    # Selected crops can precede the frame on which OCR executes. Report their actual
    # receipt-to-result age separately from the current frame's pipeline latency.
    receipts={(o['camera_id'],o['source']['sequence']):o['source']['receipt_monotonic'] for o in observations}
    ocr_ages=[]
    for o in observations:
        end=o['started_monotonic']+o['processing_ms']/1000
        for reading in o['ocr']:
            if 'receipt_to_ocr_result_ms' in reading:
                ocr_ages.append(reading['receipt_to_ocr_result_ms'])
                continue
            receipt=receipts.get((o['camera_id'],reading['selected_source_sequence']))
            if receipt is not None: ocr_ages.append((end-receipt)*1000)
    ocr_age_stats={'p50':float(np.percentile(ocr_ages,50)),'p95':float(np.percentile(ocr_ages,95))} if ocr_ages else {}
    metrics={'totals':totals,'resources':resource_summary,'quality_rejections':dict(quality_reasons),
             'processing_ms':inf.get('processing_ms',{}),'frame_receipt_to_result_ms':inf.get('receipt_to_result_ms',{}),
             'selected_crop_receipt_to_ocr_result_ms':ocr_age_stats,'ocr_ms':inf.get('ocr_ms',{}),
             'ground_truth_accuracy':None,'proven_route_count':0}
    if config.get('schema_version') == 'synetra.run.v2':
        metrics.update(ocr_queue_wait_ms=inf.get('ocr_queue_wait_ms',{}),
            vehicle_inference_ms=inf.get('vehicle_inference_ms',{}),
            plate_stage_ms=inf.get('plate_inference_ms',{}),
            ocr_event_counts=inf.get('ocr_event_counts',{}),
            ocr_completed_after_capture_deadline=inf.get('ocr_completed_after_capture_deadline',0),
            ocr_unaccounted_jobs=inf.get('ocr_unaccounted_jobs',0),
            latency_scope='processing_ms and frame_receipt_to_result_ms measure detection, not asynchronous OCR',
            stage_counters={k:sum(s.get(k,0) for s in states.values()) for k in
                ['ocr_enqueued','ocr_queue_full','oversize_crop_skipped']})
        diagnostics={}
        for cam in states:
            sources=[o['source'] for o in observations if o['camera_id']==cam]
            causes=Counter(initialization=int(bool(sources)))
            for a,b in zip(sources,sources[1:]):
                if a['session']!=b['session']: causes['source_session_change']+=1
                elif a.get('pts_s') is not None and b.get('pts_s') is not None:
                    gap=b['pts_s']-a['pts_s']
                    if gap<=0: causes['nonincreasing_pts']+=1
                    elif gap>3: causes['source_gap_over_3s']+=1
            gaps=[b['receipt_monotonic']-a['receipt_monotonic'] for a,b in zip(sources,sources[1:])]
            diagnostics[cam]={'observed_reset_causes':dict(causes),
                'receipt_gap_s':{'p50':float(np.percentile(gaps,50)),'p95':float(np.percentile(gaps,95))} if gaps else {}}
        metrics['source_diagnostics']=diagnostics
        metrics['source_session_note']='A new source session can mean reconnect or backward source PTS; neither establishes a different vehicle.'
        metrics['ocr_selection_reasons']=dict(Counter(r.get('selection_reason','unknown') for o in observations for r in o['ocr']))
    save_json(run/'metrics.json',metrics)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    times=np.array([r['elapsed_s'] for r in resources])/60
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True,layout='constrained')
    axes[0].plot(times,[r['receiving_last_5s'] for r in resources],color='#15766b',linewidth=1.2)
    axes[0].set(ylabel='Recently receiving cameras',ylim=(0,len(states)+1),title='Measured behavior during the concurrent feed test')
    axes[0].axhline(len(states),color='#888',linestyle='--',linewidth=.8)
    edges=np.linspace(0,duration,max(1,round(duration/15))+1)
    counts,_=np.histogram([o['started_monotonic']-config['started_monotonic'] for o in observations],bins=edges)
    axes[1].stairs(counts/np.diff(edges),edges/60,label='Aggregate processed FPS (~15-second bins)',color='#285f94',baseline=None)
    axes[1].axhline(config['sample_fps_target_per_camera']*len(states),color='#aa6331',linestyle='--',label='Requested aggregate sample rate')
    axes[1].set(ylabel='Frames / second',ylim=(0,None));axes[1].legend(fontsize=8)
    axes[2].plot(times,[r['cpu_percent'] for r in resources],color='#8c4867',linewidth=1,label='Host CPU utilization')
    axes[2].set(xlabel='Elapsed minutes',ylabel='Host CPU %',ylim=(0,102))
    for axis in axes: axis.grid(alpha=.2)
    fig.savefig(run/'performance.png',dpi=150);plt.close(fig)
    rows=[]
    for cam,state in states.items():
        cap=capture.get(cam,{})
        rows.append([cam,cap.get('attempts',0),cap.get('sampled_frames',0),state['processed_frames'],
                     round(state['processed_frames']/duration,3),state['vehicles'],state['plate_boxes'],
                     state['ocr_reads'],json.dumps(cap.get('errors',{}))])
    md=[f'# Concurrent camera test — {duration:.1f} seconds',
        '',f'Started: {summary["started_at"]}. Requested: {summary["requested_seconds"]} seconds. Abort reason: {summary["aborted_reason"] or "none"}.',
        '',f'**{totals["cameras_with_frames"]}/{len(states)} cameras delivered frames; {totals["cameras_with_inference"]} received inference.**',
        f'{totals["sampled_frames"]:,} sampled frames; {totals["processed_frames"]:,} processed; {totals["unprocessed_samples"]:,} unprocessed/replaced/pending at stop. Aggregate processed rate: {totals["processed_fps_aggregate"]:.2f} FPS.',
        '',f'Vehicle boxes: {totals["vehicles"]:,}. Plate candidates: {totals["plate_boxes"]:,}. Quality-rejected: {totals["quality_rejected"]:,}. OCR attempts: {totals["ocr_reads"]:,}.',
        f'Originally logged OCR candidates: {totals["candidate_reads"]} across {totals["distinct_candidate_frames"]} distinct camera frames. Repeated candidates: {totals["repeated_candidates"]}. These remain unverified; no labeled accuracy or cross-camera identity proof. Dedicated OCR reports separately re-evaluate selection using the current policy.',
        '',f'Perspective corrections: {totals["rectified"]}; two-line OCR reads: {totals["two_line_reads"]}.',
        '',f'Processing latency: {metrics["processing_ms"]} ms. Frame receipt-to-result: {metrics["frame_receipt_to_result_ms"]} ms.',
        f'Selected crop receipt-to-OCR-result age: {ocr_age_stats} ms. Receipt timestamps are not source event timestamps.',
        '',f'Resource measurements: `{json.dumps(resource_summary)}`.',
        '',f'Capture restarts: {summary["capture_group_restarts"]}. Restart scope: {summary.get("capture_restart_scope", "five-camera group")}. This is a lab recovery mechanism.',
        '', '| Camera | Connect attempts | Sampled | Processed | Processed FPS | Vehicles | Plate boxes | OCR | Errors |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    md += ['| '+' | '.join(str(x) for x in row)+' |' for row in rows]
    md += ['', '## Limits',
           '', '- All configured feeds were admitted concurrently; a shared worker processed the newest available sample from each camera in round-robin order.',
           '- Target sampling was 2 FPS/camera. Actual processing FPS is reported above; this is not full-frame-rate analysis of every feed.',
           f'- Processing bounds: {json.dumps(config["limits"])}. Budget skips are explicit in metrics.json.',
           '- Native-resolution plate crops were used. Geometric/quality filters are prototype heuristics, not a newly trained plate detector.',
           '- In asynchronous runs, detection latency excludes OCR. OCR queue delay and selected-crop receipt-to-OCR-result latency are reported separately. Admitted OCR jobs may finish after capture stops.',
           '- Repeated OCR candidates require the same selected number across three distinct frames. Frame-level selection follows the run configuration/code snapshot; the current policy ranks configured plate-structure hints first and prefers bicubic on ties. Alternatives remain available. Repeated systematic errors can still pass; no candidate is treated as ground truth.',
           '- Track IDs reset across reconnects, source timestamp discontinuities and source-time gaps over three seconds. Fragmentation limits temporal confirmation under load.',
           '- Camera availability is observed, not assumed. “Recently receiving” means a decoded frame in the last five seconds, not uninterrupted uptime.',
           '- Process-tree RSS sums shared pages and does not isolate all MPS allocations. It is not an exact GPU-memory requirement.',
           '- Persisted capture counters may lose the last in-memory decode increments on a forced restart. Unprocessed sample counts include replaced, stale and pending frames.',
           '- No LLM, ReID, production alert or watchlist integration was included in this timed ANPR workflow.',
           '', '![Measured capture, processing and CPU behavior](performance.png)',
           '', '[Visual evidence report](report.html) · [Machine-readable metrics](metrics.json) · [Every observation](observations.jsonl)']
    (run/'RESULTS.md').write_text('\n'.join(md)+'\n')
    page=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SYNETRA — concurrent camera test</title>',
          '<style>body{font:15px/1.5 system-ui;color:#172126;background:#f7f7f4;margin:30px auto;padding:0 24px;max-width:1440px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:8px;border:1px solid #ddd;text-align:left}th{background:#e9ece8}img.crop{max-width:240px;min-width:100px;max-height:150px;object-fit:contain}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:16px}.grid img{width:100%}.note{background:#fff5df;padding:16px;border-left:4px solid #987322}small{color:#556}pre{white-space:pre-wrap}h2{margin-top:36px}</style>',
          f'<h1>SYNETRA · {duration/60:.1f}-minute concurrent camera test</h1>',
          '<p class="note">Real supplied camera feeds. Counts are model predictions. OCR candidates are unverified. Frames were sampled and some samples were discarded under load; this is not full-frame-rate analysis.</p>',
          f'<p><b>{totals["cameras_with_frames"]}/{len(states)} cameras delivered frames · {totals["processed_frames"]:,} frames processed · {totals["ocr_reads"]:,} OCR attempts · {totals["repeated_candidates"]} repeated candidates</b></p>',
          '<p><a href="ocr_report.html">All decoded OCR readings</a> · <a href="preprocessing_report.html">Preprocessing before / after</a> · <a href="RESULTS.md">Detailed findings</a> · <a href="metrics.json">Metrics</a> · <a href="observations.jsonl">Raw observations</a></p>',
          '<h2>Measured performance</h2><img src="performance.png" style="width:100%;max-width:1100px" alt="Actual capture coverage, processing rate and CPU utilization over time">',
          '<h2>Per-camera results</h2><table><tr>'+''.join(f'<th>{h}</th>' for h in ['Camera','Connect attempts','Sampled','Processed','FPS','Vehicles','Plate boxes','OCR','Errors'])+'</tr>']
    page += ['<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in row)+'</tr>' for row in rows]
    page.append('</table><h2>Sampled evidence</h2><div class="grid">')
    examples={}
    for o in observations:
        if 'annotated' in o: examples[o['camera_id']]=o
    for cam,o in examples.items():
        page.append(f'<div><h3>{html.escape(camera_names[cam])}</h3><a href="{o["annotated"]}"><img src="{o["annotated"]}" loading="lazy"></a><small>Sequence {o["source"]["sequence"]}; stream PTS {o["source"]["pts_s"]}. Green: vehicle, yellow: plate candidate.</small></div>')
    page.append('</div><h2>OCR evidence — first 200 reads</h2><p>All readings remain in observations.jsonl. Two variants of one image count as one frame.</p><table><tr><th>Camera / selected sequence</th><th>Original crop</th><th>Geometry / lines</th><th>OCR variants</th><th>Decision</th></tr>')
    readings=[(o,r) for o in observations for r in o['ocr']]
    for o,r in readings[:200]:
        text='<br>'.join(html.escape(f'{v["variant"]}: {v["raw"] or "∅"} ({v["confidence"]:.2f})') for v in r['readings'])
        page.append(f'<tr><td>{o["camera_id"]} / {r["selected_source_sequence"]}</td><td><a href="{r["crop"]}"><img class="crop" src="{r["crop"]}" loading="lazy"></a></td><td>rectified={r["geometry"]["applied"]}<br>{r["layout"]["layout"]}</td><td>{text}</td><td>{html.escape(r["candidate"] or r["status"])}</td></tr>')
    page.append('</table><h2>Metrics and interpretation</h2><pre>'+html.escape(json.dumps(metrics,indent=2))+'</pre></html>')
    (run/'report.html').write_text('\n'.join(page))
    # Keep the full OCR and preprocessing views alongside the summary report.
    import subprocess
    import sys
    subprocess.run([sys.executable, str(Path(__file__).with_name('report_ocr_preprocessing.py')),
                    '--run', str(run)], check=True)
    print(json.dumps(metrics,indent=2));print(run/'report.html')


if __name__=='__main__': main()
