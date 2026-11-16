"""Seal the fixed S1 delivery after a successful cumulative historical check."""
import argparse
import json
from pathlib import Path
from causalverse.evidence_s1.service import digest, write_new

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--batch',required=True)
    args=p.parse_args()
    root=Path.cwd()
    batch=root/args.batch
    protection=json.loads((batch/'protection_final.json').read_text(encoding='utf-8'))
    assert protection['protected_count']==8992 and not protection['differences'] and not protection['unknown']
    inventory=batch/'new_files_inventory.json'
    seal=batch/'inventory_seal.json'
    paths=[root/'AI_PHASE3_S1_REPORT.md']
    for folder in ('src/causalverse/evidence_s1','s1_tests','artifacts/ai_s1_acceptance','artifacts/ai_s1_runs'):
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    entries=[dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
             for p in sorted(set(paths)) if p not in (inventory,seal)]
    write_new(inventory,dict(stage='S1',entries=entries,
        self_excluded=[inventory.relative_to(root).as_posix(),seal.relative_to(root).as_posix()],
        live_append_policy='Files created by subsequent console requests are outside this sealed cutoff.'))
    result=dict(inventory_sha256=digest(inventory),report_sha256=digest(root/'AI_PHASE3_S1_REPORT.md'),
                entries=len(entries),protected_count=8992,protection_final_sha256=digest(batch/'protection_final.json'))
    write_new(seal,result)
    print(json.dumps(result))

if __name__=='__main__':
    main()
