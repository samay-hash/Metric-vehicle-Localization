"""Replay saved stage events into SQLite and render grouped encounters from JSON."""
import argparse
import json
from pathlib import Path
from common import save_json
from encounter_store import EncounterStore, run_identity
from plate_workflow import assess_readings, OCR_SELECTION_POLICY
from report_ocr_preprocessing import document, picture, esc


def replay(run, watchlist=None):
    config=json.loads((run/'config.json').read_text())
    store=EncounterStore(run/'encounters.sqlite3',run_identity(config),OCR_SELECTION_POLICY)
    try:
        if watchlist:
            for row in json.loads(watchlist.read_text()):
                store.add_watchlist(row['id'],row['plate'],row.get('enabled',True))
        frames=ocr=0
        with (run/'detection_frames.jsonl').open() as source:
            for line in source: frames+=store.record_frame(json.loads(line))
        with (run/'ocr_results.jsonl').open() as source:
            for line in source:
                event=json.loads(line)
                if event['event_status']=='completed':
                    ocr+=int(store.record_ocr(event,assess_readings(event['reading']['readings'])))
        store.finish()
        data=store.export()
        data['provenance']={'source':'saved_real_run_replay','original_run_unchanged':True,
                            'policy':OCR_SELECTION_POLICY,'time_basis':'selected frame receipt UTC',
                            'notifications_sent':False}
        save_json(run/'encounters.json',data)
    finally:store.close()
    render(run/'encounters.json')
    return {'inserted_frame_observations':frames,'inserted_ocr_observations':ocr,**data['summary']}


def render(path):
    render_data(json.loads(path.read_text()),path.parent)


def render_data(data, run):
    cards=[]
    # Show groups with OCR first; keep non-OCR encounters compact and searchable.
    for e in sorted(data['encounters'],key=lambda e:(not e['ocr_count'],e['camera_id'],e['first_seen'],e['id'])):
        if not e['ocr_count']:continue
        texts=[o['plate'] or '' for o in e['ocr_observations']]
        search=' '.join([e['camera_id'],e['track_id'],e['id']]+texts)
        heading=(f'<article id="encounter-{e["id"]}" class="{"candidate" if e["primary_plate"] else "unreadable"}" '
                 f'data-search="{esc(search.lower())}"><h2>{esc(e["camera_id"])} · track {esc(e["track_id"])}</h2>'
                 f'<p><strong>{esc(e["primary_plate"] or "No retained plate candidate")}</strong> · '
                 f'{e["frame_count"]} vehicle observations · {e["ocr_count"]} OCR observations<br>'
                 f'{esc(e["first_seen_utc"])} → {esc(e["last_seen_utc"])}<br>'
                 f'<small>{esc(e["identity_status"])} · {esc(e["status"])} · '
                 f'{"Conflicting plate candidates — review" if e["conflicting"] else "All identity claims remain unverified"}</small></p>')
        if not e['ocr_count']:
            cards.append(heading+'</article>');continue
        if e['best_crop']:heading+=picture(e['best_crop'],'Best crop by recorded image-quality score')
        rows=[]
        for o in e['ocr_observations']:
            d=o['decision']
            alternatives=' / '.join(a['text'] for a in d.get('alternatives',[]))
            rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [o['sequence'],o['plate'] or 'No candidate',
                round(o['confidence'],3) if o['confidence'] is not None else '',alternatives,
                'linked' if o['frame_observation_id'] else 'historical association unavailable'])+
                f'<td><a href="{esc(o["crop"] or "#")}">Crop</a></td></tr>')
        cards.append(heading+'<table><tr><th>Selected frame</th><th>Candidate</th><th>Confidence</th><th>Alternatives</th><th>Vehicle frame association</th><th>Evidence</th></tr>'+''.join(rows)+'</table></article>')
    s=data['summary']
    intro=(f'<p><b>{s["encounters_with_ocr"]} encounters with OCR · {s["ocr_observations"]} OCR observations · '
           f'{s["frame_observations"]} vehicle observations · {s["alerts"]} local watchlist alert records</b></p>'
           f'<p>{s["encounters"]} total track groups, including {s["untracked_fragments"]} isolated untracked fragments. '
           'These are not proven unique vehicles. This page displays groups with OCR; all groups remain in the JSON and database.</p><p class="note">Same camera/session/track observations are grouped. '
           'Broken tracks and untracked sightings are kept separate. Plate text alone never merges encounters. '
           'Existing raw observations and original benchmark measurements are preserved.</p>'
           '<p><a href="encounters.json">Encounter JSON</a> · <a href="encounters.sqlite3">SQLite database</a> · '
           '<a href="report.html">Benchmark</a> · <a href="ocr_report.html">All OCR reads</a></p>')
    page=document('SYNETRA · grouped camera encounters',intro,cards)
    page=page.replace('Retained candidates only','Encounters with plate candidates only').replace("+' reads'","+' encounters'")
    (run/'encounter_report.html').write_text(page)


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--run',type=Path);g.add_argument('--json',type=Path)
    p.add_argument('--watchlist',type=Path,help='Optional explicit local test watchlist JSON; sends no notifications')
    args=p.parse_args()
    if args.run: print(json.dumps(replay(args.run.resolve(),args.watchlist),indent=2))
    else:render(args.json.resolve())


if __name__=='__main__':main()
