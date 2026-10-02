"""Generate a local evidence report from real pipeline outputs, without external assets."""
import argparse
import html
import json
from pathlib import Path
from common import save_json


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run
    summary = json.loads((run / 'summary.json').read_text())
    frames = load_jsonl(run / 'detections.jsonl')
    ocr = {name: {r['plate_id']: r for r in load_jsonl(run / f'ocr_{name}.jsonl')}
           for name in ['mobile','server','easyocr']}
    parts = ['''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SYNETRA model test evidence</title><style>
body{font:15px/1.5 system-ui,sans-serif;max-width:1300px;margin:36px auto;padding:0 24px;color:#172126;background:#f7f7f4}
h1{font-size:30px}h2{margin-top:38px}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #ddd;padding:9px;text-align:left}
th{background:#e9ece8}small{color:#556}img.frame{width:100%;max-width:960px}img.crop{min-width:90px;max-width:190px;max-height:110px;object-fit:contain;image-rendering:auto}
.note{padding:15px;border-left:4px solid #986d25;background:#fff8e8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}a{color:#17586e}
details{margin:16px 0}code{overflow-wrap:anywhere}</style><h1>SYNETRA · Model test evidence</h1>
<p class="note">Actual frames captured from the configured Sentinel RTSP feeds. These are short sequential samples, not a 30-camera concurrency benchmark.
Boxes and OCR strings are model predictions and may be wrong. No ground-truth accuracy has been established.</p>''']
    parts.append(f'<p>Run: <b>{html.escape(run.name)}</b> · Device: {html.escape(summary["device"])} · Input: {summary["imgsz"]}px</p>')
    parts.append('<h2>Camera results</h2><table><tr><th>Camera</th><th>Capture</th><th>Frames</th><th>Vehicle boxes</th><th>Plate boxes</th><th>Local tracks</th></tr>')
    for c in summary['cameras']:
        parts.append('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in
                     [c['camera_id']+' '+c['name'],c['capture_status'],c['frames'],c['vehicles'],c['plates'],c['local_tracks']])+'</tr>')
    parts.append('</table><h2>Annotated examples</h2><div class="grid">')
    by_camera = {}
    for frame in frames:
        score = sum(len(v['plates']) for v in frame['vehicles'])
        if frame['camera_id'] not in by_camera or score > by_camera[frame['camera_id']][0]:
            by_camera[frame['camera_id']] = (score,frame)
    for _, frame in by_camera.values():
        parts.append(f'<div><h3>{html.escape(frame["camera_name"])}</h3><a href="{frame["annotated"]}"><img class="frame" src="{frame["annotated"]}" loading="lazy"></a>'
                     f'<small>Frame {frame["frame_index"]} · stream PTS {frame["source"]["pts_s"]}s. Green: vehicle; yellow: predicted plate.</small></div>')
    parts.append('</div><h2>Plate crops and OCR comparison</h2><p>Inspect the source pixels before accepting a registration. Scores are the OCR model’s confidence, not probability of a correct vehicle identity.</p>')
    parts.append('<table><tr><th>Crop / source size</th><th>Camera / track</th><th>Mobile OCR</th><th>Server OCR</th><th>EasyOCR</th></tr>')
    for frame in frames:
        for vehicle in frame['vehicles']:
            for plate in vehicle['plates']:
                parts.append(f'<tr><td><a href="{plate["crop"]}"><img class="crop" src="{plate["crop"]}" loading="lazy"></a><br>{plate["width"]}×{plate["height"]}px</td>'
                             f'<td>{html.escape(frame["camera_id"])} / {html.escape(str(vehicle["track_id"]))}<br><small>{html.escape(plate["id"])}</small></td>')
                for name in ocr:
                    prediction = ocr[name].get(plate['id'])
                    text = (f'{prediction["raw"] or "∅"} ({prediction["confidence"]:.2f})' if prediction else 'Not run')
                    parts.append(f'<td>{html.escape(text)}</td>')
                parts.append('</tr>')
    parts.append('</table><h2>Run metadata</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>')
    (run / 'report.html').write_text('\n'.join(parts))
    print(run / 'report.html')


if __name__ == '__main__':
    main()
