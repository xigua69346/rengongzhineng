"""Keep original ledgers; permit only the explicit S1.1 source transition."""
import json
from pathlib import Path
from .service import digest,write_new

def check(root,output):
    root=Path(root);old=root/'artifacts/ai_s1_acceptance/s1_20261116_102936_452b6431'
    assert digest(old/'protection_final.json')=='d55a4089a89e0472ed9b87e7e13248e07488bb1ff80982b8bda75847cfbf6923'
    assert digest(old/'new_files_inventory.json')=='08f8c1b002173b0000aa193bfd22f9df4fc45ee6142e0506f99f05508db728f4'
    original=json.loads((old/'protection_final.json').read_text(encoding='utf8'))['expected']
    sealed={e['path']:e['sha256'] for e in json.loads((old/'new_files_inventory.json').read_text(encoding='utf8'))['entries']}
    release=json.loads((Path(__file__).parent/'release_v11.json').read_text(encoding='utf8'))
    allowed={e['path']:e for e in release['authorized_changes']}
    assert set(allowed)=={'src/causalverse/evidence_s1/'+p for p in ('service.py','gateway.py','console/index.html','console/app.js','console/style.css')}
    errors=[];changes=[]
    for name,expected in {**sealed,**original}.items():
        try:actual=digest(root/name)
        except OSError:errors.append(name);continue
        if name in allowed:
            assert name not in original and expected==allowed[name]['before_sha256']
            if actual==allowed[name]['after_sha256']:changes.append(name)
            else:errors.append(name)
        elif actual!=expected:errors.append(name)
    result=dict(expected_count=8992,sealed_count=572,authorized_changes=changes,unexpected_changes=errors)
    write_new(Path(output),result)
    if errors:raise RuntimeError('PROTECTION_STOP')
    return result
