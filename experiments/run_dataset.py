import argparse,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from causalverse.data.manifest import freeze_plan,write_json
from causalverse.data.generator import generate_one

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='artifacts/d3/dataset');ap.add_argument('--freeze',action='store_true');args=ap.parse_args()
    root=Path(args.root); root.mkdir(parents=True,exist_ok=True)
    if args.freeze:
        freeze_plan(root/'split_plan.json'); print('Plan frozen; run without --freeze to generate.');return
    plan=json.loads((root/'split_plan.json').read_text()); started=time.perf_counter(); records=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        fs=[pool.submit(generate_one,str(root),plan,s) for s in plan['runs']]
        for f in as_completed(fs):
            try: records.append(f.result())
            except Exception as e: records.append(dict(status='failed',error=repr(e)))
            write_json(root/'generation_log.json',dict(elapsed_seconds=time.perf_counter()-started,runs=records))
            print(len(records),records[-1],flush=True)
    if any(r['status']!='complete' for r in records): raise SystemExit('Generation failures retained; evaluation must stop')

if __name__=='__main__':main()
