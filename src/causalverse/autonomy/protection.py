"""Read-only cumulative seal verification; no historical baseline regeneration."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def verify():
    base=ROOT/'artifacts/ai_s2/closeout_20261116_173046'
    inventory=base/'new_files_inventory.json'
    if sha(inventory)!='8ebeea2d784b21e1220dbe195df9dd354185762a3fdd61e0d6ffd2291ace6742':
        raise ValueError('HISTORICAL_INVENTORY_HASH')
    expected=json.loads((base/'protected_expected.json').read_text(encoding='utf-8'))
    expected.update({e['path']:e['sha256'] for e in json.loads(inventory.read_text(encoding='utf-8'))['entries']})
    result=dict(expected_count=len(expected),checked_count=0,changed_hashes=[],missing_files=[],unreadable_files=[],verification_errors=[])
    for name,h in expected.items():
        try:
            p=ROOT/name
            if not p.is_file():result['missing_files'].append(name);continue
            actual=sha(p);result['checked_count']+=1
            if actual!=h:result['changed_hashes'].append(name)
        except PermissionError:result['unreadable_files'].append(name)
        except Exception as ex:result['verification_errors'].append([name,type(ex).__name__])
    return result
