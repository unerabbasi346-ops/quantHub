# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Authentication — Doc 07 §Core Services
# Security: authentication required for protected APIs; principle of least privilege
#   — Doc 07 §Security
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod


class AuthServiceInterface(ABC):
    """Authentication contract — Doc 07 §Security / D-9 Zero-Trust Data Security.

    D-9: every access request shall be explicitly authenticated and authorized;
    failure defaults to deny. Mechanism (OIDC, SAML, API key, local session)
    is Deferred Technology Decision #6 — not yet resolved.

    No credentials shall be stored in application tables per Doc 09 §Security
    and Doc 00 §14.9 regardless of the mechanism chosen.
    """

    @abstractmethod
    async def verify_token(self, token: str) -> dict: ...

    @abstractmethod
    async def get_current_user(self, token: str) -> object | None: ...
