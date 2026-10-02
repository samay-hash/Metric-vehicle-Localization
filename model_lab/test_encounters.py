"""Encounter/alert durability checks. Fixtures are synthetic software tests only."""
import copy
import json
import multiprocessing as mp
import tempfile
import unittest
from pathlib import Path
from encounter_store import EncounterStore


def event(sequence=1, track='1:7', camera='cam01', session='s1', plate='GJ01AB1234', quality=10):
    source={'sequence':sequence,'session':session,'receipt_utc':f'2026-09-18T14:00:{sequence:02d}+00:00','pts_s':sequence}
    reading={'candidate':plate,'selected_confidence':.9,'variant_relation':'agreement',
             'alternatives':[],'crop':f'evidence/{sequence}.png','selected_source_sequence':sequence}
    return {'event_status':'completed','camera_id':camera,'selected_source':source,'track_key':[camera,session,track],
            'quality_score':quality,'reading':reading,'job_id':f'job{sequence}'}


def parallel_writer(path):
    store=EncounterStore(path,'test','policy')
    for i in range(1,8):store.record_ocr(event(i))
    store.close()


class EncounterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'encounters.sqlite3'
        self.store=EncounterStore(self.path,'test','policy')
    def tearDown(self):self.store.close();self.temp.cleanup()

    def test_retry_and_restart_do_not_create_observations_or_alerts(self):
        self.store.add_watchlist('watch1','GJ01AB1234')
        for i in range(1,4):self.assertTrue(self.store.record_ocr(event(i)))
        self.store.close();self.store=EncounterStore(self.path,'test','policy')
        for i in range(1,4):self.assertFalse(self.store.record_ocr(event(i)))
        data=self.store.export()
        self.assertEqual(data['summary']['encounters'],1)
        self.assertEqual(data['summary']['ocr_observations'],3)
        self.assertEqual(data['summary']['alerts'],1)
        self.assertEqual(data['alerts'][0]['support'],3)
        self.assertEqual(data['alerts'][0]['status'],'repeated_match_needs_review')

    def test_same_plate_never_merges_cameras_sessions_or_tracks(self):
        for kwargs in [{},{'camera':'cam02'},{'session':'s2'},{'track':'1:8'},{'track':'untracked:1:0'}]:
            self.store.record_ocr(event(**kwargs))
        self.assertEqual(self.store.export()['summary']['encounters'],5)

    def test_conflicts_update_one_encounter_without_inventing_identity(self):
        self.store.add_watchlist('watch1','GJ01AB1234')
        self.store.record_ocr(event(1,quality=20))
        self.store.record_ocr(event(2,plate='GJ01AB1235',quality=10))
        self.store.record_ocr(event(3,quality=30));self.store.record_ocr(event(4))
        data=self.store.export();e=data['encounters'][0]
        self.assertEqual(e['primary_plate'],'GJ01AB1234')
        self.assertTrue(e['conflicting'])
        self.assertEqual(e['best_crop'],'evidence/3.png')
        self.assertEqual(data['alerts'][0]['status'],'possible_match_needs_review')
        self.assertEqual(e['first_seen_utc'],'2026-09-18T14:00:01+00:00')
        self.assertEqual(e['last_seen_utc'],'2026-09-18T14:00:04+00:00')

    def test_late_frame_links_ocr_and_late_ocr_uses_source_time(self):
        job=event(3);job['completed_monotonic']=999999
        self.store.record_ocr(job)
        frame={'camera_id':'cam01','source':job['selected_source'],
               'vehicles':[{'track_id':'1:7','bbox':[1,2,30,40]}]}
        self.assertEqual(self.store.record_frame(frame),1)
        self.assertEqual(self.store.record_frame(frame),0)
        self.store.finish();self.store.record_ocr(event(1))
        data=self.store.export();e=data['encounters'][0]
        linked=next(o for o in e['ocr_observations'] if o['sequence']==3)
        self.assertIsNotNone(linked['frame_observation_id'])
        self.assertEqual(e['first_seen_utc'],'2026-09-18T14:00:01+00:00')
        self.assertEqual(e['last_seen_utc'],'2026-09-18T14:00:03+00:00')
        self.assertEqual(e['status'],'closed_run_end')

    def test_ambiguous_alternatives_stay_review_only(self):
        self.store.add_watchlist('watch1','GJ01AB1234')
        for i in range(1,4):
            job=event(i);job['reading'].update(variant_relation='disagreement',alternatives=[{'text':'GJ01AB1235'}])
            self.store.record_ocr(job)
        data=self.store.export()
        self.assertEqual(data['alerts'][0]['status'],'possible_match_needs_review')
        self.assertEqual(data['encounters'][0]['ocr_observations'][0]['decision']['alternatives'][0]['text'],'GJ01AB1235')

    def test_watchlist_added_after_evidence_is_idempotent(self):
        self.store.record_ocr(event())
        self.store.add_watchlist('watch1','GJ01AB1234');self.store.add_watchlist('watch1','GJ01AB1234')
        self.assertEqual(self.store.export()['summary']['alerts'],1)
        with self.assertRaises(ValueError):self.store.add_watchlist('watch1','GJ01AB1235')

    def test_concurrent_retries_are_atomic(self):
        ctx=mp.get_context('spawn')
        workers=[ctx.Process(target=parallel_writer,args=(str(self.path),)) for _ in range(2)]
        for w in workers:w.start()
        for w in workers:w.join(15);self.assertEqual(w.exitcode,0)
        self.assertEqual(self.store.export()['summary']['ocr_observations'],7)

    def test_policy_change_requires_separate_analysis(self):
        with self.assertRaises(ValueError):EncounterStore(self.path,'test','new-policy')


if __name__=='__main__':unittest.main()
