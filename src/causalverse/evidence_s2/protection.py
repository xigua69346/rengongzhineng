"""S2 adds files; accepted S1.1 source and every sealed artifact remain unchanged."""
import hashlib,json,os
from pathlib import Path
from causalverse.evidence_s1.service import digest,write_new

def verify(root,output):
    root=Path(root);s1=root/'artifacts/ai_s1_acceptance/s1_20261116_102936_452b6431'
    s11=root/'artifacts/ai_s1_1/s1_1_20261116';supp=root/'artifacts/ai_s1_supplement/s1_final_20261116_133423'
    assert digest(s1/'protection_final.json')=='d55a4089a89e0472ed9b87e7e13248e07488bb1ff80982b8bda75847cfbf6923'
    assert digest(s1/'new_files_inventory.json')=='08f8c1b002173b0000aa193bfd22f9df4fc45ee6142e0506f99f05508db728f4'
    assert digest(s11/'new_files_inventory.json')=='7f11bae85ed67323499b54925236f44f6646a1a324299d5e6aabfb0859ab560c'
    original=json.loads((s1/'protection_final.json').read_text(encoding='utf8'))['expected']
    sets={'original_8992':original}
    for label,base in [('s1_572',s1),('s11_717',s11),('supplement_53',supp)]:
        name='supplement_inventory.json' if label=='supplement_53' else 'new_files_inventory.json'
        sets[label]={e['path']:e['sha256'] for e in json.loads((base/name).read_text(encoding='utf8'))['entries']}
    transition={e['path']:e for e in json.loads((root/'src/causalverse/evidence_s1/release_v11.json').read_text())['authorized_changes']}
    result={};known=set()
    for label,expected in sets.items():
        r=dict(expected_count=len(expected),checked_count=0,changed_hashes=[],missing_files=[],verification_errors=[],accepted_s11_transitions=[])
        for name,h in expected.items():
            known.add(name)
            try:
                actual=digest(root/name);r['checked_count']+=1
                if actual!=h:
                    if label=='s1_572' and name in transition and transition[name]['before_sha256']==h and transition[name]['after_sha256']==actual:r['accepted_s11_transitions'].append(name)
                    else:r['changed_hashes'].append(name)
            except FileNotFoundError:r['missing_files'].append(name)
            except Exception:r['verification_errors'].append(name)
        result[label]=r
    for p in (s1/'new_files_inventory.json',s1/'inventory_seal.json',s11/'new_files_inventory.json',s11/'inventory_seal.json',supp/'supplement_inventory.json',supp/'supplement_seal.json'):known.add(p.relative_to(root).as_posix())
    unknown=[]
    allowed=('artifacts/ai_s1_runs/','artifacts/ai_s2/','artifacts/ai_s2_runs/','src/causalverse/evidence_s2/','s2_tests/')
    for base in ('artifacts','src','frontend','docs','scripts','experiments','tests','s1_tests','s1_1_tests','s2_tests','build','dist'):
        for folder,dirs,files in os.walk(root/base):
            dirs[:]=[d for d in dirs if d not in ('node_modules','__pycache__','.git','.pytest_cache','.vite','.svelte-kit')]
            for name in files:
                p=Path(folder)/name;rel=p.relative_to(root).as_posix()
                if rel not in known and not rel.startswith(allowed):unknown.append(rel)
    for p in root.iterdir():
        if p.is_file() and p.name not in known and p.name!='AI_PHASE3_S2_REPORT.md':unknown.append(p.name)
    result['unknown_files']=unknown
    write_new(Path(output),result)
    if unknown or any(r[k] for label,r in result.items() if label!='unknown_files' for k in ('changed_hashes','missing_files','verification_errors')):raise RuntimeError('PROTECTION_STOP')
    return result
