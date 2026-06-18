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

# Data from experiments
BOTH = 34          # Solved by both methods
ONLY_STRUCTURED = 19   # Solved only by Structured IR
ONLY_BASELINE = 3      # Solved only by Baseline

def create_venn_diagram(output_path: str = "venn_overlap"):
    """Create and save the Venn diagram."""

    fig, ax = plt.subplots(figsize=(6, 5))

    # Create Venn diagram
    # venn2 takes (Ab, aB, AB) = (only left, only right, both)
    v = venn2(
        subsets=(ONLY_STRUCTURED, ONLY_BASELINE, BOTH),
        set_labels=('Structured IR', 'Baseline'),
        set_colors=('#4C72B0', '#DD8452'),  # Seaborn-style blue and orange
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

    # Add totals annotation
    ax.annotate(
        f'Total: 53 (21.7%)',
        xy=(-0.4, -0.55),
        fontsize=10,
        ha='center',
        color='#4C72B0'
    )
    ax.annotate(
        f'Total: 37 (15.2%)',
        xy=(0.4, -0.55),
        fontsize=10,
        ha='center',
        color='#DD8452'
    )

    # Add statistical significance note
    ax.annotate(
        r"McNemar's test: $\chi^2$ = 10.23, p < 0.01",
        xy=(0, -0.72),
        fontsize=9,
        ha='center',
        style='italic',
        color='#555555'
    )

    # Title
    ax.set_title(
        'Theorem Solving Overlap on miniF2F (k=16)',
        fontsize=13,
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
        set_labels=('Structured IR\n(53 solved)', 'Baseline\n(37 solved)'),
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
