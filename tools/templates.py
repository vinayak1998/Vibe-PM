"""Spec Markdown template for Spec Writer (phased implementation plan)."""

SPEC_TEMPLATE = """# Product Spec: {product_name}

## Problem Statement
{problem_statement}

## Target User Persona
{target_user_persona}

## Comparable Products
{comparable_products}

## Implementation Plan

### Phase 1: {phase_1_name} ({phase_1_weeks})
**Goal**: {phase_1_goal}

#### Features
{phase_1_features}

#### Core User Flow
{phase_1_flow}

#### Key Screens
{phase_1_screens}

### Phase 2: {phase_2_name} ({phase_2_weeks})
**Goal**: {phase_2_goal}

#### Features
{phase_2_features}

#### Additional Screens
{phase_2_screens}

### Phase 3: {phase_3_name} ({phase_3_weeks})
**Goal**: {phase_3_goal}

#### Features
{phase_3_features}

## Cut Features (with rationale)
{cut_features}

## RICE Scoring Summary
{rice_summary}

## Open Questions & Risks
{open_questions_risks}

## Technical Considerations
{technical_considerations}
"""
