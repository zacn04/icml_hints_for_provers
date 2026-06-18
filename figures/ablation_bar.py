#!/usr/bin/env python3
"""
Diversity ablation at k=16: bar chart of the structural-content gradient.
C2 (irrelevant comments) < A-RL = C1 (paraphrase) < C3 (NL-only) < B-RL (skeletons).
Numbers from paper Table 2 and Section 4.4 (C3).
"""
import os
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
matplotlib.rcParams['axes.spines.top'] = False
matplotlib.rcParams['axes.spines.right'] = False

LABELS = [
    'C2\nirrelevant\ncomments',
    'A-RL\ni.i.d.\nbaseline',
    'C1\ninstruction\nparaphrases',
    'C3\nNL goal\nhints only',
    'B-RL\ntactic\nskeletons',
]
SOLVED = [25, 38, 38, 48, 55]
TOTAL = 244

GREY_LIGHT = '#bbbbbb'
GREY_MID = '#888888'
BLUE = '#4C72B0'
ORANGE = '#DD8452'
RED = '#C44E52'

COLORS = [RED, GREY_MID, GREY_MID, ORANGE, BLUE]


def plot(output_path: str = "ablation"):
    fig, ax = plt.subplots(figsize=(7.0, 4.0))

    bars = ax.bar(LABELS, SOLVED, color=COLORS, edgecolor='#333', linewidth=0.8,
                  width=0.7)

    ax.axhline(y=38, color=GREY_LIGHT, linestyle='--', linewidth=0.9, zorder=0)
    ax.annotate('baseline (38)', xy=(4.4, 38), xytext=(4.55, 38),
                fontsize=8, color=GREY_MID, va='center')

    for bar, val in zip(bars, SOLVED):
        pct = 100 * val / TOTAL
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f'{val}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel(f'Theorems solved at k=16 (of {TOTAL})', fontsize=10)
    ax.set_ylim(0, 64)
    ax.set_xlim(-0.6, len(LABELS) - 0.4)

    ax.tick_params(axis='x', labelsize=9)
    ax.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.6)
    ax.set_axisbelow(True)

    ax.set_title('Diversity ablation: structural content drives the gain',
                 fontsize=11, fontweight='bold', pad=12)

    plt.tight_layout()
    fig.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight')
    fig.savefig(f'{output_path}.png', dpi=200, bbox_inches='tight')
    print(f'Saved: {output_path}.pdf, {output_path}.png')
    plt.close()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot('ablation')
