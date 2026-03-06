#!/usr/bin/env python3
"""
Generate resilience figures using local CSV data in submissions/data/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


GROUP_NO = "Dedicated group: No"
GROUP_YES = "Dedicated group: Yes"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate submission figures.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="Directory containing group_summary.csv and effect_summary.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "figures",
        help="Directory for generated figures.",
    )
    return parser.parse_args()


def save_composite_resilience_plot(group_summary: pd.DataFrame, output_dir: Path) -> None:
    plot_df = group_summary.copy()
    plot_df["resilience_score"] = (
        plot_df["transition_plan_yes_pct"] - plot_df["bus_single_point_risk_pct"]
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=plot_df,
        x="survey_year",
        y="resilience_score",
        hue="group_label",
        hue_order=[GROUP_NO, GROUP_YES],
        marker="o",
        linewidth=2.5,
        ax=ax,
    )
    ax.axhline(0, color="black", linewidth=1, alpha=0.5)
    ax.set_title("Composite Resilience Score by Team Structure")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Score (transition plan % minus bus-risk %)")
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(output_dir / "01_composite_resilience_by_group.png", dpi=200)
    plt.close(fig)


def save_advantage_components_plot(effect_summary: pd.DataFrame, output_dir: Path) -> None:
    melted = effect_summary.melt(
        id_vars="survey_year",
        value_vars=["transition_advantage_pp", "bus_risk_reduction_pp"],
        var_name="metric",
        value_name="percentage_points",
    )
    labels = {
        "transition_advantage_pp": "Transition-plan advantage",
        "bus_risk_reduction_pp": "Bus-risk reduction",
    }
    melted["metric"] = melted["metric"].map(labels)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=melted,
        x="survey_year",
        y="percentage_points",
        hue="metric",
        ax=ax,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Resilience Advantage of Dedicated Groups (Percentage Points)")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Advantage for dedicated groups (pp)")
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(output_dir / "02_resilience_advantage_components.png", dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    group_summary_path = data_dir / "group_summary.csv"
    effect_summary_path = data_dir / "effect_summary.csv"
    if not group_summary_path.exists():
        raise FileNotFoundError(f"Missing: {group_summary_path}")
    if not effect_summary_path.exists():
        raise FileNotFoundError(f"Missing: {effect_summary_path}")

    sns.set_theme(style="whitegrid", context="talk", palette="colorblind")

    group_summary = pd.read_csv(group_summary_path)
    effect_summary = pd.read_csv(effect_summary_path)

    save_composite_resilience_plot(group_summary, output_dir)
    save_advantage_components_plot(effect_summary, output_dir)

    print(f"Wrote: {output_dir / '01_composite_resilience_by_group.png'}")
    print(f"Wrote: {output_dir / '02_resilience_advantage_components.png'}")


if __name__ == "__main__":
    main()
