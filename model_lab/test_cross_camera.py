import unittest
from cross_camera_report import analyse


def encounter(camera,seq=1,plate='GJ01AB1234',eid=None):
    return {'id':eid or camera,'camera_id':camera,'session':'s','track_id':'1:1','conflicting':0,
        'ocr_observations':[{'id':f'{camera}-{seq}-{eid}','sequence':seq,'seen_at':float(seq),'plate':plate,
            'confidence':.9,'crop':'evidence/crop.png','decision':{'variant_relation':'agreement','selected_variant':'bicubic','alternatives':[]}}]}


class CrossCameraTests(unittest.TestCase):
    def test_same_camera_repetitions_do_not_make_cross_camera_match(self):
        d=analyse({'run_id':'test','encounters':[encounter('c1',1),encounter('c1',2)]})
        self.assertEqual(d['summary']['cross_camera_plate_candidates'],0)

    def test_exact_match_keeps_evidence_and_never_claims_verified_route(self):
        d=analyse({'run_id':'test','encounters':[encounter('c2',2),encounter('c1',1),encounter('c1',1,eid='duplicate-track')]})
        self.assertEqual(d['summary']['cross_camera_plate_candidates'],1)
        m=d['matches'][0]
        self.assertEqual(m['camera_sightings'][0]['camera_id'],'c1')
        self.assertEqual(m['camera_sightings'][0]['distinct_source_frames'],1)
        self.assertEqual(m['camera_sightings'][0]['encounter_count'],2)
        self.assertEqual(d['summary']['verified_routes'],0)

    def test_similar_strings_and_alternatives_never_silently_match(self):
        a=encounter('c1');b=encounter('c2',plate='GJ01AB1235')
        b['ocr_observations'][0]['decision']['alternatives']=[{'text':'GJ01AB1234'}]
        d=analyse({'run_id':'test','encounters':[a,b]})
        self.assertEqual(d['summary']['cross_camera_plate_candidates'],0)


if __name__=='__main__':unittest.main()
