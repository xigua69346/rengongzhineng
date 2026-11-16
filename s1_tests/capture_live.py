"""Read-only check of the old site; real HTTP acceptance of the new sidecar."""
import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import urllib.request
from causalverse.evidence_s1.service import write_new

def old_site():
    results = {}
    for path in ('/', '/api/runs', '/api/research'):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8768'+path, timeout=15) as r:
                body = r.read()
                results[path] = dict(status=r.status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        except Exception as exc:
            results[path] = dict(status='UNAVAILABLE', error=type(exc).__name__)
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--sidecar', action='store_true')
    args = p.parse_args()
    result = dict(old_site=old_site())
    if args.sidecar:
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def get(path):
            return json.load(client.open('http://127.0.0.1:8769'+path, timeout=60))
        csrf = get('/api/session')['csrf']
        result['health'] = get('/api/health')
        catalog = get('/api/catalog')
        result['contexts'] = []
        for chain in ('D3','D511'):
            case = next(c for c in catalog if c['chain'] == chain)
            req = urllib.request.Request('http://127.0.0.1:8769/api/contexts',
                data=json.dumps(dict(selection_id=case['selection_id'],as_of=5400,window=1800)).encode(),
                headers={'Content-Type':'application/json','X-CSRF-Token':csrf})
            context = json.load(client.open(req, timeout=120))
            assert get('/api/contexts/'+context['context_id']) == context
            assert get('/api/evidence/'+context['evidence'][0]['evidence_id']) == context['evidence'][0]
            result['contexts'].append(context)
    write_new(Path(args.output), result)
    print(json.dumps(dict(old_site=result['old_site'], contexts=[(c['chain'],c['context_id']) for c in result.get('contexts',[])])))

if __name__ == '__main__':
    main()
