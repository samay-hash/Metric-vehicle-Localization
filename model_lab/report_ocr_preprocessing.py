"""Expose every logged OCR read and reconstruct its preprocessing for inspection.

Does not run inference. Geometry and line splits come from the original log.
"""
import argparse
import html
import json
from pathlib import Path

from common import save_json
from plate_workflow import assess_readings, OCR_MIN_CONFIDENCE, OCR_SELECTION_POLICY
import cv2
import numpy as np


def esc(value):
    return html.escape(str(value), quote=True)


def picture(path, label):
    return (f'<figure><a href="{esc(path)}"><img src="{esc(path)}" loading="lazy" '
            f'alt="{esc(label)}"></a><figcaption>{esc(label)}</figcaption></figure>')


def reconstruct(run, index, reading):
    original = cv2.imread(str(run / reading['crop']))
    if original is None:
        raise ValueError(f'Missing crop: {reading["crop"]}')
    corrected = original
    geometry = reading['geometry']
    if geometry['applied']:
        p = np.array(geometry['corners'], dtype='float32')
        w = int(max(np.linalg.norm(p[1]-p[0]), np.linalg.norm(p[2]-p[3])))
        h = int(max(np.linalg.norm(p[3]-p[0]), np.linalg.norm(p[2]-p[1])))
        target = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype='float32')
        corrected = cv2.warpPerspective(original, cv2.getPerspectiveTransform(p, target),
                                        (w, h), flags=cv2.INTER_CUBIC)
    enlarged = cv2.resize(corrected, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    split = reading['layout'].get('split_y')
    lines = [enlarged[:split], enlarged[split:]] if split is not None else [enlarged]
    stages = [('corrected', corrected), ('bicubic_3x', enlarged)]
    for i, line in enumerate(lines, 1):
        lab = cv2.cvtColor(line, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4)).apply(lab[:, :, 0])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        stages += [(f'line_{i}', line), (f'clahe_{i}', enhanced)]
        for name, pixels in [('bicubic', line), ('mild_clahe', enhanced)]:
            stages.append((f'{name}_input_{i}', cv2.copyMakeBorder(pixels, 4, 4, 4, 4, cv2.BORDER_REPLICATE)))
    paths = {}
    for name, pixels in stages:
        relative = f'preprocessing/{index:04d}_{name}.png'
        if not cv2.imwrite(str(run / relative), pixels):
            raise OSError(f'Could not save {relative}')
        paths[name] = relative
    return paths, original.shape, len(lines)


def document(title, intro, cards):
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>''' + esc(title) + '''</title><style>
body{font:15px/1.5 system-ui,sans-serif;color:#182c30;background:#f5f6f3;max-width:1400px;margin:32px auto;padding:0 24px}
a{color:#125b75}nav{margin-bottom:24px}article{background:white;border:1px solid #d9dfdc;border-radius:8px;padding:22px;margin:20px 0;scroll-margin-top:12px}
article.candidate{border-left:5px solid #207a68}h1{font-size:30px}h2{font-size:20px;margin-top:0}h3{font-size:16px}
.note{background:#fff1d6;padding:16px}.images{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-start}
figure{margin:0;max-width:420px}img{max-width:100%;max-height:220px;min-width:120px;object-fit:contain;background:#eceeea}
figcaption,small{color:#526164;font-size:13px}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{text-align:left;border-bottom:1px solid #dde3df;padding:10px;overflow-wrap:anywhere}
code{font-size:17px;white-space:pre-wrap}.controls{display:flex;gap:16px;flex-wrap:wrap;align-items:center}input[type=search]{font:inherit;padding:10px;min-width:280px}summary{cursor:pointer}pre{white-space:pre-wrap}[hidden]{display:none!important}
</style></head><body><nav><a href="report.html">Run overview</a> · <a href="ocr_report.html">Decoded OCR</a> · <a href="preprocessing_report.html">Preprocessing</a></nav><h1>''' + esc(title) + '</h1>' + intro + '''
<div class="controls"><label>Search <input id="search" type="search" placeholder="Plate text, camera, track…"></label>
<label><input id="candidates" type="checkbox"> Retained candidates only</label><span id="count" aria-live="polite"></span></div>
''' + '\n'.join(cards) + '''<script>
const cards=[...document.querySelectorAll('article')],search=document.getElementById('search'),only=document.getElementById('candidates');
function filter(){let count=0;for(const card of cards){const visible=(card.dataset.search||card.textContent.toLowerCase()).includes(search.value.toLowerCase())&&(!only.checked||card.classList.contains('candidate'));card.hidden=!visible;if(visible)count++;}document.getElementById('count').textContent=count+' / '+cards.length+' reads';}
search.addEventListener('input',filter);only.addEventListener('change',filter);filter();
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    run = parser.parse_args().run.resolve()
    observations = [json.loads(line) for line in (run/'observations.jsonl').read_text().splitlines()]
    sources = {(o['camera_id'], o['source']['sequence']): o['source'] for o in observations}
    config = json.loads((run/'config.json').read_text())
    names = {c['id']: c['name'] for c in config['cameras']}
    reads = [(i, o, r) for i, (o, r) in enumerate((o, r) for o in observations for r in o['ocr'])]
    decisions = {i: assess_readings(r['readings']) for i, _, r in reads}
    reads.sort(key=lambda item: (not bool(decisions[item[0]]['candidate']), item[0]))
    (run/'preprocessing').mkdir(exist_ok=True)
    ocr_cards, preprocessing_cards, manifest = [], [], []
    for index, observation, reading in reads:
        cam = observation['camera_id']
        sequence = reading['selected_source_sequence']
        source = reading.get('selected_source') or sources.get((cam, sequence), {})
        paths, shape, line_count = reconstruct(run, index, reading)
        assessment = decisions[index]
        candidate = assessment['candidate']
        search = ' '.join([cam, names[cam], str(reading['track_id'])] +
                          [str(v[key]) for v in reading['readings'] for key in ('raw', 'text')])
        opening = (f'<article id="read-{index}" class="{"candidate" if candidate else "unreadable"}" '
                   f'data-search="{esc(search.lower())}"><h2>Read {index+1} · {esc(names[cam])}</h2>')
        metadata = (f'<p>{esc(cam)} · selected frame {sequence} · track {esc(reading["track_id"])}<br>'
                    f'<small>Selected frame received: {esc(source.get("receipt_utc", "unknown"))} · '
                    f'stream PTS: {esc(source.get("pts_s", "unknown"))} s. Receipt time is not camera capture time.</small></p>')
        reasons = {'missing_or_empty_reading': 'Missing or empty OCR reading',
                   'invalid_candidate_structure': 'Text fails candidate length / letter-and-digit checks',
                   'below_confidence_threshold': f'No plausible reading reaches {OCR_MIN_CONFIDENCE:.2f} confidence'}
        label = (f'{candidate} — {assessment["selected_variant"]} candidate; needs confirmation'
                 if candidate else reasons[assessment['status']])
        relation = {'agreement':'Variants agree on text', 'disagreement':'Variants disagree — alternative retained',
                    'unavailable':'No second nonempty reading to compare'}[assessment['variant_relation']]
        alternatives = '; '.join(f'{a["variant"]}: {a["text"]} ({a["confidence"]:.3f})' for a in assessment['alternatives'])
        decision = (f'<p><strong>{esc(label)}</strong><br>{esc(relation)}'
                    f'<br>Selection: {esc(assessment["variant_selection_reason"].replace("_", " "))}'
                    f'{"<br>Format: " + esc(assessment["selected_format"]["description"]) if candidate else ""}'
                    f'{"<br>Alternative: " + esc(alternatives) if alternatives else ""}<br>'
                    f'<small>Re-evaluated at {OCR_MIN_CONFIDENCE:.2f}. Original logged decision: '
                    f'{esc(reading["candidate"] or reading["status"])}.</small></p>')
        rows = []
        for variant in reading['readings']:
            rows.append('<tr>' + ''.join(f'<td>{value}</td>' for value in [esc(variant['variant']),
                '<code>'+esc(variant['raw'] or '∅')+'</code>', '<code>'+esc(variant['text'] or '∅')+'</code>',
                f'{variant["confidence"]:.3f}', '<br>'.join(f'{esc(v["raw"] or "∅")} ({v["confidence"]:.3f})' for v in variant['lines'])]) + '</tr>')
        table = '<table><tr><th>Variant</th><th>Raw decoded text</th><th>Normalized text</th><th>Model confidence</th><th>Per-line text (confidence)</th></tr>'+''.join(rows)+'</table>'
        original = picture(reading['crop'], f'Original crop · {shape[1]} × {shape[0]} px')
        ocr_cards.append(opening+metadata+decision+original+table+
                         f'<a href="preprocessing_report.html#read-{index}">See this crop’s preprocessing steps →</a></article>')
        stages = original + picture(paths['corrected'], 'Perspective corrected' if reading['geometry']['applied'] else 'Geometry unchanged — no valid quadrilateral')
        stages += picture(paths['bicubic_3x'], '3× bicubic enlargement')
        stages = '<div class="images">'+stages+'</div>'
        for i in range(1, line_count+1):
            stages += f'<h3>Line {i} of {line_count}</h3><div class="images">'
            for key, label in [(f'line_{i}', 'Selected line'), (f'clahe_{i}', 'Mild CLAHE contrast'),
                               (f'bicubic_input_{i}', 'Bicubic OCR input · 4 px margin'),
                               (f'mild_clahe_input_{i}', 'CLAHE OCR input · 4 px margin')]:
                stages += picture(paths[key], label)
            stages += '</div>'
        details = esc(json.dumps({'geometry':reading['geometry'], 'layout':reading['layout']}, indent=2))
        preprocessing_cards.append(opening+metadata+decision+stages+table+
            f'<details><summary>Recorded transform parameters</summary><pre>{details}</pre></details>'
            f'<p><a href="ocr_report.html#read-{index}">View decoded OCR entry →</a></p></article>')
        manifest.append({'read_index': index, 'camera_id':cam, 'selected_source_sequence': sequence,
                         'selected_source':source, 'original_crop':reading['crop'], 'stages':paths,
                         'logged_ocr':reading, 'reevaluated_decision':assessment})
    candidates = sum(bool(d['candidate']) for d in decisions.values())
    original_candidates = sum(bool(r['candidate']) for _, _, r in reads)
    distinct = len({(o['camera_id'], r['selected_source_sequence']) for i, o, r in reads if decisions[i]['candidate']})
    primary = sum(d['selected_variant'] == 'bicubic' for d in decisions.values())
    fallback = sum(d['selected_variant'] == 'mild_clahe' for d in decisions.values())
    disagreements = sum(bool(d['candidate']) and d['variant_relation'] == 'disagreement' for d in decisions.values())
    intro = (f'<p>{len(reads)} OCR attempts · {candidates} retained candidates from {distinct} distinct frames: '
             f'{primary} bicubic selections, {fallback} CLAHE selections. {disagreements} retained candidates have variant disagreements. Candidates appear first.</p>'
             f'<p>Saved readings re-evaluated at confidence ≥{OCR_MIN_CONFIDENCE:.2f}: stronger configured plate structure ranks first, then bicubic breaks ties. '
             'Candidate length and letter-and-digit checks still apply. Alternative readings are preserved. All candidates need separate-frame confirmation. '
             f'The original run logged {original_candidates} agreement outputs; its raw observations and benchmark metrics are unchanged. '
             'Temporal confirmation has not been rerun.</p>'
             '<p class="note">All decoded strings are original logged model outputs, including failed reads. '
             'Confidence is a model score, not measured accuracy. Agreement between two versions of one crop does not confirm vehicle identity.</p>')
    (run/'ocr_report.html').write_text(document('Decoded plate OCR · ten-minute run', intro, ocr_cards))
    prep_intro = intro + ('<p>Intermediate images were reconstructed from saved original PNG crops using the recorded perspective corners and line splits. '
        'Bicubic enlargement, CLAHE and replicated margins follow the live workflow. These are the images passed to the OCR API before its internal model transforms. '
        'OCR was not rerun. This view does not measure improvement over raw-crop OCR.</p>')
    (run/'preprocessing_report.html').write_text(document('Plate preprocessing · ten-minute run', prep_intro, preprocessing_cards))
    save_json(run/'preprocessing/manifest.json', {'reconstructed':True, 'ocr_rerun':False,
              'reevaluation_min_confidence':OCR_MIN_CONFIDENCE, 'selection_policy':OCR_SELECTION_POLICY, 'reads':manifest})
    print(json.dumps({'reads':len(reads), 'retained_candidates':candidates, 'primary':primary, 'fallback':fallback,
                      'disagreements':disagreements, 'distinct_candidate_frames':distinct,
                      'ocr_report':str(run/'ocr_report.html'), 'preprocessing_report':str(run/'preprocessing_report.html')}))


if __name__ == '__main__':
    main()
