from src.pipeline import generate,validate,analyze

def test_keys_and_balances():
    loans,snapshots=generate(n=80)
    validate(loans,snapshots)
    assert len(snapshots)==960
    assert snapshots.ead.min()>=0

def test_roll_rows_sum_to_100():
    loans,snapshots=generate(n=400)
    monthly,segments,roll,latest=analyze(loans,snapshots)
    assert (abs(roll.sum(axis=1)-100)<1e-8).all()
    assert monthly.dq30_pct.between(0,100).all()
    assert monthly.exposure.gt(0).all()
    assert segments.exposure.sum()>0

def test_deterministic_generation():
    a,b=generate(n=25)
    c,d=generate(n=25)
    assert a.equals(c) and b.equals(d)
