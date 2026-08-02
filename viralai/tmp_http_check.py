import json
import urllib.request

urls = [
    'http://127.0.0.1:8001/health',
    'http://127.0.0.1:8001/openapi.json',
    'http://127.0.0.1:8001/benchmark/datasets',
    'http://127.0.0.1:8001/benchmark/latest',
]
for url in urls:
    try:
        resp = urllib.request.urlopen(url)
        data = resp.read().decode('utf-8')
        print(url, '=>', resp.getcode(), data[:500])
    except Exception as exc:
        print(url, 'ERROR', exc)
