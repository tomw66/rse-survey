# Submissions Package

This folder contains everything needed for the resilience submission section.

## Contents

- `submission_text.md`: submission draft text.
- `script.py`: figure-generation script.
- `data/group_summary.csv`: grouped resilience metrics by year/team structure.
- `data/effect_summary.csv`: year-by-year percentage-point effects.
- `figures/`: output directory for generated PNG files.

## Generate figures

From the `analysis/` directory:

```bash
python3 submissions/script.py
```

Or from inside `submissions/`:

```bash
python3 script.py
```

The script writes:

- `figures/01_composite_resilience_by_group.png`
- `figures/02_resilience_advantage_components.png`

## Requirements

Python packages:

- `pandas`
- `matplotlib`
- `seaborn`
