"""Cumulative historical protection, anchored to the accepted P0-04 inventory."""
import json
from pathlib import Path
from .service import digest, write_new

PLAN_HASH = '1861def8ed90acc2f6082829d635629e7b9b66af9b71c9b92275baa2861c3645'
INVENTORY_HASH = '5a2e324da592145a3f8e01145f175700e5dd484912db4f23c3f5b4d3a87f7a5b'

def check(root, output):
    root = Path(root)
    folder = root / 'artifacts/ai_p0_acceptance/p0_04_20261115_223237_9b309664'
    inv = folder / 'new_files_inventory.json'
    if digest(inv) != INVENTORY_HASH:
        raise RuntimeError('PROTECTION_INVENTORY_HASH')
    expected = {e['path']: e['sha256'] for e in json.loads((folder / 'protected_expected.json').read_text(encoding='utf-8'))}
    for e in json.loads(inv.read_text(encoding='utf-8'))['entries']:
        if e['path'] in expected and expected[e['path']] != e['sha256']:
            raise RuntimeError('PROTECTION_SCOPE_CONFLICT')
        expected[e['path']] = e['sha256']
    expected[inv.relative_to(root).as_posix()] = INVENTORY_HASH
    expected['AI_DEEPSEEK_INTEGRATION_PLAN.md'] = PLAN_HASH
    if len(expected) != 8992:
        raise RuntimeError('PROTECTION_COUNT')
    differences = [p for p, h in expected.items() if not (root / p).is_file() or digest(root / p) != h]
    allowed = ('src/causalverse/evidence_s1/', 's1_tests/', 'artifacts/ai_s1_acceptance/', 'artifacts/ai_s1_runs/')
    unknown = []
    for base in ('artifacts', 'src', 'frontend', 'docs', 'scripts', 'experiments', 'tests', 'build', 'dist', 's1_tests'):
        for p in (root / base).rglob('*'):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and not any(x in p.parts for x in ('node_modules', '__pycache__', '.git', '.pytest_cache', '.vite', '.svelte-kit')):
                if rel not in expected and not rel.startswith(allowed):
                    unknown.append(rel)
    for p in root.iterdir():
        if p.is_file() and p.name not in expected and p.name != 'AI_PHASE3_S1_REPORT.md':
            unknown.append(p.name)
    report = dict(protected_count=len(expected), differences=differences, unknown=unknown,
                  expected=expected, plan_sha256=PLAN_HASH)
    write_new(Path(output), report)
    if differences or unknown:
        raise RuntimeError('PROTECTION_STOP')
    return report
