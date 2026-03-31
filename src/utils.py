"""
utils.py — Fonctions utilitaires pour l'application DevSecOps
"""

import uuid
import re
import os
import html
import logging

logger = logging.getLogger(__name__)

# ─── Version ──────────────────────────────────────────────────────────────────
VERSION = os.getenv("APP_VERSION", "1.0.0")


def get_version() -> str:
    """Retourne la version de l'application."""
    return VERSION


# ─── Génération d'ID de requête ───────────────────────────────────────────────
def generate_request_id() -> str:
    """Génère un identifiant unique pour chaque requête."""
    return str(uuid.uuid4())


# ─── Validation des entrées ───────────────────────────────────────────────────
# Patterns interdits (injection, XSS, SQLi, etc.)
FORBIDDEN_PATTERNS = [
    r"<script.*?>.*?</script>",          # XSS script tag
    r"javascript:",                       # XSS javascript:
    r"on\w+\s*=",                         # XSS event handlers
    r"(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\s+",  # SQLi
    r"(\.\./|\.\.\\)",                    # Path traversal
    r"(\$\{|\$\()",                       # Template / command injection
    r"(&&|\|\|)\s*\w+",                  # Command chaining
    r"[;<>`]",                            # Shell metacharacters
]

COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in FORBIDDEN_PATTERNS
]


def validate_input(text: str) -> bool:
    """
    Valide une chaîne de caractères contre les patterns d'injection connus.
    Retourne True si le texte est sûr, False sinon.
    """
    if not text or not isinstance(text, str):
        return False

    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Pattern dangereux détecté : {pattern.pattern!r}")
            return False

    return True


def sanitize_string(text: str) -> str:
    """
    Assainit une chaîne en encodant les caractères HTML et en supprimant
    les caractères de contrôle.
    """
    if not text:
        return ""

    # Encode les entités HTML (protège contre XSS)
    sanitized = html.escape(text)

    # Supprime les caractères de contrôle (sauf newline et tab)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

    return sanitized.strip()


# ─── Vérification des variables d'environnement ───────────────────────────────
REQUIRED_ENV_VARS = [
    "API_SECRET_TOKEN",
]


def check_env_vars() -> list[str]:
    """
    Vérifie que les variables d'environnement obligatoires sont définies.
    Retourne la liste des variables manquantes.
    """
    missing = []
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if not value or value.lower() in ("", "none", "null", "changeme"):
            missing.append(var)
            logger.warning(f"Variable d'environnement manquante ou non sécurisée : {var}")
    return missing


# ─── Masquage des secrets dans les logs ──────────────────────────────────────
def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Masque un secret dans les logs en ne laissant apparaître que
    les premiers caractères.
    Ex: "mysecrettoken123" → "myse***"
    """
    if not value:
        return "***"
    if len(value) <= visible_chars:
        return "***"
    return value[:visible_chars] + "***"
