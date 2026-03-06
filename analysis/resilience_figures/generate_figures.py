#!/usr/bin/env python3
"""
Generate two resilience-focused figures from the RSE longitudinal survey data.

This script is standalone inside the `resilience_figures/` directory.
It reads raw CSVs directly from the survey repo structure:
  <repo_root>/<year>/<year>_tf.csv
for years: 2016, 2017, 2018, 2022.
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

GROUP_NO = "Dedicated group: No"
GROUP_YES = "Dedicated group: Yes"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create two standalone resilience figures from raw longitudinal survey data."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Path containing 2016/2016_tf.csv, 2017/2017_tf.csv, etc.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "figures",
        help="Directory where output PNG files will be written.",
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
    keep = [c for c in (COL_RSE, COL_GROUP, COL_TRANSITION, COL_BUS) if c in raw]
    df = raw.loc[:, keep].copy()
    df["survey_year"] = year

    # 2016 does not consistently carry rse1_0, so keep all rows for that wave.
    if year != 2016 and COL_RSE in df.columns:
        is_rse = to_binary(df[COL_RSE]) == 1.0
        df = df.loc[is_rse].copy()

    return df


def build_dataset(repo_root: Path) -> pd.DataFrame:
    yearly = [load_year_dataframe(repo_root, year) for year in YEARS]
    df = pd.concat(yearly, ignore_index=True, sort=False)
    df = ensure_columns(df, [COL_GROUP, COL_TRANSITION, COL_BUS])

    df["group_yes"] = to_binary(df[COL_GROUP])
    df["transition_yes"] = to_binary(df[COL_TRANSITION])

    bus_factor = pd.to_numeric(df[COL_BUS], errors="coerce")
    df["bus_factor"] = bus_factor.where((bus_factor >= 0) & (bus_factor <= 50))
    df["bus_single_point_risk"] = np.where(
        df["bus_factor"].notna(), (df["bus_factor"] <= 1).astype(float), np.nan
    )
    df["group_label"] = df["group_yes"].map({0.0: GROUP_NO, 1.0: GROUP_YES})
    return df


def build_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    clean = df[df["group_label"].notna()].copy()
    for (year, label), group in clean.groupby(["survey_year", "group_label"], sort=True):
        rows.append(
            {
                "survey_year": year,
                "group_label": label,
                "transition_plan_yes_pct": pct_true(group["transition_yes"]),
                "bus_single_point_risk_pct": pct_true(group["bus_single_point_risk"]),
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
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", context="talk", palette="colorblind")

    df = build_dataset(repo_root)
    group_summary = build_group_summary(df)
    effect_summary = build_effect_summary(group_summary)

    save_composite_resilience_plot(group_summary, output_dir)
    save_advantage_components_plot(effect_summary, output_dir)

    print(f"Wrote: {output_dir / '01_composite_resilience_by_group.png'}")
    print(f"Wrote: {output_dir / '02_resilience_advantage_components.png'}")


if __name__ == "__main__":
    main()
