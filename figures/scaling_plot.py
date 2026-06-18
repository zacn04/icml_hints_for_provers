#!/usr/bin/env python3
"""
Scaling plot: A-RL (i.i.d. baseline) vs B-RL (skeleton schedule) on
DeepSeek-Prover-V1.5-RL, miniF2F-test. Numbers from Table 1 of the paper.
"""
import os
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
matplotlib.rcParams['axes.spines.top'] = False
matplotlib.rcParams['axes.spines.right'] = False

K = [16, 32, 64]
A_RL = [38, 42, 42]
B_RL = [55, 58, 60]
TOTAL = 244

BLUE = '#4C72B0'
ORANGE = '#DD8452'
GREY = '#666666'


def plot(output_path: str = "scaling"):
    fig, ax = plt.subplots(figsize=(6.5, 4.0))

    ax.fill_between(K, A_RL, B_RL, color=BLUE, alpha=0.08, label='_nolegend_')

    ax.plot(K, A_RL, marker='o', markersize=7, linewidth=2,
            color=ORANGE, label='A-RL (i.i.d. baseline)')
    ax.plot(K, B_RL, marker='s', markersize=7, linewidth=2,
            color=BLUE, label='B-RL (skeleton schedule)')

    for k, y in zip(K, A_RL):
        ax.annotate(f'{y}', xy=(k, y), xytext=(0, -16),
                    textcoords='offset points', ha='center',
                    fontsize=10, color=ORANGE, fontweight='bold')
    for k, y in zip(K, B_RL):
        ax.annotate(f'{y}', xy=(k, y), xytext=(0, 10),
                    textcoords='offset points', ha='center',
                    fontsize=10, color=BLUE, fontweight='bold')

    ax.annotate(
        'plateau (k=32 -> k=64\nadds zero theorems)',
        xy=(64, 42), xytext=(56, 32),
        fontsize=9, color=GREY, ha='center',
        arrowprops=dict(arrowstyle='->', color=GREY, lw=0.8,
                        connectionstyle="arc3,rad=0.2"),
    )

    ax.set_xticks(K)
    ax.set_xticklabels([f'k={k}' for k in K])
    ax.set_ylabel(f'Theorems solved (of {TOTAL})', fontsize=10)
    ax.set_xlabel('Sampling budget', fontsize=10)
    ax.set_ylim(25, 68)
    ax.set_xlim(13, 67)

    ax.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.6)
    ax.set_axisbelow(True)

    leg = ax.legend(loc='upper left', frameon=False, fontsize=10)

    ax.set_title('Mode-collapse plateau on miniF2F-test (V1.5-RL)',
                 fontsize=11, fontweight='bold', pad=12)

    plt.tight_layout()
    fig.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight')
    fig.savefig(f'{output_path}.png', dpi=200, bbox_inches='tight')
    print(f'Saved: {output_path}.pdf, {output_path}.png')
    plt.close()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    plot('scaling')
