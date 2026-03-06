#!/usr/bin/env python3
"""
Longitudinal analysis for the RSE survey (2016, 2017, 2018, 2022).

The analysis focuses on one cross-year question:
"Do dedicated RSE groups correlate with better software resilience?"

It uses three variables that exist in all four survey waves:
- currentWork2_0: dedicated RSE group membership
- stability2_0: presence of a transition plan when developers leave
- stability1_0: bus factor
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


YEARS: tuple[int, ...] = (2016, 2017, 2018, 2022)

COL_RSE = "rse1_0"
COL_GROUP = "currentWork2_0"
COL_TRANSITION = "stability2_0"
COL_BUS = "stability1_0"
COL_COUNTRY = "socio1_0"

GROUP_NO = "Dedicated group: No"
GROUP_YES = "Dedicated group: Yes"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create longitudinal summary stats and figures for the RSE survey."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to RSE_survey_longitudinal repository root.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
        help="Directory where figures and CSV summaries will be saved.",
    )
    return parser.parse_args()


def _to_binary_value(value: object) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (bool, np.bool_)):
        return float(value)
    if isinstance(value, (int, float, np.number)):
        if value in (0, 1):
            return float(value)
        return np.nan
    as_text = str(value).strip().lower()
    if as_text in {"true", "yes", "y", "1"}:
        return 1.0
    if as_text in {"false", "no", "n", "0"}:
        return 0.0
    return np.nan


def to_binary(series: pd.Series) -> pd.Series:
    return series.map(_to_binary_value)


def pct_true(series: pd.Series) -> float:
    valid = series.dropna()
    if valid.empty:
        return np.nan
    return float(valid.mean() * 100.0)


def ensure_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    frame = frame.copy()
    for col in columns:
        if col not in frame.columns:
            frame[col] = np.nan
    return frame


def load_year_dataframe(repo_root: Path, year: int) -> pd.DataFrame:
    year_path = repo_root / str(year) / f"{year}_tf.csv"
    if not year_path.exists():
        raise FileNotFoundError(f"Missing expected file: {year_path}")

    raw = pd.read_csv(year_path, low_memory=False)
    keep = [c for c in (COL_RSE, COL_GROUP, COL_TRANSITION, COL_BUS, COL_COUNTRY) if c in raw]
    df = raw.loc[:, keep].copy()
    df["survey_year"] = year

    # 2016 does not carry rse1_0 in this dataset, so all rows are retained.
    if year != 2016 and COL_RSE in df.columns:
        is_rse = to_binary(df[COL_RSE]) == 1.0
        df = df.loc[is_rse].copy()

    return df


def build_dataset(repo_root: Path) -> pd.DataFrame:
    yearly = [load_year_dataframe(repo_root, year) for year in YEARS]
    df = pd.concat(yearly, ignore_index=True, sort=False)
    df = ensure_columns(df, [COL_GROUP, COL_TRANSITION, COL_BUS, COL_COUNTRY])

    df["group_yes"] = to_binary(df[COL_GROUP])
    df["transition_yes"] = to_binary(df[COL_TRANSITION])

    # Keep plausible bus factors and drop obvious data-entry artifacts.
    bus_factor = pd.to_numeric(df[COL_BUS], errors="coerce")
    df["bus_factor"] = bus_factor.where((bus_factor >= 0) & (bus_factor <= 50))
    df["bus_single_point_risk"] = np.where(
        df["bus_factor"].notna(), (df["bus_factor"] <= 1).astype(float), np.nan
    )

    df["group_label"] = df["group_yes"].map({0.0: GROUP_NO, 1.0: GROUP_YES})
    return df


def build_yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for year, group in df.groupby("survey_year", sort=True):
        rows.append(
            {
                "survey_year": year,
                "n_respondents": int(len(group)),
                "n_countries": int(group[COL_COUNTRY].nunique(dropna=True)),
                "dedicated_group_yes_pct": pct_true(group["group_yes"]),
                "transition_plan_yes_pct": pct_true(group["transition_yes"]),
                "bus_factor_median": float(group["bus_factor"].median()),
                "bus_single_point_risk_pct": pct_true(group["bus_single_point_risk"]),
                "n_group_non_null": int(group["group_yes"].notna().sum()),
                "n_transition_non_null": int(group["transition_yes"].notna().sum()),
                "n_bus_non_null": int(group["bus_factor"].notna().sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("survey_year").reset_index(drop=True)


def build_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    clean = df[df["group_label"].notna()].copy()
    for (year, label), group in clean.groupby(["survey_year", "group_label"], sort=True):
        rows.append(
            {
                "survey_year": year,
                "group_label": label,
                "n_respondents": int(len(group)),
                "transition_plan_yes_pct": pct_true(group["transition_yes"]),
                "bus_single_point_risk_pct": pct_true(group["bus_single_point_risk"]),
                "bus_factor_median": float(group["bus_factor"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values(["survey_year", "group_label"]).reset_index(drop=True)


def build_effect_summary(group_summary: pd.DataFrame) -> pd.DataFrame:
    years = sorted(group_summary["survey_year"].unique().tolist())
    rows: list[dict[str, float]] = []

    for year in years:
        yr = group_summary[group_summary["survey_year"] == year]
        no = yr[yr["group_label"] == GROUP_NO]
        yes = yr[yr["group_label"] == GROUP_YES]

        if no.empty or yes.empty:
            rows.append(
                {
                    "survey_year": year,
                    "transition_advantage_pp": np.nan,
                    "bus_risk_reduction_pp": np.nan,
                }
            )
            continue

        transition_advantage = (
            float(yes["transition_plan_yes_pct"].iloc[0])
            - float(no["transition_plan_yes_pct"].iloc[0])
        )
        bus_risk_reduction = (
            float(no["bus_single_point_risk_pct"].iloc[0])
            - float(yes["bus_single_point_risk_pct"].iloc[0])
        )
        rows.append(
            {
                "survey_year": year,
                "transition_advantage_pp": transition_advantage,
                "bus_risk_reduction_pp": bus_risk_reduction,
            }
        )

    return pd.DataFrame(rows).sort_values("survey_year").reset_index(drop=True)


def save_plot_sample_context(yearly: pd.DataFrame, output_dir: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 5))

    year_labels = yearly["survey_year"].astype(str)
    ax1.bar(year_labels, yearly["n_respondents"], color="#4C78A8", alpha=0.9)
    ax1.set_ylabel("Respondents included")
    ax1.set_xlabel("Survey year")
    ax1.set_title("Sample Context: Respondents and Country Coverage")

    ax2 = ax1.twinx()
    ax2.plot(year_labels, yearly["n_countries"], color="#F58518", marker="o", linewidth=2)
    ax2.set_ylabel("Countries represented")

    fig.tight_layout()
    fig.savefig(output_dir / "01_sample_context.png", dpi=200)
    plt.close(fig)


def save_plot_trends(yearly: pd.DataFrame, output_dir: Path) -> None:
    plot_data = yearly.melt(
        id_vars=["survey_year"],
        value_vars=[
            "dedicated_group_yes_pct",
            "transition_plan_yes_pct",
            "bus_single_point_risk_pct",
        ],
        var_name="metric",
        value_name="pct",
    )
    labels = {
        "dedicated_group_yes_pct": "Dedicated group membership (%)",
        "transition_plan_yes_pct": "Transition plan present (%)",
        "bus_single_point_risk_pct": "Single-point-failure risk (%)",
    }
    plot_data["metric"] = plot_data["metric"].map(labels)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=plot_data,
        x="survey_year",
        y="pct",
        hue="metric",
        marker="o",
        linewidth=2.5,
        ax=ax,
    )
    ax.set_title("Longitudinal Trends in Team Structure and Resilience")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 100)
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(output_dir / "02_structure_resilience_trends.png", dpi=200)
    plt.close(fig)


def save_plot_transition_by_group(group_summary: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=group_summary,
        x="survey_year",
        y="transition_plan_yes_pct",
        hue="group_label",
        hue_order=[GROUP_NO, GROUP_YES],
        ax=ax,
    )
    ax.set_title("Transition Planning by Dedicated Group Membership")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Transition plan present (%)")
    ax.set_ylim(0, 40)
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(output_dir / "03_transition_by_group.png", dpi=200)
    plt.close(fig)


def save_plot_bus_risk_by_group(group_summary: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=group_summary,
        x="survey_year",
        y="bus_single_point_risk_pct",
        hue="group_label",
        hue_order=[GROUP_NO, GROUP_YES],
        ax=ax,
    )
    ax.set_title("Single-Point-Failure Risk by Dedicated Group Membership")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Bus factor <= 1 (%)")
    ax.set_ylim(0, 75)
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(output_dir / "04_bus_risk_by_group.png", dpi=200)
    plt.close(fig)


def save_plot_effect_sizes(effect_summary: pd.DataFrame, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=effect_summary.melt(
            id_vars="survey_year",
            value_vars=["transition_advantage_pp", "bus_risk_reduction_pp"],
            var_name="metric",
            value_name="pp",
        ),
        x="survey_year",
        y="pp",
        hue="metric",
        marker="o",
        linewidth=2.5,
        ax=ax,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Dedicated Group Effect Size Over Time")
    ax.set_xlabel("Survey year")
    ax.set_ylabel("Percentage-point advantage")
    ax.legend(
        title="",
        labels=[
            "Transition-plan advantage (Yes minus No)",
            "Bus-risk reduction (No minus Yes)",
        ],
    )
    fig.tight_layout()
    fig.savefig(output_dir / "05_effect_sizes.png", dpi=200)
    plt.close(fig)


def print_console_summary(
    yearly: pd.DataFrame, group_summary: pd.DataFrame, effect_summary: pd.DataFrame
) -> None:
    print("\n=== Longitudinal Summary (All Years) ===")
    print(yearly.to_string(index=False, float_format=lambda x: f"{x:0.2f}"))

    print("\n=== Dedicated Group Comparison by Year ===")
    print(group_summary.to_string(index=False, float_format=lambda x: f"{x:0.2f}"))

    print("\n=== Dedicated Group Effect Sizes ===")
    print(effect_summary.to_string(index=False, float_format=lambda x: f"{x:0.2f}"))

    yes = group_summary[group_summary["group_label"] == GROUP_YES]
    no = group_summary[group_summary["group_label"] == GROUP_NO]
    merged = yes.merge(no, on="survey_year", suffixes=("_yes", "_no"))

    mean_transition_advantage = (
        merged["transition_plan_yes_pct_yes"] - merged["transition_plan_yes_pct_no"]
    ).mean()
    mean_bus_risk_reduction = (
        merged["bus_single_point_risk_pct_no"] - merged["bus_single_point_risk_pct_yes"]
    ).mean()

    print("\n=== Headline Metrics ===")
    print(f"Average transition-plan advantage of dedicated groups: {mean_transition_advantage:0.2f} pp")
    print(f"Average bus-risk reduction of dedicated groups: {mean_bus_risk_reduction:0.2f} pp")


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", context="talk", palette="colorblind")

    df = build_dataset(repo_root)
    yearly = build_yearly_summary(df)
    group_summary = build_group_summary(df)
    effect_summary = build_effect_summary(group_summary)

    yearly.to_csv(output_dir / "yearly_summary.csv", index=False)
    group_summary.to_csv(output_dir / "group_summary.csv", index=False)
    effect_summary.to_csv(output_dir / "effect_summary.csv", index=False)

    save_plot_sample_context(yearly, output_dir)
    save_plot_trends(yearly, output_dir)
    save_plot_transition_by_group(group_summary, output_dir)
    save_plot_bus_risk_by_group(group_summary, output_dir)
    save_plot_effect_sizes(effect_summary, output_dir)

    print_console_summary(yearly, group_summary, effect_summary)
    print(f"\nOutputs written to: {output_dir}")


if __name__ == "__main__":
    main()
