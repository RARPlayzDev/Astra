"""Branded exception hierarchy for the ewsmart package.

Every error raised deliberately by ewsmart code derives from
:class:`EwsmartError`, so callers can catch one branded base class while
still distinguishing configuration mistakes, simulation bounds violations,
scheduler misuse and persistence failures.  Standard Python exceptions
(``ValueError``, ``TypeError``, ...) continue to surface for genuine
programming bugs; anything a *user* of the library can trigger by passing
bad input is converted into a branded subclass at the API boundary.
"""
from __future__ import annotations


class EwsmartError(Exception):
    """Base class for every exception raised deliberately by ewsmart."""


class ConfigurationError(EwsmartError):
    """Invalid configuration or constructor argument.

    Raised when a :class:`~ewsmart.config.ScenarioConfig`, scheduler
    parameter or function keyword falls outside its documented domain
    (e.g. ``n_bands <= 0``, a negative horizon, malformed ranges).
    """


class InvalidBandError(EwsmartError, IndexError):
    """A band index outside ``[0, n_bands)`` was supplied.

    Derives from :class:`IndexError` as well so existing ``except IndexError``
    call sites keep working.
    """


class SimulationBoundsError(EwsmartError, ValueError):
    """A simulation argument is outside the valid episode domain.

    Examples: a time slot ``t < 0`` or ``t >= T``, an emitter id without a
    matching spec, or a probability-like quantity outside ``[0.0, 1.0]``.
    """


class InvalidDwellResultError(EwsmartError, TypeError):
    """A scheduler ``update()`` received a result object missing the
    required ``band`` / ``t`` / ``hit`` / ``false_alarm`` / ``detections``
    attributes."""


class InvalidRewardError(EwsmartError, TypeError):
    """A scheduler ``update()`` received a reward that is not a finite
    real number (non-numeric or NaN/inf)."""


class SchedulerStateError(EwsmartError, ValueError):
    """A scheduler was asked to operate on incompatible persisted state
    (wrong dimensions, missing keys, wrong scheduler type)."""


class DatabaseError(EwsmartError):
    """A metrics-database operation failed (schema mismatch, locked file,
    unreadable path)."""
