# RFC-0020 --- Decision Compiler

**Status:** Draft **Version:** 1.0

# 1. Purpose

The Decision Compiler transforms Decision DSL into executable Decision
Objects.

The compiler is deterministic and independent of any LLM.

------------------------------------------------------------------------

# 2. Scope

The compiler SHALL:

-   Parse Decision DSL
-   Validate syntax
-   Validate semantics
-   Build an Abstract Syntax Tree (AST)
-   Produce a Decision Graph
-   Emit a Decision Object

The compiler SHALL NOT:

-   Call external APIs
-   Execute trades
-   Query databases directly
-   Generate natural-language investment advice

------------------------------------------------------------------------

# 3. Compilation Pipeline

``` text
Decision DSL
    ↓
Lexer
    ↓
Parser
    ↓
AST
    ↓
Semantic Analyzer
    ↓
Rule Validator
    ↓
Decision Graph
    ↓
Probability Engine
    ↓
Risk Engine
    ↓
Portfolio Engine
    ↓
Decision Object
```

------------------------------------------------------------------------

# 4. Components

## Lexer

Responsibilities:

-   Tokenize input
-   Detect lexical errors
-   Preserve source locations

## Parser

Responsibilities:

-   Build AST
-   Validate grammar
-   Report syntax errors

## Semantic Analyzer

Responsibilities:

-   Resolve identifiers
-   Validate references
-   Validate types
-   Detect circular dependencies

## Rule Validator

Responsibilities:

-   Enforce business invariants
-   Validate probability ranges
-   Validate required outputs

## Decision Graph Builder

Responsibilities:

-   Convert AST into executable graph
-   Preserve dependency ordering
-   Support explainable execution

------------------------------------------------------------------------

# 5. Intermediate Representation (IR)

The compiler produces an immutable IR containing:

-   Rule ID
-   Conditions
-   Actions
-   Dependencies
-   Metadata
-   Source location

------------------------------------------------------------------------

# 6. Decision Object

Required fields:

-   decision_id
-   hypothesis
-   evidence
-   counter_evidence
-   probability
-   confidence
-   expected_utility
-   portfolio_impact
-   risk_assessment
-   explanation
-   compiler_version

------------------------------------------------------------------------

# 7. Error Codes

DC001 Invalid Token

DC002 Syntax Error

DC003 Unknown Identifier

DC004 Type Mismatch

DC005 Circular Dependency

DC006 Invalid Decision Output

DC007 Semantic Validation Failed

------------------------------------------------------------------------

# 8. Acceptance Criteria

-   Deterministic compilation
-   Stable AST generation
-   Versioned IR
-   Explainable Decision Graph
-   100% unit test coverage for compiler stages
-   Compiler output reproducible for identical input
