import pandas as pd

from src.readme_figures import SOURCE, shares


def test_shares_sum_to_100_and_match_readme():
    data = shares(pd.read_csv(SOURCE)).set_index('segment')
    assert abs(data.exposure_share.sum() - 100) < 1e-9
    assert abs(data.loss_share.sum() - 100) < 1e-9
    # README: Near-prime holds 36% of exposure but 47% of the loss proxy.
    assert round(data.loc['Near-prime', 'exposure_share']) == 36
    assert round(data.loc['Near-prime', 'loss_share']) == 47
    assert round(data.loc['Subprime', 'loss_share']) == 34
