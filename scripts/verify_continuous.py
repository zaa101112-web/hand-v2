"""Reproducible synthetic benchmark. It does not claim human recognition accuracy."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tests.continuous_samples import run_continuous_case

cases=[run_continuous_case(interval,noise,seed) for interval in (20,33,50,66)
       for noise in (0,1.0) for seed in (7,42,101)]
totals={key:sum(c[key] for c in cases) for key in ('expected','recognized','executed','missed','wrong','duplicates','blocked_or_failed')}
report=dict(source='SYNTHETIC_LANDMARKS',cases=cases,totals=totals,
    passed=all(c['passed'] and not c['owned_keys'] for c in cases),
    real_hand_accuracy='NOT_RUN',real_chrome_effects='NOT_RUN',
    coverage='24 authored mixed sequences, 15–50fps, 0/1px rigid jitter, 10 steps each; shape and motion templates are synthetic. No pose/lighting/user diversity claim.')
path=ROOT/'docs/validation/m09-continuous-replay.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=report['passed'],totals=totals,path=str(path)),ensure_ascii=True))
raise SystemExit(0 if report['passed'] else 1)
