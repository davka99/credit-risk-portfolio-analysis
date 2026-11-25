"""README figure: share of exposure vs share of the loss proxy per risk segment.

Reads reports/segment_kpis.csv (written by ``python -m src.pipeline``) and writes
assets/loss_vs_exposure_by_segment.png. Needs matplotlib, which is not in
requirements.txt because the pipeline and the tests do not use it:

    python -m pip install matplotlib
    python -m src.readme_figures
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports' / 'segment_kpis.csv'
OUT = ROOT / 'assets' / 'loss_vs_exposure_by_segment.png'

INK = '#182B42'
MUTED = '#64748B'
EXPOSURE_COLOR = '#A9B8C8'
LOSS_COLOR = '#182B42'


def shares(segments: pd.DataFrame) -> pd.DataFrame:
    """Share of December exposure and of the illustrative loss proxy, in percent."""
    out = segments[['segment']].copy()
    out['exposure_share'] = segments.exposure / segments.exposure.sum() * 100
    out['loss_share'] = segments.ecl / segments.ecl.sum() * 100
    return out.reset_index(drop=True)


def main() -> None:
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    data = shares(pd.read_csv(SOURCE))
    order = ['Subprime', 'Near-prime', 'Prime']  # top to bottom
    data = data.set_index('segment').loc[order[::-1]].reset_index()

    fig, ax = plt.subplots(figsize=(8.4, 3.9), dpi=200)
    y = range(len(data))
    height = .36
    ax.barh([i + height / 2 for i in y], data.exposure_share, height=height - .04,
            color=EXPOSURE_COLOR, label='Share of exposure')
    ax.barh([i - height / 2 for i in y], data.loss_share, height=height - .04,
            color=LOSS_COLOR, label='Share of loss proxy')
    for i, row in data.iterrows():
        ax.text(row.exposure_share + .8, i + height / 2, f'{row.exposure_share:.0f} %',
                va='center', fontsize=9, color=MUTED)
        ax.text(row.loss_share + .8, i - height / 2, f'{row.loss_share:.0f} %',
                va='center', fontsize=9, color=INK, fontweight='bold')

    ax.set_yticks(list(y), data.segment, fontsize=10, color=INK)
    ax.set_xlim(0, 60)
    ax.set_xlabel('Share of the December 2025 portfolio (%)', color=MUTED, fontsize=9)
    ax.tick_params(axis='x', colors=MUTED, labelsize=9)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='x', color='#E5EAF0', linewidth=.8)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9,
              borderaxespad=.2, handlelength=1.2)

    fig.suptitle('Near-prime carries the largest share of the expected loss',
                 x=.02, ha='left', fontsize=12.5, fontweight='bold', color=INK)
    fig.text(.02, .875, 'Synthetic portfolio, December 2025. Loss proxy = balance × PD × LGD.',
             ha='left', fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, .93))
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, facecolor='white')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
