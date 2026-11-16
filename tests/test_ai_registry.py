"""Frozen artifacts are read only; all corruptions target pytest temporary copies."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import pytest
from causalverse.ai_runtime.registry import Registry, ROOT
from causalverse.ai_runtime.contracts import AdmissionError


@pytest.fixture
def registry():
    return Registry()


@pytest.mark.parametrize('model_id', list(Registry().entries))
def test_registered_models(registry, model_id):
    entry = registry.entry(model_id)
    required = {'model_id','model_version','model_type','source_stage','parameter_path','parameter_sha256',
                'source_code_version','input_contract','supported_scope','calibration_reference',
                'training_data_reference','validation_test_reference','parameter_shapes','status'}
    assert required <= set(entry)
    assert registry.load(model_id)


def test_twenty_members_and_candidate_models(registry):
    for kind in ('action', 'delta'):
        a = registry.load('d511.' + kind)
        assert a['bootstrap_seeds'].shape == (20,20)
        for member in range(20):
            for block in (('model', 'base') if kind == 'delta' else ('model',)):
                for field in ('mean','scale','coef'):
                    assert f'{member}_{block}_{field}' in a
    a = registry.load('d511.candidate_support')
    assert len(a) == 880
    for kind in ('action','delta'):
        for cls in (0,4,11,14):
            for member in range(20):
                for block in (('model','base') if kind=='delta' else ('model',)):
                    for field in ('mean','scale','coef'):
                        assert f'{kind}_{cls}_{member}_{block}_{field}' in a


def test_var_scope_is_semantic(registry):
    with pytest.raises(AdmissionError, match='CONTRACT_MISMATCH'):
        registry.load('d4.var7', 'D512')
    assert registry.load('d512.var4','D512')['coef'].shape == (25,4)


@pytest.mark.parametrize('path',['../secret','/etc/passwd','C:/secret','artifacts\\secret'])
def test_registry_paths_cannot_escape(registry,path):
    with pytest.raises(AdmissionError,match='PATH_REJECTED'):registry.path(path)


def test_unregistered_source_rejected(registry):
    with pytest.raises(AdmissionError,match='PATH_REJECTED'):registry.trusted_bytes('unknown.npz')


@pytest.mark.parametrize('damage,code', [('hash','MODEL_HASH_MISMATCH'),('missing','FILE_MISSING'),
    ('key','PARAMETER_KEY_MISSING'),('shape','PARAMETER_SHAPE_ERROR'),
    ('dtype','PARAMETER_DTYPE_ERROR'),('nan','NONFINITE_PARAMETER'),('inf','NONFINITE_PARAMETER')])
def test_damaged_temporary_models(tmp_path, registry, damage, code):
    catalog = copy.deepcopy(registry.catalog)
    entry = next(e for e in catalog['models'] if e['model_id']=='d3.pca')
    # Trusted configuration injection is test-only; no online API accepts paths/catalogs.
    target = tmp_path / entry['parameter_path']
    target.parent.mkdir(parents=True)
    original = ROOT / entry['parameter_path']
    shutil.copyfile(original, target)
    shutil.copyfile(ROOT/'AI_PHASE3_M0_PREPARATION.md', tmp_path/'AI_PHASE3_M0_PREPARATION.md')
    entry['dependencies'] = []
    if damage=='hash':
        target.write_bytes(target.read_bytes()+b'changed')
    elif damage=='missing':
        target.unlink()
    else:
        with np.load(target, allow_pickle=False) as archive:
            arrays = {k:archive[k].copy() for k in archive.files}
        if damage=='key': del arrays['mean']
        if damage=='shape': arrays['mean'] = arrays['mean'][:-1]
        if damage=='dtype': arrays['mean'] = arrays['mean'].astype(np.float32)
        if damage in ('nan','inf'): arrays['mean'][0] = np.nan if damage=='nan' else np.inf
        np.savez(target,**arrays)
        entry['parameter_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(AdmissionError, match=code):
        Registry(tmp_path,catalog).load('d3.pca')


def test_no_training_calibration_or_simulator_import(registry):
    calls=[]
    def guard(frame,event,arg):
        if event=='call' and (frame.f_code.co_name in ('fit','calibrate','set_control','inject_fault') or
                              'causalverse/simulation' in frame.f_code.co_filename.replace('\\','/')):
            calls.append(frame.f_code.co_name)
            raise AssertionError('forbidden call')
    old=sys.getprofile()
    try:
        sys.setprofile(guard)
        for mid in registry.entries: registry.load(mid)
    finally: sys.setprofile(old)
    assert calls==[]
    assert 'causalverse.simulation' not in sys.modules
