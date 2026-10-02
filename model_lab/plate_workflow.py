"""Conservative plate geometry, line segmentation and frame selection for the live lab."""
import re
import json
from functools import lru_cache
from pathlib import Path
from collections import defaultdict

OCR_MIN_CONFIDENCE = 0.70
OCR_SELECTION_POLICY = 'format_rank_then_bicubic_v2'


@lru_cache(maxsize=1)
def format_rules():
    return json.loads(Path(__file__).with_name('plate_formats.json').read_text())


def format_evidence(text):
    matches = [p for p in format_rules()['profiles'] if re.fullmatch(p['pattern'], text)]
    best = max(matches, key=lambda p:p['rank']) if matches else {
        'name':'unrecognized_layout', 'rank':0,
        'description':'Layout not recognized by configured hints; retain for review, not automatically invalid'}
    return {'profile':best['name'], 'rank':best['rank'], 'description':best['description'],
            'rules_version':format_rules()['version'], 'registration_verified':False}


def assess_readings(readings, min_confidence=OCR_MIN_CONFIDENCE):
    """Apply the same acceptance rule to live OCR and saved-reading reviews."""
    variants = {r['variant']: r for r in readings}
    def plausible(r):
        text = r['text']
        return (6 <= len(text) <= 12 and any(c.isalpha() for c in text)
                and any(c.isdigit() for c in text))
    eligible = [variants[name] for name in ('bicubic', 'mild_clahe')
                     if name in variants and plausible(variants[name])
                     and variants[name]['confidence'] >= min_confidence]
    # Stable ordering keeps bicubic as the tie-breaker, rather than always
    # allowing its score/preference to overrule stronger structural evidence.
    formats = {name:format_evidence(r['text']) for name,r in variants.items()}
    selected = max(eligible, key=lambda r:formats[r['variant']]['rank']) if eligible else None
    selection_reason = ('stronger_plate_structure' if selected and selected != eligible[0]
                        else 'bicubic_preferred' if selected and selected['variant']=='bicubic'
                        else 'clahe_fallback' if selected else 'no_eligible_reading')
    nonempty = [variants[name] for name in ('bicubic', 'mild_clahe')
                if name in variants and variants[name]['text']]
    relation = ('agreement' if nonempty[0]['text'] == nonempty[1]['text'] else 'disagreement') if len(nonempty) == 2 else 'unavailable'
    status = ('primary_candidate' if selected['variant'] == 'bicubic' else 'fallback_candidate') if selected else (
        'below_confidence_threshold' if any(plausible(r) for r in nonempty)
        else 'invalid_candidate_structure' if nonempty else 'missing_or_empty_reading')
    return {'candidate':selected['text'] if selected else None,
            'selected_variant':selected['variant'] if selected else None,
            'selected_confidence':selected['confidence'] if selected else None,
            'variant_selection_reason':selection_reason, 'format_assessments':formats,
            'selected_format':formats[selected['variant']] if selected else None,
            'variant_relation':relation,
            'alternatives':[{'variant':r['variant'], 'text':r['text'], 'confidence':r['confidence']}
                            for r in nonempty if selected and r['text'] != selected['text']],
            'needs_confirmation':selected is not None,
            'status':status, 'min_confidence':min_confidence, 'selection_policy':OCR_SELECTION_POLICY}


def quality(image):
    import cv2
    import numpy as np
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h,w=gray.shape
    sharpness=float(cv2.Laplacian(gray,cv2.CV_64F).var())
    contrast=float(np.percentile(gray,95)-np.percentile(gray,5))
    bright=float(np.mean(gray>=250))
    score=float(min(w*h,30000)**.5 * np.log1p(sharpness) * min(contrast/80,1))
    reasons=[]
    if h<12 or w<24: reasons.append('too_few_native_pixels')
    if not .9 <= w/max(h,1) <= 6.5: reasons.append('implausible_plate_aspect')
    if contrast<18: reasons.append('low_contrast')
    if bright>.75 and contrast<60: reasons.append('mostly_saturated')
    return dict(width=w,height=h,sharpness=sharpness,contrast=contrast,
                saturated_fraction=bright,score=score,reject_reasons=reasons)


def rectify(image):
    """Use a large convex quadrilateral only when geometric checks pass; otherwise preserve original."""
    import cv2
    import numpy as np
    h,w=image.shape[:2]
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,50,150)
    contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours,key=cv2.contourArea,reverse=True):
        area=cv2.contourArea(contour)/(w*h)
        if not .60<=area<=.98: continue
        poly=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
        if len(poly)!=4 or not cv2.isContourConvex(poly): continue
        p=poly.reshape(4,2).astype('float32')
        center=p.mean(axis=0)
        p=p[np.argsort(np.arctan2(p[:,1]-center[1],p[:,0]-center[0]))]
        p=np.roll(p,-np.argmin(p.sum(axis=1)),axis=0)
        angles=[]
        for i in range(4):
            a=p[(i-1)%4]-p[i];b=p[(i+1)%4]-p[i]
            angles.append(float(np.degrees(np.arccos(np.clip(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9),-1,1)))))
        if min(angles)<50 or max(angles)>130: continue
        width=int(max(np.linalg.norm(p[1]-p[0]),np.linalg.norm(p[2]-p[3])))
        height=int(max(np.linalg.norm(p[3]-p[0]),np.linalg.norm(p[2]-p[1])))
        if width<20 or height<10: continue
        target=np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]],dtype='float32')
        corrected=cv2.warpPerspective(image,cv2.getPerspectiveTransform(p,target),(width,height),flags=cv2.INTER_CUBIC)
        return corrected,{'applied':True,'corners':p.tolist(),'method':'conservative_contour_quad'}
    return image,{'applied':False,'method':'no_valid_quadrilateral'}


def split_lines(image):
    """Find two distinct ink bands using row projection, with a single-line fallback."""
    import cv2
    import numpy as np
    h,w=image.shape[:2]
    if w/h>=2.7: return [image],{'layout':'single_line','reason':'wide_aspect'}
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    _,ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    if np.median(gray)<127: ink=255-ink
    border=max(1,int(w*.07))
    projection=(ink[:,border:w-border]>0).mean(axis=1)
    projection=np.convolve(projection,np.ones(3)/3,mode='same')
    lo,hi=int(h*.28),int(h*.72)
    if hi<=lo: return [image],{'layout':'single_line','reason':'too_short'}
    split=lo+int(np.argmin(projection[lo:hi]))
    top=projection[max(1,int(h*.08)):split]
    bottom=projection[split+1:int(h*.92)]
    if not len(top) or not len(bottom): return [image],{'layout':'single_line','reason':'no_bands'}
    peak=min(float(top.max()),float(bottom.max()))
    valley=float(projection[split])
    # Demand separated text bands and enough rows of ink on both sides.
    valid=peak>.12 and valley<peak*.45 and sum(top>peak*.6)>=h*.10 and sum(bottom>peak*.6)>=h*.10
    if not valid:
        return [image],{'layout':'single_line','reason':'no_clear_two_line_gap','valley':valley,'peak':peak}
    return [image[:split],image[split:]],{'layout':'two_lines','split_y':split,'valley':valley,'peak':peak}


class PlateReader:
    def __init__(self):
        from common import MODELS
        from paddleocr import TextRecognition
        self.model=TextRecognition(model_name='en_PP-OCRv5_mobile_rec',
            model_dir=str(MODELS/'en_PP-OCRv5_mobile_rec'),device='cpu',enable_mkldnn=False,cpu_threads=1)

    def read(self,image):
        import cv2
        rectified,geometry=rectify(image)
        enlarged=cv2.resize(rectified,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        lines,layout=split_lines(enlarged)
        variants=[('bicubic',lines)]
        # Contrast normalization is an alternative reading, not an overwrite of the source.
        enhanced=[]
        for line in lines:
            lab=cv2.cvtColor(line,cv2.COLOR_BGR2LAB)
            lab[:,:,0]=cv2.createCLAHE(clipLimit=1.5,tileGridSize=(4,4)).apply(lab[:,:,0])
            enhanced.append(cv2.cvtColor(lab,cv2.COLOR_LAB2BGR))
        variants.append(('mild_clahe',enhanced))
        readings=[]
        for name,images in variants:
            rows=[]
            for line in images:
                # Small replicated margins help avoid cutting the first/last stroke.
                padded=cv2.copyMakeBorder(line,4,4,4,4,cv2.BORDER_REPLICATE)
                result=list(self.model.predict(padded,batch_size=1))[0]
                rows.append({'raw':str(result['rec_text']),'confidence':float(result['rec_score'])})
            raw=''.join(row['raw'] for row in rows)
            text=re.sub('[^A-Z0-9]','',raw.upper())
            readings.append({'variant':name,'raw':raw,'text':text,
                             'confidence':min(row['confidence'] for row in rows),'lines':rows})
        return {'geometry':geometry,'layout':layout,'readings':readings,
                **assess_readings(readings)}


class BestFrames:
    """Collect distinct frames before selecting the highest-quality crop for OCR."""
    def __init__(self):
        self.entries={}

    def consider(self,key,sequence,crop,score,now):
        entry=self.entries.setdefault(key,{'samples':[],'last_read':-1e9,'best_read_score':0,'last_seen':now})
        entry['last_seen']=now
        same=[item for item in entry['samples'] if item[1]==sequence]
        if same and same[0][0]>=score: return None
        entry['samples']=[item for item in entry['samples'] if item[1]!=sequence]
        entry['samples'].append((score,sequence,crop.copy()))
        entry['samples']=entry['samples'][-3:]
        # Bounded memory; prevent thousands of expired tracks retaining native crops.
        if len(self.entries)>300:
            for old in sorted(self.entries,key=lambda k:self.entries[k]['last_seen'])[:100]: del self.entries[old]
        if len(entry['samples'])<2 or now-entry['last_read']<1.5: return None
        best=max(entry['samples'],key=lambda item:item[0])
        entry['samples']=[]
        entry['last_read']=now
        entry['best_read_score']=best[0]
        return best

    def flush_camera(self,camera_id,now):
        """Read a best single crop when a short encounter has ended; do not discard it."""
        pending=[]
        for key,entry in self.entries.items():
            if key[0]==camera_id and entry['samples'] and now-entry['last_seen']>=1.5:
                pending.append((key,max(entry['samples'],key=lambda item:item[0])))
                entry['samples']=[];entry['last_read']=now
        return pending


class Consensus:
    def __init__(self): self.observations=defaultdict(dict)

    def add(self,key,sequence,candidate):
        if candidate is None: return None
        self.observations[key][sequence]=candidate
        observations=self.observations[key]
        from collections import Counter
        counts=Counter(observations.values())
        text,support=counts.most_common(1)[0]
        if support>=3 and len(counts)==1:
            return {'candidate':text,'distinct_frame_support':support,'status':'repeated_candidate_needs_human_validation'}
        return None
