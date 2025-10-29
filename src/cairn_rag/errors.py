"""Cairn's public exception hierarchy and CLI exit codes."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Stable process exit codes used by the ``cairn-rag`` command."""

    SUCCESS = 0
    PLAN_OR_APPLY_FAILURE = 1
    VERIFICATION_MISMATCH = 2
    BACKEND_OR_PROVIDER_ERROR = 3
    CONFIG_ERROR = 4


class CairnError(Exception):
    """Base class for expected, user-facing Cairn failures."""

    exit_code = ExitCode.PLAN_OR_APPLY_FAILURE


class ConfigError(CairnError):
    """Raised when configuration is absent, malformed, or inconsistent."""

    exit_code = ExitCode.CONFIG_ERROR


class BackendError(CairnError):
    """Raised when an index or cache backend cannot complete an operation."""

    exit_code = ExitCode.BACKEND_OR_PROVIDER_ERROR


class ProviderError(CairnError):
    """Raised when an embedding provider cannot complete an operation."""

    exit_code = ExitCode.BACKEND_OR_PROVIDER_ERROR


class TransientProviderError(ProviderError):
    """A provider failure that is explicitly safe to retry with backoff."""


class VerificationError(CairnError):
    """Raised when durable manifest and active index state disagree."""

    exit_code = ExitCode.VERIFICATION_MISMATCH
