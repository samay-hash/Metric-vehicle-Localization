"""Concurrency and event-joining checks; synthetic pixels are software tests only."""
import json
import multiprocessing as mp
import tempfile
import unittest
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from shared_frames import SharedFrame
from live_optimized import final_observations, detect


def publish_child(slot):
    slot.publish({'session':'s1','sequence':1,'width':8,'height':6}, np.full((6,8,3),17,np.uint8))


class OptimizedTests(unittest.TestCase):
    def test_detector_heartbeats_without_camera_frames(self):
        # Exercise the actual worker loop with unavailable input; no model inference
        # or generated footage is used in this liveness regression test.
        fake_modules = {
            'torch': SimpleNamespace(set_num_threads=Mock()),
            'ultralytics': SimpleNamespace(YOLO=Mock(return_value=SimpleNamespace(predict=Mock()))),
            'ultralytics.trackers.byte_tracker': SimpleNamespace(BYTETracker=type('Tracker', (), {})),
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', fake_modules):
            output=Path(tmp)
            cameras=[{'id':'c1','name':'Unavailable camera'}]
            (output/'config.json').write_text(json.dumps({'started_at':'test','cameras':cameras}))
            published=[]
            def capture_status(path, value):
                published.append((value['heartbeat_monotonic'], value['finished']))
            with patch('live_optimized.atomic_json', side_effect=capture_status):
                detect(cameras, {'c1':SimpleNamespace(read=lambda previous:None)}, output,
                       Mock(), SimpleNamespace(value=time.monotonic()+1.2), threading.Event(),
                       Mock(), Mock(), Mock(), 'cpu', 1)
            self.assertGreaterEqual(sum(not final for stamp,final in published), 2)
            self.assertTrue(published[-1][1])
            self.assertEqual((output/'detection_frames.jsonl').read_text(), '')

    def test_cross_process_native_pixels_and_duplicate_skip(self):
        ctx=mp.get_context('spawn'); slot=SharedFrame(ctx,max_bytes=1024)
        child=ctx.Process(target=publish_child,args=(slot,));child.start();child.join(10)
        self.assertEqual(child.exitcode,0)
        metadata,pixels=slot.read()
        np.testing.assert_array_equal(pixels,np.full((6,8,3),17,np.uint8))
        self.assertIsNone(slot.read(('s1',1)))
        pixels[:]=0
        self.assertEqual(int(slot.read()[1].min()),17)
        slot.publish(dict(metadata,session='s2'),np.full((6,8,3),19,np.uint8))
        self.assertEqual(int(slot.read(('s1',1))[1].min()),19)

    def test_capacity_is_bounded(self):
        slot=SharedFrame(mp.get_context('spawn'),max_bytes=12)
        with self.assertRaises(ValueError): slot.publish({'width':4,'height':4},np.zeros((4,4,3),np.uint8))

    def test_ocr_join_preserves_selected_frame_and_async_latency(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            frame={'camera_id':'c1','source':{'session':'s1','sequence':9},'ocr':[]}
            reading={'selected_source_sequence':7,'latency_ms':50,'receipt_to_ocr_result_ms':250,
                     'geometry':{'applied':False},'layout':{'layout':'single_line'},'candidate':'GJ01AB1234'}
            event={'event_status':'completed','camera_id':'c1','trigger_session':'s1','trigger_sequence':9,
                   'queue_wait_ms':40,'completed_monotonic':12,'reading':reading}
            (output/'detection_frames.jsonl').write_text(json.dumps(frame)+'\n')
            (output/'ocr_results.jsonl').write_text(json.dumps(event)+'\n')
            (output/'inference_status.json').write_text(json.dumps({'cameras':{'c1':{'ocr_enqueued':1}}}))
            result=final_observations(output,{'started_monotonic':0,'requested_seconds':10})
            merged=json.loads((output/'observations.jsonl').read_text())
            self.assertEqual(merged['ocr'][0]['selected_source_sequence'],7)
            self.assertEqual(result['selected_crop_receipt_to_ocr_result_ms']['p50'],250)
            self.assertEqual(result['ocr_completed_after_capture_deadline'],1)
            self.assertEqual(result['ocr_unaccounted_jobs'],0)


if __name__=='__main__':unittest.main()
