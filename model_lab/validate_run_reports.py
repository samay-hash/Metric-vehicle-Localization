"""Check a completed run's report provenance, evidence links and JSON rendering."""
import argparse
import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from common import save_json
from report_bundle import render


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links, self.ids = [], set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'): self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key): self.links.append(attrs[key])


def validate(run):
    data = json.loads((run/'report.json').read_text())
    summary, totals = data['summary'], data['metrics']['totals']
    checks, details = {}, {}
    checks['requested_duration_completed'] = summary['measured_wall_seconds'] >= summary['requested_seconds'] and not summary['aborted_reason']
    checks['workers_exited_cleanly'] = all(v == 0 for v in summary['worker_exit_codes'].values())
    checks['all_cameras_processed'] = totals['cameras_with_inference'] == len(data['cameras'])
    checks['all_ocr_jobs_accounted'] = data['metrics']['ocr_unaccounted_jobs'] == 0
    observations = [json.loads(line) for line in (run/'observations.jsonl').read_text().splitlines()]
    completed = [e for e in data['ocr_events'] if e['event_status'] == 'completed']
    checks['frame_counts_match'] = len(observations) == totals['processed_frames']
    checks['ocr_counts_match'] = len(completed) == len(data['ocr']) == totals['ocr_reads'] == data['encounters']['summary']['ocr_observations']
    checks['ocr_source_frames_linked'] = data['encounters']['summary']['ocr_observations_without_frame_link'] == 0
    checks['report_selections_match_live'] = all(e['logged_ocr']['candidate'] == e['reevaluated_decision']['candidate'] for e in data['ocr'])
    with sqlite3.connect(f'file:{run}/encounters.sqlite3?mode=ro', uri=True) as db:
        checks['sqlite_integrity'] = db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        checks['sqlite_foreign_keys'] = not db.execute('PRAGMA foreign_key_check').fetchall()
        counts = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('encounters', 'frame_observations', 'ocr_observations', 'alerts')}
        checks['database_export_counts_match'] = all(data['encounters']['summary'][t] == n for t, n in counts.items())
        details['database_counts'] = counts
    manifests = [(run, data['input_hashes']), (run/'code_snapshot', data['inference_code_manifest']),
                 (run/'report_renderer_snapshot', data['renderer_code_manifest'])]
    bad_hashes = [str(base/name) for base, manifest in manifests for name, expected in manifest.items()
                  if not (base/name).is_file() or hashlib.sha256((base/name).read_bytes()).hexdigest() != expected]
    checks['provenance_hashes_match'] = not bad_hashes
    details['hash_mismatches'] = bad_hashes
    pages = ['report.html','ocr_report.html','preprocessing_report.html','encounter_report.html','cross_camera_report.html']
    parsed = {name: Links((run/name).read_text()) for name in pages}
    bad_links = []
    for name, page in parsed.items():
        for link in set(page.links):
            url = urlsplit(link)
            if url.scheme or url.netloc: continue
            target = unquote(url.path) or name
            if not (run/target).is_file(): bad_links.append([name, link, 'missing_file'])
            elif url.fragment and target in parsed and unquote(url.fragment) not in parsed[target].ids:
                bad_links.append([name, link, 'missing_anchor'])
    checks['report_evidence_links_exist'] = not bad_links
    details['broken_links'] = bad_links
    with tempfile.TemporaryDirectory(prefix='synetra-json-render-') as temp:
        target = Path(temp)/'report.json'
        target.write_bytes((run/'report.json').read_bytes())
        render(target)
        checks['json_only_html_reproduction'] = all((Path(temp)/p).read_bytes() == (run/p).read_bytes() for p in pages)
    details['ocr_event_counts'] = dict(Counter(e['event_status'] for e in data['ocr_events']))
    details['cross_camera_summary'] = data['cross_camera']['summary']
    result = {'schema_version':'synetra.validation.v1', 'run_id':run.name,
              'passed':all(checks.values()), 'checks':checks, 'details':details,
              'scope':'Artifact consistency and reproducibility, not labeled OCR accuracy or verified vehicle identity.'}
    save_json(run/'validation.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    result = validate(parser.parse_args().run.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
