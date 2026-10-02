"""Bounded preprocessing comparison on real crops; never selects a confirmed identity."""
import html
import time
from common import MODELS, RUNS, save_json


def variants(image):
    import cv2
    yield 'original', image
    cubic = cv2.resize(image, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    yield 'bicubic_4x', cubic
    yield 'lanczos_4x', cv2.resize(image, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(cubic, cv2.COLOR_BGR2GRAY)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4)).apply(gray)
    yield 'clahe_4x', cv2.cvtColor(contrast, cv2.COLOR_GRAY2BGR)
    blur = cv2.GaussianBlur(cubic, (0,0), .8)
    yield 'mild_sharpen_4x', cv2.addWeighted(cubic, 1.4, blur, -.4, 0)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    yield 'otsu_4x', cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 7)
    yield 'adaptive_threshold_4x', cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)


def main():
    import cv2
    from paddleocr import TextRecognition
    inputs = [
        ('combined_nano', 'cam06_0000_000_p0'),
        ('combined_nano', 'cam06_0001_000_p0'),
        ('combined_nano', 'cam06_0002_000_p0'),
        ('combined_small', 'cam15_0000_004_p0'),
    ]
    output = RUNS/'preprocess_experiment'
    output.mkdir(exist_ok=True)
    results = []
    for model_name in ('en_PP-OCRv5_mobile_rec', 'PP-OCRv5_server_rec'):
        model = TextRecognition(model_name=model_name, model_dir=str(MODELS/model_name),
                                device='cpu', enable_mkldnn=False, cpu_threads=2)
        def read(image):
            r=list(model.predict(image, batch_size=1))[0]
            return {'text': str(r['rec_text']), 'confidence': float(r['rec_score'])}
        for run, crop_id in inputs:
            path=RUNS/run/'crops'/f'{crop_id}.jpg'
            image=cv2.imread(str(path))
            if image is None:
                raise FileNotFoundError(path)
            for name, processed in variants(image):
                filename=f'{crop_id}_{name}.png'
                cv2.imwrite(str(output/filename), processed)
                start=time.perf_counter()
                readings={'whole': read(processed)}
                if image.shape[1]/image.shape[0]<2.5 and image.shape[0]>=24:
                    mid=processed.shape[0]//2
                    top,bottom=read(processed[:mid]),read(processed[mid:])
                    readings['two_line_midpoint']={
                        'text': top['text']+bottom['text'],
                        'confidence': min(top['confidence'],bottom['confidence']),
                        'top': top, 'bottom': bottom}
                results.append({'source':str(path.relative_to(RUNS)), 'model':model_name,
                                'variant':name, 'image':filename, 'readings':readings,
                                'ocr_ms':(time.perf_counter()-start)*1000})
            print(model_name, crop_id, 'complete', flush=True)
        del model
    save_json(output/'results.json', {'ground_truth':None, 'results':results,
              'note':'Exploratory four-crop test. OCR confidence changes do not establish accuracy. Multiple transformations of one frame are not independent temporal evidence.'})
    page=['<!doctype html><meta charset="utf-8"><title>OCR preprocessing experiment</title>',
          '<style>body{font:15px system-ui;margin:32px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:10px}img{max-width:240px;max-height:132px}small{color:#555}</style>',
          '<h1>OCR preprocessing: actual camera crops</h1><p>Exploratory comparison, no confirmed labels. Scores are model confidence, not measured accuracy. Alternate variants are not independent observations.</p>',
          '<table><tr><th>Source / preprocessing</th><th>Image</th><th>Model</th><th>Whole plate</th><th>Two-line hypothesis</th></tr>']
    for r in results:
        def fmt(x): return html.escape(x['text'] or '∅')+f" <small>({x['confidence']:.2f})</small>" if x else '—'
        page.append(f'<tr><td>{html.escape(r["source"])}<br><b>{r["variant"]}</b></td><td><img src="{r["image"]}"></td><td>{r["model"]}</td><td>{fmt(r["readings"]["whole"])}</td><td>{fmt(r["readings"].get("two_line_midpoint"))}</td></tr>')
    page.append('</table>')
    (output/'report.html').write_text('\n'.join(page))
    print(output/'report.html')


if __name__ == '__main__':
    main()
