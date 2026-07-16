"""Decision DSL bounded context (RFC-0017 v2).

The official business language of Athena: all investment decision logic
is expressed in `.rule` files — never hardcoded in Python. Compilation
is deterministic and pure: the DSL never touches the network, database,
filesystem, OS, or any LLM (RFC-0017 Non Goals).
"""
