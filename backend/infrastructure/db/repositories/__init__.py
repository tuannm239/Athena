"""Repository implementations over SQLAlchemy (SPEC-03 interfaces, SPEC-07 storage).

Every mutation of Decision, Portfolio, or Position writes an immutable
audit record (SPEC-07, Audit). No SQL exists outside this package and
its sibling infrastructure modules.
"""
