#!/usr/bin/env python3
"""
Generate publication-quality Venn diagram for theorem solving overlap.
Outputs PDF and PNG for LaTeX inclusion.
"""

import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn2_circles
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

# Numbers from leanpaper/main.tex Section 4.5 (Solved-Set Overlap).
# B-RL totals 55/244, A-RL totals 38/244 at k=16. Intersection = 35.
BOTH = 35              # Solved by both A-RL and B-RL
ONLY_STRUCTURED = 20   # Solved only by B-RL (skeleton schedule)
ONLY_BASELINE = 3      # Solved only by A-RL (i.i.d. baseline)

def create_venn_diagram(output_path: str = "venn_overlap"):
    """Create and save the Venn diagram."""

    fig, ax = plt.subplots(figsize=(6, 5))

    # Create Venn diagram
    # venn2 takes (Ab, aB, AB) = (only left, only right, both)
    v = venn2(
        subsets=(ONLY_STRUCTURED, ONLY_BASELINE, BOTH),
        set_labels=('B-RL (skeleton schedule)', 'A-RL (i.i.d. baseline)'),
        set_colors=('#4C72B0', '#DD8452'),
        alpha=0.7,
        ax=ax
    )

    # Add circles outline
    c = venn2_circles(
        subsets=(ONLY_STRUCTURED, ONLY_BASELINE, BOTH),
        linestyle='solid',
        linewidth=1.5,
        color='#333333',
        ax=ax
    )

    # Style the labels
    for text in v.set_labels:
        if text:
            text.set_fontsize(12)
            text.set_fontweight('bold')

    for text in v.subset_labels:
        if text:
            text.set_fontsize(14)
            text.set_fontweight('bold')

    # Totals
    ax.annotate(
        'Total: 55 (22.5%)',
        xy=(-0.4, -0.55),
        fontsize=10,
        ha='center',
        color='#4C72B0'
    )
    ax.annotate(
        'Total: 38 (15.6%)',
        xy=(0.4, -0.55),
        fontsize=10,
        ha='center',
        color='#DD8452'
    )

    ax.set_title(
        'Solved-set overlap on miniF2F-test (V1.5-RL, k=16)',
        fontsize=12,
        fontweight='bold',
        pad=15
    )

    plt.tight_layout()

    # Save in multiple formats
    fig.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight', format='pdf')
    fig.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight', format='png')
    print(f"Saved: {output_path}.pdf, {output_path}.png")

    plt.close()


def create_simple_venn(output_path: str = "venn_simple"):
    """Create a minimal version without annotations (for inline use)."""

    fig, ax = plt.subplots(figsize=(4, 3.5))

    v = venn2(
        subsets=(ONLY_STRUCTURED, ONLY_BASELINE, BOTH),
        set_labels=('B-RL\n(55 solved)', 'A-RL\n(38 solved)'),
        set_colors=('#4C72B0', '#DD8452'),
        alpha=0.7,
        ax=ax
    )

    venn2_circles(
        subsets=(ONLY_STRUCTURED, ONLY_BASELINE, BOTH),
        linestyle='solid',
        linewidth=1.2,
        color='#333333',
        ax=ax
    )

    for text in v.set_labels:
        if text:
            text.set_fontsize(10)

    for text in v.subset_labels:
        if text:
            text.set_fontsize(12)
            text.set_fontweight('bold')

    plt.tight_layout()
    fig.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight', format='pdf')
    fig.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight', format='png')
    print(f"Saved: {output_path}.pdf, {output_path}.png")
    plt.close()


if __name__ == "__main__":
    import os

    # Ensure we're in the figures directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    create_venn_diagram("venn_overlap")
    create_simple_venn("venn_simple")

    print("\nTo include in LaTeX:")
    print(r"  \includegraphics[width=0.6\textwidth]{figures/venn_overlap.pdf}")
