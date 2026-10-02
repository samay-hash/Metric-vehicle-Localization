"""Find exact selected plate strings across cameras; never assert vehicle identity."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone
from common import save_json
from report_ocr_preprocessing import document, picture, esc


def analyse(encounter_data, camera_names=None):
    camera_names=camera_names or {}
    grouped=defaultdict(list)
    for encounter in encounter_data['encounters']:
        for observation in encounter['ocr_observations']:
            if observation['plate']:
                grouped[observation['plate']].append((encounter,observation))
    matches=[]
    for plate, records in grouped.items():
        cameras=sorted({e['camera_id'] for e,o in records})
        if len(cameras)<2:continue
        timeline=[]
        for camera in cameras:
            relevant=[(e,o) for e,o in records if e['camera_id']==camera]
            evidence=[]
            for e,o in sorted(relevant,key=lambda pair:(pair[1]['seen_at'],pair[1]['id'])):
                d=o['decision']
                evidence.append({'encounter_id':e['id'],'observation_id':o['id'],'track_id':e['track_id'],
                    'session':e['session'],'source_sequence':o['sequence'],
                    'receipt_utc':datetime.fromtimestamp(o['seen_at'],timezone.utc).isoformat(),
                    'receipt_epoch':o['seen_at'],'confidence':o['confidence'],'crop':o['crop'],
                    'variant_relation':d.get('variant_relation'),'selected_variant':d.get('selected_variant'),
                    'format':d.get('selected_format'),'encounter_conflicting':bool(e['conflicting']),
                    'alternatives':d.get('alternatives',[])})
            timeline.append({'camera_id':camera,'camera_name':camera_names.get(camera,camera),
                'first_receipt_utc':evidence[0]['receipt_utc'],'last_receipt_utc':evidence[-1]['receipt_utc'],
                'first_receipt_epoch':evidence[0]['receipt_epoch'],
                'distinct_source_frames':len({(e['session'],o['sequence']) for e,o in relevant}),
                'encounter_count':len({e['id'] for e,o in relevant}),'evidence':evidence})
        timeline.sort(key=lambda item:item['first_receipt_epoch'])
        matches.append({'plate':plate,'camera_count':len(cameras),'status':'exact_plate_text_across_cameras_unverified',
            'camera_sightings':timeline,'has_variant_disagreement':any(o['decision'].get('variant_relation')=='disagreement' for e,o in records),
            'has_conflicting_encounter':any(e['conflicting'] for e,o in records),
            'ordered_observations':sorted([dict(ev,camera_id=s['camera_id'],camera_name=s['camera_name'])
                for s in timeline for ev in s['evidence']],key=lambda ev:(ev['receipt_epoch'],ev['observation_id']))})
    matches.sort(key=lambda m:(-m['camera_count'],m['plate']))
    return {'schema_version':'synetra.cross_camera.v1','run_id':encounter_data['run_id'],
        'matching_rule':'Exact normalized selected candidates only; no fuzzy matching, character substitution or ReID.',
        'summary':{'distinct_selected_plate_strings':len(grouped),'cross_camera_plate_candidates':len(matches),
                   'verified_vehicle_matches':0,'verified_routes':0},
        'limits':['These are matching OCR strings, not verified vehicle identities.',
                  'Source cameras may replay or duplicate footage; this has not been independently excluded.',
                  'Receipt times are not synchronized camera capture times. Travel-time or GPS feasibility has not been validated.',
                  'Only selected candidates are matched; OCR alternatives remain visible for review.'],
        'matches':matches}


def render_data(data,run):
    cards=[]
    for match in data['matches']:
        text=f'{match["plate"]} '+ ' '.join(s['camera_name'] for s in match['camera_sightings'])
        body=f'<article class="candidate" data-search="{esc(text.lower())}"><h2>{esc(match["plate"])} · {match["camera_count"]} cameras</h2><p><strong>Exact OCR text match — unverified</strong></p>'
        for sighting in match['camera_sightings']:
            body+=f'<h3>{esc(sighting["camera_name"])} ({esc(sighting["camera_id"])})</h3><p>{esc(sighting["first_receipt_utc"])} → {esc(sighting["last_receipt_utc"])} · {sighting["distinct_source_frames"]} distinct source frames</p><div class="images">'
            for ev in sighting['evidence']:
                if ev['crop']:body+=picture(ev['crop'],f'{ev["receipt_utc"]} · score {ev["confidence"]:.3f} · {ev["variant_relation"]}')
                body+=f'<a href="encounter_report.html#encounter-{esc(ev["encounter_id"])}">Encounter evidence</a>'
            body+='</div>'
        body+='<details><summary>Ordered observations and uncertainty</summary><pre>'+esc(json.dumps(match['ordered_observations'],indent=2))+'</pre></details></article>'
        cards.append(body)
    summary=data['summary']
    intro=(f'<p><b>{summary["cross_camera_plate_candidates"]} plate strings appeared as selected candidates on two or more cameras.</b> '
           f'{summary["distinct_selected_plate_strings"]} distinct selected strings were examined.</p>'
           '<p class="note">Matching strings are leads for review, not confirmed vehicle routes. No ReID, fuzzy matching or automatic character repair was used.</p>'
           '<p><a href="cross_camera.json">Cross-camera JSON</a> · <a href="encounter_report.html">Encounters</a> · <a href="report.html">Benchmark</a></p>'+
           '<ul>'+''.join('<li>'+esc(v)+'</li>' for v in data['limits'])+'</ul>')
    if not cards:intro+='<p>No exact cross-camera plate candidates were found in this run. This does not prove that no vehicle crossed between cameras.</p>'
    (run/'cross_camera_report.html').write_text(document('SYNETRA · cross-camera plate candidates',intro,cards))


def build(run):
    config=json.loads((run/'config.json').read_text())
    encounters=json.loads((run/'encounters.json').read_text())
    data=analyse(encounters,{c['id']:c['name'] for c in config['cameras']})
    save_json(run/'cross_camera.json',data);render_data(data,run)
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().run.resolve())['summary'],indent=2))
