"""
test_app.py — Tests unitaires et d'intégration pour l'application DevSecOps
Lancement : pytest tests/ -v --cov=src --cov-report=xml
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ajouter src/ au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import app
from utils import (
    validate_input,
    sanitize_string,
    generate_request_id,
    mask_secret,
)

# ─── Configuration des tests ──────────────────────────────────────────────────
os.environ["API_SECRET_TOKEN"] = "test-secret-token-valid"
VALID_TOKEN = "test-secret-token-valid"
INVALID_TOKEN = "wrong-token"

client = TestClient(app)


# ═════════════════════════════════════════════════════════════════════════════
# Tests des routes publiques
# ═════════════════════════════════════════════════════════════════════════════

class TestPublicRoutes:

    def test_root_returns_200(self):
        """L'endpoint racine doit retourner un statut 200."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data

    def test_health_check_returns_healthy(self):
        """L'endpoint /health doit retourner status=healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_version_endpoint(self):
        """L'endpoint /version doit retourner les informations de version."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "build" in data


# ═════════════════════════════════════════════════════════════════════════════
# Tests des routes protégées — Authentification
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthentication:

    def test_protected_route_without_token_returns_403(self):
        """Un accès sans token doit être refusé (403)."""
        response = client.post(
            "/api/message",
            json={"content": "test message", "author": "user"},
        )
        assert response.status_code in (401, 403)

    def test_protected_route_with_invalid_token_returns_401(self):
        """Un token invalide doit retourner 401."""
        response = client.post(
            "/api/message",
            json={"content": "test message"},
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
        )
        assert response.status_code == 401

    def test_protected_route_with_valid_token_returns_200(self):
        """Un token valide doit permettre l'accès."""
        response = client.post(
            "/api/message",
            json={"content": "Bonjour depuis les tests !", "author": "pytest"},
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "request_id" in data

    def test_secure_data_requires_auth(self):
        """L'endpoint /api/secure-data nécessite une authentification."""
        response = client.get("/api/secure-data")
        assert response.status_code in (401, 403)

    def test_secure_data_with_valid_token(self):
        """L'endpoint /api/secure-data est accessible avec un bon token."""
        response = client.get(
            "/api/secure-data",
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# Tests de validation des entrées
# ═════════════════════════════════════════════════════════════════════════════

class TestInputValidation:

    def test_valid_message_accepted(self):
        """Un message normal doit être accepté."""
        response = client.post(
            "/api/message",
            json={"content": "Message de test valide", "author": "user1"},
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )
        assert response.status_code == 200

    def test_empty_content_rejected(self):
        """Un contenu vide doit être rejeté (422)."""
        response = client.post(
            "/api/message",
            json={"content": "   ", "author": "user"},
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )
        assert response.status_code == 422

    def test_content_too_long_rejected(self):
        """Un contenu dépassant 1000 chars doit être rejeté."""
        response = client.post(
            "/api/message",
            json={"content": "x" * 1001, "author": "user"},
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# Tests des utilitaires (utils.py)
# ═════════════════════════════════════════════════════════════════════════════

class TestUtils:

    # --- validate_input ---
    def test_validate_input_safe_text(self):
        assert validate_input("Bonjour, ceci est un texte sûr.") is True

    def test_validate_input_xss_script(self):
        assert validate_input("<script>alert('xss')</script>") is False

    def test_validate_input_sql_injection(self):
        assert validate_input("SELECT * FROM users WHERE id=1") is False

    def test_validate_input_path_traversal(self):
        assert validate_input("../../etc/passwd") is False

    def test_validate_input_command_injection(self):
        assert validate_input("$(rm -rf /)") is False

    def test_validate_input_empty_string(self):
        assert validate_input("") is False

    def test_validate_input_none(self):
        assert validate_input(None) is False  # type: ignore

    # --- sanitize_string ---
    def test_sanitize_encodes_html_entities(self):
        result = sanitize_string("<b>texte</b>")
        assert "<b>" not in result
        assert "&lt;b&gt;" in result

    def test_sanitize_removes_control_chars(self):
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result

    def test_sanitize_strips_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_sanitize_empty_string(self):
        assert sanitize_string("") == ""

    # --- generate_request_id ---
    def test_request_id_is_unique(self):
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2

    def test_request_id_is_valid_uuid(self):
        import uuid
        request_id = generate_request_id()
        # Vérifie que c'est un UUID valide (ne lève pas d'exception)
        uuid.UUID(request_id)

    # --- mask_secret ---
    def test_mask_secret_hides_value(self):
        result = mask_secret("mysecrettoken123")
        assert "mysecrettoken123" not in result
        assert "***" in result

    def test_mask_secret_empty(self):
        assert mask_secret("") == "***"

    def test_mask_secret_short_value(self):
        assert mask_secret("ab") == "***"
