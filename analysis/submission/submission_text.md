# Submission Draft: Centralised RSE Team and Resilience

## Core Claim

A centralised Research Software Engineering (RSE) team is likely to provide stronger organisational resilience than models where RSEs are embedded as isolated individuals in separate projects or departments.

## Narrative

The primary resilience advantage of a central team is that knowledge, responsibilities, and specialist skills are distributed rather than concentrated in one person per project. In embedded models, an individual often becomes the sole holder of technical context for software architecture, deployment, testing workflows, and operational handover. This creates a single-point-of-failure risk at the organisational level: if that individual leaves, is unavailable, or is moved to another priority, software continuity can degrade quickly.

Centralised teams reduce this fragility by creating redundancy in capability. Work can be reallocated when needed, peer review is more available, and key practices are more likely to be standardised across projects. This does not eliminate project risk, but it changes the risk profile from person-dependent to team-dependent, which is generally more manageable.

The figure-based evidence supports this direction of travel. In Figure 1, the composite resilience score (transition-plan percentage minus bus-risk percentage) is consistently higher for dedicated-group respondents in every survey year: -13.9 vs -39.4 (2016), -21.0 vs -45.6 (2017), -29.1 vs -48.2 (2018), and -31.9 vs -48.1 (2022), all in percentage points. This corresponds to a dedicated-group advantage of 25.5, 24.6, 19.1, and 16.2 percentage points respectively. Figure 2 shows the same pattern by component: transition-plan advantage is +17.6, +4.2, +6.7, and +6.1 percentage points, while bus-risk reduction is +7.9, +20.4, +12.4, and +10.1 percentage points (2016 to 2022). Taken together, the figures show a stable directional benefit for dedicated-group structures on resilience outcomes.

In practical terms, this means centralisation can improve the ability of an institution to absorb staffing shocks, sustain delivery under changing project demands, and preserve software maintainability over time. It also enables faster circulation of proven resilience practices (for example: documented handover procedures, shared tooling standards, and repeatable support workflows), which can improve baseline reliability across multiple projects rather than only in isolated pockets.

For decision-makers, this supports a strategy of consolidating dispersed embedded roles into a central RSE function where feasible, while preserving strong domain links to research teams through clear engagement models.

## Figure Captions

**Figure 1 (`01_composite_resilience_by_group.png`)**  
Composite resilience score by survey year, shown separately for respondents with and without a dedicated RSE group. The score is calculated as: percentage reporting a transition plan minus percentage with bus-factor risk (`bus factor <= 1`). Higher values indicate stronger resilience. Across all years, the dedicated-group line is consistently higher, indicating a more favourable resilience profile.

**Figure 2 (`02_resilience_advantage_components.png`)**  
Year-by-year resilience advantage of dedicated groups, decomposed into two percentage-point effects: (1) transition-plan advantage (`Yes minus No`) and (2) bus-risk reduction (`No minus Yes`). Positive bars indicate outcomes that favour dedicated groups. The chart shows that dedicated-group settings are associated with both better transition planning and lower single-point-failure risk.
