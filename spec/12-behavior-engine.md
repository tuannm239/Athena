# SPEC-12 — Behavior Engine

> Status: Accepted Version: 2.0 (Enterprise Draft)

# Behavior Engine Specification

## Purpose

The Behavior Engine helps investors improve decision quality by
detecting behavioral biases, reviewing historical decisions and
providing structured feedback.

It never overrides the Decision Kernel. It augments decision quality.

------------------------------------------------------------------------

# Objectives

-   Detect recurring behavioral biases
-   Build an investor behavior profile
-   Improve confidence calibration
-   Support post-investment reviews
-   Encourage disciplined decision making

------------------------------------------------------------------------

# Responsibilities

-   Behavior profiling
-   Bias detection
-   Decision journaling
-   Decision replay
-   Performance attribution
-   Learning recommendations

------------------------------------------------------------------------

# Biases

Supported categories:

-   Loss Aversion
-   Confirmation Bias
-   Anchoring
-   Overconfidence
-   Recency Bias
-   Disposition Effect
-   FOMO
-   Herding

------------------------------------------------------------------------

# Inputs

-   Decision history
-   Portfolio history
-   Market context
-   User notes
-   Execution outcomes

------------------------------------------------------------------------

# Outputs

Behavior Report

-   behavior_score
-   detected_biases
-   confidence_calibration
-   recurring_patterns
-   recommendations
-   learning_actions

------------------------------------------------------------------------

# Decision Journal

Every decision stores:

-   Original hypothesis
-   Supporting evidence
-   Counter evidence
-   Expected outcome
-   Actual outcome
-   Lessons learned

Journal entries are immutable.

------------------------------------------------------------------------

# Confidence Calibration

Compare:

Expected probability

vs.

Observed outcome

Track calibration error over time.

------------------------------------------------------------------------

# Behavioral KPIs

-   Average holding period
-   Premature exits
-   Excessive concentration
-   Rule violations
-   Emotional trades
-   Review completion rate

------------------------------------------------------------------------

# Sequence

``` mermaid
sequenceDiagram
Decision Kernel->>Behavior Engine: Decision Completed
Behavior Engine->>Journal: Record Decision
Behavior Engine->>Analytics: Detect Bias
Analytics-->>Behavior Engine: Behavior Report
Behavior Engine-->>User: Recommendations
```

------------------------------------------------------------------------

# Business Rules

1.  Behavioral feedback is advisory only.
2.  Historical records cannot be modified.
3.  Every review references the original decision.
4.  Recommendations must be explainable.

------------------------------------------------------------------------

# Acceptance Criteria

-   Deterministic scoring
-   Immutable journal
-   Explainable recommendations
-   Full audit trail
-   Independent from UI and LLM
