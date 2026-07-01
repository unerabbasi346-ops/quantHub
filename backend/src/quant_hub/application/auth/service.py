# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Authentication — Doc 07 §Core Services
# Security: authentication required for all protected APIs — Doc 07 §Security
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.auth.interfaces import AuthServiceInterface


class AuthService:
    """Application service stub — business logic not implemented in Step 0.4.

    Doc 07 §Security: delegates to external IdP (OIDC/SAML).
    No credentials stored locally per Doc 09 §Security and Doc 00 §14.9.
    """

    def __init__(self, auth: AuthServiceInterface) -> None:
        self._auth = auth
