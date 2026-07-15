"""Decision application layer — use cases over the Decision aggregate.

No decision *logic* lives here (that is the kernel's, Sprint 9); these
use cases orchestrate persistence, lifecycle transitions requested by
users, and event publication (SPEC-03; controllers stay logic-free).
"""
