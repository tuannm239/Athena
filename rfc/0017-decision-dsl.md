# RFC-0017 — Decision DSL

**Status:** Approved **Version:** 2.0

## Purpose

Decision DSL is the official business language of Athena. All investment
decision logic SHALL be expressed in Decision DSL; business logic SHALL NOT
be hardcoded in Python. The DSL SHALL be deterministic, explainable,
versioned and testable.

## Non Goals

The DSL SHALL NOT execute trades, read databases, call HTTP APIs, call LLMs,
modify portfolios, read files, execute Python, or access the OS.

## File extension

`.rule` (e.g. `quality_growth.rule`).

## Compiler architecture

Decision DSL → Lexer → Parser → AST → Semantic Analyzer → Rule Validator →
Intermediate Representation → Decision Graph → Decision Object.

## Lexical rules

Case sensitive; UTF-8; Unix line endings; `//` single-line and `/* */`
multi-line comments.

## Reserved keywords

RULE WHEN THEN VERSION PRIORITY EXPLAIN TAG AND OR NOT TRUE FALSE NULL
PROBABILITY CONFIDENCE UTILITY RISK RETURN STOP IGNORE WATCH

## Root objects

Market Company Portfolio Risk Behavior Decision Evidence Feature Macro
Sector Industry Country

## Operators

`== != > >= < <= + - * / % && || !` and `IN`, `NOT IN`, `BETWEEN`, `LIKE`.

## Grammar (EBNF)

```ebnf
program        ::= rule*
rule           ::= RULE identifier metadata? when_clause then_clause explain_clause?
metadata       ::= VERSION string PRIORITY integer
when_clause    ::= WHEN expression
then_clause    ::= THEN action+
expression     ::= condition
                 | expression AND expression
                 | expression OR expression
                 | NOT expression
                 | "(" expression ")"
condition      ::= identifier operator literal
action         ::= probability_action | confidence_action | utility_action
                 | risk_action | tag_action
probability_action ::= PROBABILITY assign number
confidence_action  ::= CONFIDENCE assign number
utility_action     ::= UTILITY assign number
risk_action        ::= RISK assign number
assign             ::= "=" | "+=" | "-="
tag_action         ::= TAG string
explain_clause     ::= EXPLAIN string
```

Note: the v2 grammar's `condition` takes a single literal, so `IN`,
`NOT IN` and `BETWEEN` are not expressible; the compiler reports DSL002
for them until a future grammar revision adds list/range literals.

## Example

```text
RULE HighQualityCompounder
VERSION "1.0"
PRIORITY 100
WHEN
    Market.Regime == Expansion
    AND Company.ROIC > 20
    AND Company.RevenueGrowth > 15
    AND Company.DebtToEquity < 0.50
THEN
    PROBABILITY += 0.08
    CONFIDENCE += 0.05
    UTILITY += 0.12
    RISK -= 0.04
    TAG "Quality"
    TAG "Growth"
EXPLAIN "High quality compounder during expansion."
```

## Semantic rules

Exactly one WHEN and one THEN per rule; PROBABILITY/CONFIDENCE values in
0..1; PRIORITY positive integer; duplicate rule names forbidden; circular
dependencies forbidden; unknown identifier/function/property/enum are
compiler errors.

## Intermediate representation

Immutable IR: rule id, priority, conditions, actions, dependencies, tags,
metadata, source location.

## Decision graph

Directed acyclic graph; each rule a node; dependencies edges; cycles are
compiler errors.

## Compiler output (Decision Object)

decision_id, matched_rules, probability, confidence, expected_utility,
risk_adjustment, portfolio_impact, position_size, tags, hypothesis,
assumptions, invalidation_conditions, compiler_version, explanation.

## Error codes

DSL001 Invalid Token · DSL002 Invalid Syntax · DSL003 Unknown Identifier ·
DSL004 Unknown Function · DSL005 Type Mismatch · DSL006 Probability Out Of
Range · DSL007 Confidence Out Of Range · DSL008 Duplicate Rule · DSL009
Circular Dependency · DSL010 Missing WHEN · DSL011 Missing THEN · DSL012
Invalid Action · DSL013 Invalid Property · DSL014 Invalid Enum · DSL015
Semantic Validation Failed

## Acceptance criteria

Identical source ⇒ identical AST ⇒ identical Decision Graph ⇒ identical
Decision Object; deterministic compilation; reproducible execution; zero
business logic outside the DSL; golden/regression/semantic tests green;
≥ 95% test coverage on compiler stages.
