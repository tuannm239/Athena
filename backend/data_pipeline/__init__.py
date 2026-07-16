"""Data Pipeline bounded context (RFC-0024).

The only approved path for data entering Athena: ingestion, validation,
normalization, enrichment, quality checks, versioned publication with
full lineage. Failed datasets never reach the Feature Store.
"""
