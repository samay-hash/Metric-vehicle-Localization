"""Software checks only: synthetic shapes/text are not benchmark camera evidence."""
import unittest
import numpy as np
import cv2
from plate_workflow import quality,rectify,split_lines,BestFrames,Consensus,assess_readings


class PlateWorkflowTests(unittest.TestCase):
    def test_bicubic_wins_disagreement_even_when_clahe_scores_higher(self):
        readings=[{'variant':'mild_clahe','text':'GJO3NE9186','confidence':.883},
                  {'variant':'bicubic','text':'GJO3ME9186','confidence':.878}]
        decision=assess_readings(readings)
        self.assertEqual(decision['candidate'],'GJO3ME9186')
        self.assertEqual(decision['variant_relation'],'disagreement')
        self.assertEqual(decision['alternatives'][0]['text'],'GJO3NE9186')
        self.assertTrue(decision['needs_confirmation'])

    def test_structure_overrides_extra_leading_character(self):
        readings=[{'variant':'bicubic','text':'AGJ100N2875','confidence':.897},
                  {'variant':'mild_clahe','text':'GJ100N2875','confidence':.872}]
        decision=assess_readings(readings)
        self.assertEqual(decision['candidate'],'GJ100N2875')
        self.assertEqual(decision['variant_selection_reason'],'stronger_plate_structure')
        self.assertEqual(decision['selected_format']['profile'],'state_layout_ambiguous_series')
        self.assertFalse(decision['selected_format']['registration_verified'])
        self.assertEqual(decision['alternatives'][0]['text'],'AGJ100N2875')

    def test_format_hints_do_not_enforce_ten_characters(self):
        for text in ['GJ10A1234','DL1C1234','DL12ABC1234','22BH1234AA']:
            result=assess_readings([{'variant':'bicubic','text':text,'confidence':.8}])
            self.assertEqual(result['candidate'],text)
            self.assertEqual(result['selected_format']['rank'],2)

    def test_format_cannot_override_confidence_or_rewrite_text(self):
        result=assess_readings([{'variant':'bicubic','text':'AGJ100N2875','confidence':.9},
                               {'variant':'mild_clahe','text':'GJ10DN2875','confidence':.69}])
        self.assertEqual(result['candidate'],'AGJ100N2875')
        self.assertEqual(result['selected_format']['rank'],0)

    def test_clahe_fallback_and_threshold_boundary(self):
        readings=[{'variant':'bicubic','text':'GJ01AB1234','confidence':.699},
                  {'variant':'mild_clahe','text':'GJ01AB1234','confidence':.7}]
        self.assertEqual(assess_readings(readings)['selected_variant'],'mild_clahe')
        readings[0]['confidence']=.7
        self.assertEqual(assess_readings(readings)['selected_variant'],'bicubic')
        self.assertEqual(assess_readings(readings)['variant_relation'],'agreement')
        readings[0]['confidence']=readings[1]['confidence']=.699
        self.assertIsNone(assess_readings(readings)['candidate'])

    def test_empty_or_invalid_primary_does_not_block_valid_fallback(self):
        fallback={'variant':'mild_clahe','text':'GJ01AB1234','confidence':.85}
        for text in ('','12345678','ABCDEF','A1'):
            result=assess_readings([{'variant':'bicubic','text':text,'confidence':.99},fallback])
            self.assertEqual(result['selected_variant'],'mild_clahe')
        self.assertIsNone(assess_readings([])['candidate'])
        self.assertEqual(assess_readings([fallback])['selected_variant'],'mild_clahe')

    def test_flat_glare_is_rejected(self):
        q=quality(np.full((24,80,3),255,np.uint8))
        self.assertIn('low_contrast',q['reject_reasons'])
        self.assertIn('mostly_saturated',q['reject_reasons'])

    def test_small_source_cannot_pass_by_upscaling(self):
        q=quality(np.full((5,16,3),128,np.uint8))
        self.assertIn('too_few_native_pixels',q['reject_reasons'])

    def test_rectification_falls_back_without_a_quad(self):
        source=np.full((30,80,3),128,np.uint8)
        corrected,meta=rectify(source)
        self.assertFalse(meta['applied'])
        np.testing.assert_array_equal(source,corrected)

    def test_line_split_uses_an_ink_gap(self):
        source=np.full((100,180,3),255,np.uint8)
        cv2.putText(source,'AB12',(15,35),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,0),2)
        cv2.putText(source,'3456',(15,80),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,0),2)
        lines,meta=split_lines(source)
        self.assertEqual(meta['layout'],'two_lines')
        self.assertEqual(sum(line.shape[0] for line in lines),100)

    def test_same_frame_is_not_two_observations(self):
        best=BestFrames();crop=np.zeros((20,60,3),np.uint8);key=('cam01','session','track')
        self.assertIsNone(best.consider(key,1,crop,10,0))
        self.assertIsNone(best.consider(key,1,crop,20,.1))
        selected=best.consider(key,2,crop,15,.2)
        self.assertEqual(selected[1],1)
        self.assertEqual(selected[0],20)

    def test_short_encounter_keeps_best_single_crop(self):
        best=BestFrames();crop=np.zeros((20,60,3),np.uint8);key=('cam01','session','track')
        best.consider(key,1,crop,10,0)
        self.assertFalse(best.flush_camera('cam02',2))
        results=best.flush_camera('cam01',2)
        self.assertEqual(results[0][1][1],1)
        self.assertFalse(best.flush_camera('cam01',3))

    def test_consensus_requires_three_distinct_frames(self):
        votes=Consensus();key=('cam01','s1','t1')
        self.assertIsNone(votes.add(key,1,'GJ01AB1234'))
        self.assertIsNone(votes.add(key,1,'GJ01AB1234'))
        self.assertIsNone(votes.add(key,2,'GJ01AB1234'))
        self.assertEqual(votes.add(key,3,'GJ01AB1234')['distinct_frame_support'],3)

    def test_conflicting_text_or_camera_never_confirms(self):
        votes=Consensus()
        self.assertIsNone(votes.add(('cam01','s1','t1'),1,'GJ01AB1234'))
        self.assertIsNone(votes.add(('cam01','s1','t1'),2,'GJ01AB1235'))
        self.assertIsNone(votes.add(('cam01','s1','t1'),3,'GJ01AB1234'))
        self.assertIsNone(votes.add(('cam02','s1','t1'),4,'GJ01AB1234'))


if __name__=='__main__': unittest.main()
