from pathlib import Path
from causalverse.data.manifest import write_json,digest
from causalverse.causal.dynamic import NAMES,PARENTS

root=Path('artifacts/d4');root.mkdir(parents=True,exist_ok=True)
if (root/'protocol.json').exists():raise FileExistsError('D4 protocol frozen')
protected=[Path('src/causalverse/simulation/adapter.py'),*Path('artifacts/d3').rglob('*.json'),*Path('artifacts/d3/dataset/processed').glob('*.npz')]
write_json(root/'protected_before.json',{str(p):digest(p) for p in protected})
write_json(root/'protocol.json',dict(nodes=NAMES,parents=PARENTS,dt_seconds=10,lags=[1,3,6],ridge=[.1,10.],
    windows_seconds=[600,1800,3600],window_start=3600,normal_warmup=1800,
    diagnostic_trigger='fixed experiment clock; not an unknown-onset online detector',
    model_selection='normal validation one-step normalized MSE; train fits only',
    ambiguity='class-conditional split conformal alpha .1; singleton only certain; empty OOD; multiple ambiguous',
    pair_seeds=[dict(split=split,seed=base+i) for split,base,n in [('train',410000,4),('validation',420000,3),('test',430000,5)] for i in range(n)],
    intervention=dict(fault_at=3600,action_at=5400,duration=120,deltas=[0,1,5],end=6000),
    discovery='normal train per-run conditional Granger OLS F-test; BH FDR .05; no claims physical graph truth',
    bootstrap_runs=500))
edges=[]
for target,parents in enumerate(PARENTS):
    for source in parents:
        if source==target:basis='状态记忆/控制保持'
        elif target in (5,6):basis='controllers.py ctrl10/18 或 ctrl17/4反馈路径'
        elif (source,target)==(5,1):basis='命令→潜在阀位→潜在流量→水侧能量平衡'
        elif (source,target) in ((0,1),(1,0)):basis='qur耦合釜体与水侧能量平衡'
        else:basis='物料/能量/容积的候选约化路径，未单独识别'
        edges.append(dict(source=NAMES[source],target=NAMES[target],lag_seconds=[10,20,30,40,50,60],basis=basis,experimental_evidence='总路径实验，非独立边效应' if (source,target)==(5,1) else '未独立干预验证'))
write_json(root/'process_graph.json',dict(nodes=NAMES,edges=edges,latent=['coolant_inlet','valve_position','coolant_flow','composition/reaction_state'],warning='Reduced local graph, not identified truth'))
