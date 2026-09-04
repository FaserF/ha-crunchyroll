from __future__ import annotations


class CrunchyrollError(Exception):
    """Base exception for Crunchyroll API."""


class AuthenticationError(CrunchyrollError):
    """Invalid credentials token expired, etc."""


class ConnectionError(CrunchyrollError):
    """Network or http connectivity issues."""


class RateLimitError(CrunchyrollError):
    """Rate limit exceeded."""
