"""Package the rendered benchmark and referenced assets for static hosting."""
import argparse
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote


class References(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.paths = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                url = urlsplit(value)
                if not url.scheme and not url.netloc and url.path:
                    self.paths.add(unquote(url.path))


def package(run, output):
    output.mkdir(parents=True, exist_ok=False)
    pages = ['report.html', 'benchmark_report.html', 'ocr_report.html',
             'preprocessing_report.html', 'encounter_report.html', 'cross_camera_report.html']
    assets = set()
    for name in pages:
        text = (run/name).read_text()
        text = text.replace('<a href="encounters.sqlite3">SQLite database</a> · ', '')
        text = text.replace('<head>', '<head><meta name="robots" content="noindex,nofollow">')
        # Keep report tables accessible on narrow screens without shrinking evidence.
        text = text.replace('</head>', '<style>body{overflow-wrap:anywhere}article{overflow-x:auto}nav{line-height:1.9}</style></head>')
        (output/name).write_text(text)
        assets.update(References(text).paths)
    assets.update(['validation.json'])
    for name in assets-set(pages):
        source = (run/name).resolve()
        if not source.is_relative_to(run.resolve()) or source.suffix not in ('.json', '.png', '.jpg', '.md'):
            raise ValueError(f'Unexpected public asset: {name}')
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(output/'report.html', output/'index.html')
    (output/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    config = {'version':2, 'framework':None, 'buildCommand':None, 'installCommand':None,
              'outputDirectory':'.', 'cleanUrls':False,
              'headers':[{'source':'/(.*)', 'headers':[
                  {'key':'X-Robots-Tag','value':'noindex, nofollow'},
                  {'key':'X-Content-Type-Options','value':'nosniff'},
                  {'key':'Referrer-Policy','value':'no-referrer'}]}]}
    (output/'vercel.json').write_text(json.dumps(config, indent=2)+'\n')
    for page in output.glob('*.html'):
        for name in References(page.read_text()).paths:
            if not (output/name).is_file(): raise ValueError(f'Missing public asset: {name}')
    files = [p for p in output.rglob('*') if p.is_file()]
    print(json.dumps({'output':str(output), 'files':len(files),
                      'size_mb':round(sum(p.stat().st_size for p in files)/2**20, 2)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package(args.run.resolve(), args.output.resolve())
