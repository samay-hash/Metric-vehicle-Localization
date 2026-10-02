"""Local durable encounter/observation store. No global vehicle identity or notifications.

All times are frame receipt UTC, not claimed camera event time. Track fragments
are deliberately isolated; no plate-only or cross-camera merging is performed.
"""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()[:32]


def run_identity(config):
    return identity(config['started_at'], config.get('created_at'), config['cameras'])


class EncounterStore:
    def __init__(self, path, run_id, policy, idle_seconds=10):
        self.run_id, self.policy, self.idle_seconds = run_id, policy, idle_seconds
        self.db = sqlite3.connect(str(path), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, policy TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS encounters(
          id TEXT PRIMARY KEY, run_id TEXT NOT NULL, camera_id TEXT NOT NULL,
          session TEXT NOT NULL, track_id TEXT NOT NULL, tracked INTEGER NOT NULL,
          first_seen REAL NOT NULL, last_seen REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'active', best_crop TEXT, best_quality REAL,
          primary_plate TEXT, primary_support INTEGER NOT NULL DEFAULT 0,
          conflicting INTEGER NOT NULL DEFAULT 0,
          UNIQUE(run_id,camera_id,session,track_id));
        CREATE INDEX IF NOT EXISTS encounters_camera_time ON encounters(run_id,camera_id,last_seen);
        CREATE TABLE IF NOT EXISTS frame_observations(
          id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL REFERENCES encounters(id),
          sequence INTEGER NOT NULL, seen_at REAL NOT NULL, source_json TEXT NOT NULL,
          vehicle_json TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS frame_encounter ON frame_observations(encounter_id);
        CREATE TABLE IF NOT EXISTS ocr_observations(
          id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL REFERENCES encounters(id),
          sequence INTEGER NOT NULL, seen_at REAL NOT NULL, plate TEXT, confidence REAL,
          raw_json TEXT NOT NULL, decision_json TEXT NOT NULL, crop TEXT,
          frame_observation_id TEXT REFERENCES frame_observations(id),
          UNIQUE(encounter_id,sequence));
        CREATE INDEX IF NOT EXISTS ocr_encounter ON ocr_observations(encounter_id);
        CREATE TABLE IF NOT EXISTS watchlist(
          id TEXT PRIMARY KEY, plate TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS alerts(
          id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL REFERENCES encounters(id),
          watchlist_id TEXT NOT NULL REFERENCES watchlist(id), plate TEXT NOT NULL,
          support INTEGER NOT NULL, status TEXT NOT NULL,
          first_seen REAL NOT NULL, last_seen REAL NOT NULL,
          evidence_json TEXT NOT NULL, UNIQUE(encounter_id,watchlist_id));
        ''')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO runs VALUES (?,?)', (run_id, policy))
        stored = self.db.execute('SELECT policy FROM runs WHERE run_id=?', (run_id,)).fetchone()['policy']
        if stored != policy:
            self.db.close()
            raise ValueError('Existing encounter analysis uses a different selection policy; use a new database')

    def close(self): self.db.close()

    def encounter_id(self, camera, session, track):
        return identity('encounter', self.run_id, camera, session, str(track))

    def _ensure(self, camera, source, track):
        if not track:
            raise ValueError('An explicit track or isolated untracked-observation key is required')
        eid = self.encounter_id(camera, source['session'], track)
        seen = datetime.fromisoformat(source['receipt_utc']).timestamp()
        tracked = not str(track).startswith('untracked:')
        self.db.execute('''INSERT INTO encounters(id,run_id,camera_id,session,track_id,tracked,first_seen,last_seen)
          VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
          first_seen=MIN(first_seen,excluded.first_seen),last_seen=MAX(last_seen,excluded.last_seen)''',
          (eid,self.run_id,camera,source['session'],str(track),int(tracked),seen,seen))
        return eid, seen

    def record_frame(self, frame):
        inserted = 0
        with self.db:
            source = frame['source']; camera = frame['camera_id']
            now = datetime.fromisoformat(source['receipt_utc']).timestamp()
            self.db.execute("UPDATE encounters SET status='closed_idle' WHERE run_id=? AND camera_id=? AND status='active' AND last_seen<?",
                            (self.run_id,camera,now-self.idle_seconds))
            for index, vehicle in enumerate(frame['vehicles']):
                # Historical logs did not preserve the detector index for untracked
                # boxes. Isolate those rather than guessing an OCR association.
                track = vehicle.get('observation_track_id') or vehicle.get('track_id') or f'untracked:legacy:{source["sequence"]}:{index}'
                eid, seen = self._ensure(camera,source,track)
                oid = identity('frame_observation',eid,source['sequence'])
                inserted += self.db.execute('INSERT OR IGNORE INTO frame_observations VALUES (?,?,?,?,?,?)',
                    (oid,eid,source['sequence'],seen,json.dumps(source),json.dumps(vehicle))).rowcount
                self.db.execute('UPDATE ocr_observations SET frame_observation_id=? WHERE encounter_id=? AND sequence=? AND frame_observation_id IS NULL',
                                (oid,eid,source['sequence']))
        return inserted

    def record_ocr(self, event, decision=None):
        if event['event_status'] != 'completed': return False
        reading = event['reading']; source = event['selected_source']
        track = str(event['track_key'][2]); camera = event['camera_id']
        if event['track_key'][:2] != [camera,source['session']]:
            raise ValueError('OCR key does not match selected camera/session')
        decision = decision or reading
        eid = self.encounter_id(camera,source['session'],track)
        oid = identity('ocr_observation',eid,source['sequence'])
        with self.db:
            # Acquire the SQLite writer reservation before checking existence;
            # otherwise two retrying workers can both pass the SELECT check.
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute('SELECT 1 FROM ocr_observations WHERE id=?',(oid,)).fetchone(): return False
            eid, seen = self._ensure(camera,source,track)
            fid = identity('frame_observation',eid,source['sequence'])
            linked = self.db.execute('SELECT id FROM frame_observations WHERE id=?',(fid,)).fetchone()
            self.db.execute('INSERT INTO ocr_observations VALUES (?,?,?,?,?,?,?,?,?,?)',
                (oid,eid,source['sequence'],seen,decision.get('candidate'),decision.get('selected_confidence'),
                 json.dumps(event),json.dumps(decision),reading.get('crop'),fid if linked else None))
            quality = float(event.get('quality_score',0))
            if reading.get('crop'):
                self.db.execute('UPDATE encounters SET best_crop=?,best_quality=? WHERE id=? AND (best_quality IS NULL OR best_quality<?)',
                                (reading['crop'],quality,eid,quality))
            candidates = self.db.execute('''SELECT plate,COUNT(*) AS support,MAX(confidence) AS confidence FROM ocr_observations
                WHERE encounter_id=? AND plate IS NOT NULL GROUP BY plate ORDER BY support DESC,confidence DESC,plate ASC''',(eid,)).fetchall()
            if candidates:
                self.db.execute('UPDATE encounters SET primary_plate=?,primary_support=?,conflicting=? WHERE id=?',
                                (candidates[0]['plate'],candidates[0]['support'],int(len(candidates)>1),eid))
            self._update_alerts(eid)
        return True

    def add_watchlist(self, record_id, plate, enabled=True):
        # Watchlist values must be explicit; never repair OCR text to match them.
        if not plate or not plate.isascii() or not plate.isalnum() or plate != plate.upper():
            raise ValueError('Watchlist plate must be an explicit uppercase alphanumeric string')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT plate FROM watchlist WHERE id=?',(record_id,)).fetchone()
            if old and old['plate'] != plate:
                raise ValueError('Use a new watchlist record ID when changing the plate')
            self.db.execute('INSERT INTO watchlist VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled',
                            (record_id,plate,int(enabled)))
            for row in self.db.execute('SELECT id FROM encounters WHERE run_id=?',(self.run_id,)).fetchall():
                self._update_alerts(row['id'])

    def _update_alerts(self, eid):
        encounter = self.db.execute('SELECT conflicting FROM encounters WHERE id=?',(eid,)).fetchone()
        for watch in self.db.execute('SELECT * FROM watchlist WHERE enabled=1').fetchall():
            rows = self.db.execute('SELECT id,seen_at,decision_json,crop FROM ocr_observations WHERE encounter_id=? AND plate=? ORDER BY seen_at,id',
                                   (eid,watch['plate'])).fetchall()
            if not rows: continue
            ambiguous = any(json.loads(r['decision_json']).get('variant_relation') == 'disagreement' for r in rows)
            status = 'repeated_match_needs_review' if len(rows)>=3 and not encounter['conflicting'] and not ambiguous else 'possible_match_needs_review'
            self.db.execute('''INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(encounter_id,watchlist_id)
                DO UPDATE SET support=excluded.support,status=excluded.status,first_seen=excluded.first_seen,
                last_seen=excluded.last_seen,evidence_json=excluded.evidence_json''',
                (identity('alert',eid,watch['id']),eid,watch['id'],watch['plate'],len(rows),status,
                 rows[0]['seen_at'],rows[-1]['seen_at'],json.dumps([{'observation_id':r['id'],'crop':r['crop']} for r in rows])))

    def finish(self):
        with self.db:
            self.db.execute("UPDATE encounters SET status='closed_run_end' WHERE run_id=? AND status='active'",(self.run_id,))

    def export(self):
        encounters=[]
        for row in self.db.execute('SELECT * FROM encounters WHERE run_id=? ORDER BY camera_id,first_seen,id',(self.run_id,)):
            item=dict(row); eid=item['id']
            frames=self.db.execute('SELECT id,sequence,seen_at FROM frame_observations WHERE encounter_id=? ORDER BY seen_at,id',(eid,)).fetchall()
            ocr=self.db.execute('SELECT * FROM ocr_observations WHERE encounter_id=? ORDER BY seen_at,id',(eid,)).fetchall()
            item['frame_observations']=[dict(v) for v in frames]
            item['ocr_observations']=[dict(v,raw_event=json.loads(v['raw_json']),decision=json.loads(v['decision_json'])) for v in ocr]
            for o in item['ocr_observations']: del o['raw_json']; del o['decision_json']
            item['frame_count']=len(frames); item['ocr_count']=len(ocr)
            item['first_seen_utc']=datetime.fromtimestamp(item['first_seen'],tz=__import__('datetime').timezone.utc).isoformat()
            item['last_seen_utc']=datetime.fromtimestamp(item['last_seen'],tz=__import__('datetime').timezone.utc).isoformat()
            item['identity_status']='track_group_unverified' if item['tracked'] else 'untracked_fragment_unverified'
            encounters.append(item)
        alerts=[dict(r) for r in self.db.execute('SELECT alerts.* FROM alerts JOIN encounters ON encounters.id=alerts.encounter_id WHERE encounters.run_id=? ORDER BY alerts.id',(self.run_id,))]
        for alert in alerts: alert['evidence']=json.loads(alert.pop('evidence_json'))
        return {'schema_version':'synetra.encounters.v1','run_id':self.run_id,'selection_policy':self.policy,
            'summary':{'encounters':len(encounters),'encounters_with_ocr':sum(bool(e['ocr_count']) for e in encounters),
                'frame_observations':sum(e['frame_count'] for e in encounters),'ocr_observations':sum(e['ocr_count'] for e in encounters),
                'ocr_observations_without_frame_link':sum(o['frame_observation_id'] is None for e in encounters for o in e['ocr_observations']),
                'alerts':len(alerts),'untracked_fragments':sum(not e['tracked'] for e in encounters)},
            'limits':['Encounter counts are track groups, not proven unique vehicles.',
                      'Broken/untracked tracks are isolated; no plate-only or cross-camera merges.',
                      'Receipt UTC is not camera capture time. No notifications are sent.',
                      'Historical untracked OCR may lack a frame link because the detector index was not saved.'],
            'encounters':encounters,'alerts':alerts}
