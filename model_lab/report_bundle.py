"""Build a versioned JSON view model and render all reports from that JSON alone.

Build:  python report_bundle.py --build runs/example
Render: python report_bundle.py --json runs/example/report.json
Keep evidence/, preprocessing/ and performance.png alongside the JSON for images.
"""
import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from common import save_json, sha256, ROOT
from report_ocr_preprocessing import document, picture, esc


def table(headers, rows):
    return '<table><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr>'+''.join(
        '<tr>'+''.join('<td>'+esc(value)+'</td>' for value in row)+'</tr>' for row in rows)+'</table>'


def build(run):
    def read(name): return json.loads((run/name).read_text())
    config=read('config.json'); summary=read('summary.json'); metrics=read('metrics.json')
    resources=[json.loads(line) for line in (run/'resources.jsonl').read_text().splitlines()]
    observations=[json.loads(line) for line in (run/'observations.jsonl').read_text().splitlines()]
    manifest=read('preprocessing/manifest.json')
    names={c['id']:c['name'] for c in config['cameras']}
    readings=[]
    for entry in manifest['reads']:
        r=entry['logged_ocr']
        readings.append(dict(entry, camera_name=names[entry['camera_id']],
            ocr_latency_ms=r.get('latency_ms'), queue_wait_ms=r.get('queue_wait_ms'),
            receipt_to_ocr_result_ms=r.get('receipt_to_ocr_result_ms')))
    latest={o['camera_id']:o['annotated'] for o in observations if o.get('annotated')}
    captures={c['camera_id']:c for c in summary['capture']}
    cameras=[dict(camera_id=c['id'],name=c['name'],capture=captures.get(c['id'],{}),
                  inference=summary['inference'].get('cameras',{}).get(c['id'],{}),
                  latest_annotated=latest.get(c['id'])) for c in config['cameras']]
    events_path=run/'ocr_results.jsonl'
    bundle={'schema_version':'synetra.reports.v1','run_id':run.name,
        'config':config,'summary':summary,'metrics':metrics,'cameras':cameras,
        'resources':resources,'ocr':readings,
        'ocr_events':[json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else [],
        'artifacts':{'performance_chart':'performance.png','observations':'observations.jsonl',
                     'detection_frames':'detection_frames.jsonl','ocr_events':'ocr_results.jsonl'},
        'provenance':{'ocr_rerun':False,'intermediate_images_reconstructed':True,
                      'selection_policy':manifest.get('selection_policy'),
                      'accuracy_measured':False,'images_relative_to_json':True},
        'limits':['Counts are predictions, not ground truth. No labeled accuracy was measured.',
                  'Capture receipt time is not camera event time; source PTS is stored separately.',
                  'Processing latency covers detection; asynchronous OCR has separate queue and completion timing.',
                  'Repeated candidates remain unverified and are not production watchlist alerts.',
                  'This live run has no matched, labeled baseline; it does not establish accuracy or a controlled speedup.']}
    for name in ('runtime','model_manifest','access_check','post_run_fixes'):
        if (run/f'{name}.json').exists(): bundle[name]=read(f'{name}.json')
    if (run/'code_manifest.json').exists(): bundle['inference_code_manifest']=read('code_manifest.json')
    if (run/'encounters.json').exists():
        bundle['encounters']=read('encounters.json')
        by_job={o['raw_event']['job_id']:e['id'] for e in bundle['encounters']['encounters'] for o in e['ocr_observations']}
        for entry in readings:
            entry['encounter_id']=by_job.get(entry['logged_ocr'].get('job_id'))
    if (run/'cross_camera.json').exists():bundle['cross_camera']=read('cross_camera.json')
    renderer_dir=run/'report_renderer_snapshot'
    renderer_dir.mkdir(exist_ok=True)
    for name in ('report_bundle.py','report_live.py','report_ocr_preprocessing.py','plate_workflow.py','plate_formats.json','encounter_store.py','encounter_report.py','cross_camera_report.py','common.py'):
        shutil.copy2(ROOT/name,renderer_dir/name)
    bundle['renderer_code_manifest']={p.name:sha256(p) for p in renderer_dir.iterdir() if p.is_file()}
    bundle['input_hashes']={name:sha256(run/name) for name in
        ('config.json','summary.json','metrics.json','observations.jsonl','resources.jsonl','preprocessing/manifest.json')}
    if (run/'encounters.json').exists():bundle['input_hashes']['encounters.json']=sha256(run/'encounters.json')
    if (run/'cross_camera.json').exists():bundle['input_hashes']['cross_camera.json']=sha256(run/'cross_camera.json')
    save_json(run/'report.json',bundle)
    return run/'report.json'


def render(path):
    data=json.loads(path.read_text()); run=path.parent
    if data['schema_version']!='synetra.reports.v1': raise ValueError('Unsupported report schema')
    summary=data['summary']; metrics=data['metrics']; totals=metrics['totals']; duration=summary['measured_wall_seconds']
    intro=(f'<p><b>{len(data["cameras"])} cameras · {duration:.2f} measured seconds · '
           f'{totals["processed_frames"]:,} processed frames · {totals["processed_fps_aggregate"]:.2f} aggregate FPS · '
           f'{totals["ocr_reads"]} OCR attempts</b></p>'
           f'<p>Run: {esc(data["run_id"])} · started {esc(summary["started_at"])} · '
           f'abort: {esc(summary["aborted_reason"] or "none")}</p>'
           '<p>These pages render from <a href="report.json">report.json</a>. Images are relative local assets. '
           '<a href="RESULTS.md">Detailed findings</a> · <a href="metrics.json">Metrics</a></p>')
    benchmark=['<article><h2>Per-camera measurements</h2>'+table(
        ['Camera','Sampled','Processed','Processed FPS','Vehicles','Plate boxes','OCR','Tracker initializations / resets'],
        [(c['name'],c['capture'].get('sampled_frames',0),c['inference'].get('processed_frames',0),
          round(c['inference'].get('processed_frames',0)/duration,3),c['inference'].get('vehicles',0),
          c['inference'].get('plate_boxes',0),c['inference'].get('ocr_reads',0),c['inference'].get('tracker_resets',0)) for c in data['cameras']])+'</article>']
    benchmark.append('<article><h2>Stage latency</h2>'+table(['Stage','p50 ms','p95 ms'],
        [(label,round(metrics.get(key,{}).get('p50',0),2),round(metrics.get(key,{}).get('p95',0),2)) for key,label in [
         ('processing_ms','Detection processing'),('frame_receipt_to_result_ms','Frame receipt → detection result'),
         ('ocr_queue_wait_ms','OCR queue wait'),('ocr_ms','OCR processing'),
         ('selected_crop_receipt_to_ocr_result_ms','Selected frame receipt → OCR result')]])+
        '<p>OCR includes jobs admitted during capture and completed during the bounded drain. '
        f'{metrics.get("ocr_completed_after_capture_deadline",0)} OCR results finished after the capture deadline.</p></article>')
    benchmark.append('<article><h2>Capture, throughput and resource measurements</h2>'+picture(data['artifacts']['performance_chart'],'Measured performance')+
        '<pre>'+esc(json.dumps({'resources':metrics['resources'],'stage_counters':metrics.get('stage_counters'),
                               'ocr_events':metrics.get('ocr_event_counts'), 'limits':data['config']['limits']},indent=2))+'</pre></article>')
    benchmark.append('<article><h2>Source continuity and crop selection</h2><p>Source-session changes can reflect reconnects or backward source timestamps. These can reset tracking even without a processing backlog.</p><pre>'+esc(json.dumps({
        'source_diagnostics':metrics.get('source_diagnostics',{}),
        'ocr_selection_reasons':metrics.get('ocr_selection_reasons',{})},indent=2))+'</pre></article>')
    benchmark.append('<article><h2>Capture recovery</h2><p>'+
        esc(f'{summary.get("capture_group_restarts",0)} capture-group restarts. Scope: {summary.get("capture_restart_scope","unknown")}.')+
        ' A group restart can interrupt other cameras in that group. Connection attempts and error counts below include automatic retries.</p>'+
        table(['Camera','Connection attempts','Errors'],[(c['name'],c['capture'].get('attempts',0),
            json.dumps(c['capture'].get('errors',{}))) for c in data['cameras']])+'</article>')
    if data.get('access_check'):
        benchmark.append('<article><h2>Access check after the run</h2><pre>'+esc(json.dumps(data['access_check'],indent=2))+'</pre></article>')
    if data.get('post_run_fixes'):
        benchmark.append('<article><h2>Changes after this measurement</h2><p>These changes were not used in this benchmark.</p><pre>'+esc(json.dumps(data['post_run_fixes'],indent=2))+'</pre></article>')
    for camera in data['cameras']:
        if camera.get('latest_annotated'):
            benchmark.append('<article><h2>'+esc(camera['name'])+'</h2>'+picture(camera['latest_annotated'],'Latest saved annotated frame')+'</article>')
    benchmark.append('<article><h2>Interpretation</h2><ul>'+''.join('<li>'+esc(v)+'</li>' for v in data['limits'])+'</ul></article>')
    benchmark_page=document('SYNETRA · optimized camera benchmark',intro,benchmark)
    benchmark_page=benchmark_page.replace('</head>', '<style>.benchmark figure{max-width:1100px}.benchmark img{max-height:none;width:100%;min-width:0}</style></head>').replace('<body>', '<body class="benchmark">')
    # Controls in the shared document apply only to OCR entries, not benchmark cards.
    benchmark_page=benchmark_page.replace('<div class="controls">','<div class="controls" hidden>')
    (run/'report.html').write_text(benchmark_page)
    (run/'benchmark_report.html').write_text(benchmark_page)
    ocr_cards=[]; prep_cards=[]
    reads=data['ocr']
    decisions=[r['reevaluated_decision'] for r in reads]
    selected=sum(bool(d['candidate']) for d in decisions)
    primary=sum(d.get('selected_variant')=='bicubic' for d in decisions)
    fallback=sum(d.get('selected_variant')=='mild_clahe' for d in decisions)
    disagreements=sum(bool(d['candidate']) and d.get('variant_relation')=='disagreement' for d in decisions)
    repeated=len(summary['inference'].get('repeated_candidates',[]))
    ocr_intro=(intro+f'<p>{len(reads)} OCR attempts · {selected} retained candidates '
        f'({primary} bicubic selections, {fallback} CLAHE selections) · {disagreements} disagreements · '
        f'{repeated} repeated candidates needing validation.</p>'
        '<p class="note">Readings must reach ≥0.70. Configured plate-structure hints rank first; bicubic breaks ties. Unsupported formats remain reviewable. '
        'Structure checks do not validate a registration or correct characters. '
        'Alternatives remain visible. Confidence is a model score, not measured accuracy. All numbers remain unverified.</p>')
    ocr_intro += '<p>Selection is re-evaluated using the current policy. Benchmark totals and repeated-candidate counts describe the original live run; temporal confirmation has not been rerun.</p>'
    for entry in sorted(reads,key=lambda r:(not bool(r['reevaluated_decision']['candidate']),r['read_index'])):
        r=entry['logged_ocr']; d=entry['reevaluated_decision']; i=entry['read_index']; source=entry['selected_source']
        search=' '.join([entry['camera_id'],entry['camera_name'],str(r['track_id'])]+[v['text'] for v in r['readings']])
        heading=(f'<article id="read-{i}" class="{"candidate" if d["candidate"] else "unreadable"}" data-search="{esc(search.lower())}">'
                 f'<h2>Read {i+1} · {esc(entry["camera_name"])}</h2><p>Frame {entry["selected_source_sequence"]} · '
                 f'track {esc(r["track_id"])} · received {esc(source.get("receipt_utc","unknown"))} · PTS {esc(source.get("pts_s","unknown"))} s</p>')
        if entry.get('encounter_id'):
            heading+=f'<p><a href="encounter_report.html#encounter-{esc(entry["encounter_id"])}">View grouped encounter and all its observations →</a></p>'
        if d['candidate']:
            decision=f'<p><strong>{esc(d["candidate"])} — {esc(d["selected_variant"])} candidate; needs confirmation</strong><br>Variants: {esc(d["variant_relation"])}'
            decision+='<br>Selection: '+esc(d.get('variant_selection_reason','previous policy').replace('_',' '))
            if d.get('selected_format'): decision+='<br>Format: '+esc(d['selected_format']['description'])
            if d.get('alternatives'):
                decision+='<br>Alternative: '+esc('; '.join(a['text'] for a in d['alternatives']))
            decision+='</p>'
        else: decision='<p><strong>No candidate: '+esc(d['status'].replace('_',' '))+'</strong></p>'
        readings_table=table(['Variant','Raw decoded text','Normalized text','Confidence','Per-line text'],
            [(v['variant'],v['raw'],v['text'],round(v['confidence'],3),
              ' / '.join(f'{line["raw"]} ({line["confidence"]:.3f})' for line in v['lines'])) for v in r['readings']])
        timing='<p><small>'+esc(f'OCR {entry["ocr_latency_ms"]} ms · queue {entry["queue_wait_ms"]} ms · selected frame receipt-to-OCR {entry["receipt_to_ocr_result_ms"]} ms')+'</small></p>'
        original=picture(entry['original_crop'],'Saved native-resolution plate crop')
        ocr_cards.append(heading+decision+original+readings_table+timing+
            f'<a href="preprocessing_report.html#read-{i}">Inspect preprocessing →</a></article>')
        stages='<div class="images">'+original+''.join(picture(path,name.replace('_',' ')) for name,path in entry['stages'].items())+'</div>'
        prep_cards.append(heading+decision+stages+readings_table+
            '<details><summary>Recorded preprocessing parameters</summary><pre>'+esc(json.dumps({'geometry':r['geometry'],'layout':r['layout']},indent=2))+'</pre></details>'+
            f'<a href="ocr_report.html#read-{i}">Decoded OCR entry →</a></article>')
    (run/'ocr_report.html').write_text(document('SYNETRA · decoded OCR',ocr_intro,ocr_cards))
    (run/'preprocessing_report.html').write_text(document('SYNETRA · preprocessing',ocr_intro+
        '<p>Intermediate images are reconstructed from saved native crops and logged geometry/line splits. '
        'They show inputs passed to the OCR API, before its internal transforms. OCR was not rerun.</p>',prep_cards))
    if data.get('encounters'):
        from encounter_report import render_data
        render_data(data['encounters'],run)
        for name in ('report.html','benchmark_report.html','ocr_report.html','preprocessing_report.html'):
            file=run/name
            file.write_text(file.read_text().replace('<nav>','<nav><a href="encounter_report.html">Grouped encounters</a> · '))
    if data.get('cross_camera'):
        from cross_camera_report import render_data as render_cross_camera
        render_cross_camera(data['cross_camera'],run)
        for name in ('report.html','benchmark_report.html','ocr_report.html','preprocessing_report.html','encounter_report.html'):
            file=run/name
            if file.exists():file.write_text(file.read_text().replace('<nav>','<nav><a href="cross_camera_report.html">Cross-camera candidates</a> · '))
    reports=['report.html','ocr_report.html','preprocessing_report.html']
    if data.get('encounters'):reports.append('encounter_report.html')
    if data.get('cross_camera'):reports.append('cross_camera_report.html')
    print(json.dumps({'report_json':str(path),'ocr_entries':len(reads),'candidates':selected,'reports':reports}))


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--build',type=Path)
    group.add_argument('--json',type=Path)
    args=parser.parse_args()
    path=build(args.build.resolve()) if args.build else args.json.resolve()
    render(path)


if __name__=='__main__':main()
