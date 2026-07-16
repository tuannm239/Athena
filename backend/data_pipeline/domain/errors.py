"""Data pipeline error codes (RFC-0024 §10)."""

from __future__ import annotations

from shared_kernel.exceptions import DomainError


class DataPipelineError(DomainError):
    """Base class; `code` carries the RFC-0024 §10 error code."""

    code = "DP000"


class InvalidSourceError(DataPipelineError):
    code = "DP001"


class SchemaValidationError(DataPipelineError):
    code = "DP002"


class DuplicateDatasetError(DataPipelineError):
    code = "DP003"


class TransformationError(DataPipelineError):
    code = "DP004"


class PublishError(DataPipelineError):
    code = "DP005"
