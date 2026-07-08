"""
Dynamic Verification layer.

Responsibility: Given a ClassifiedRoute with is_vulnerable=True, craft and
execute HTTP probes using attacker/victim credentials from test_users.json,
then produce VerificationResult objects with full evidence.

Public API
----------
verify_all_routes(classified_routes, base_url) -> list[VerifiedRoute]
execute_verification(route, test_users, base_url) -> VerificationResult
"""

from .executor import execute_verification
from .verifier import verify_all_routes

__all__ = ["execute_verification", "verify_all_routes"]
