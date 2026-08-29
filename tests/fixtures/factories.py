"""
Hermetic Test Data Factories & Mock Generators.
"""

from typing import Dict, Any

def make_sample_payload(**overrides: Any) -> Dict[str, Any]:
    """Generates a standard test dictionary payload with optional overrides."""
    payload = {
        "id": "test-id-12345",
        "name": "Sample Entity",
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z"
    }
    payload.update(overrides)
    return payload
