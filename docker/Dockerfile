# ═══════════════════════════════════════════════════════════════════════════
#  Dockerfile — Image Docker sécurisée (multi-stage build)
#  Application : FastAPI DevSecOps
#  Base        : python:3.11-slim (image minimale = surface d'attaque réduite)
# ═══════════════════════════════════════════════════════════════════════════

# ─── Stage 1 : Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Métadonnées OCI
LABEL org.opencontainers.image.title="DevSecOps FastAPI App"
LABEL org.opencontainers.image.description="Application FastAPI déployée via pipeline CI/CD sécurisé"
LABEL org.opencontainers.image.source="https://github.com/mon-org/devsecops-project"

# Répertoire de travail
WORKDIR /build

# Copier uniquement les dépendances en premier (cache Docker efficace)
COPY requirements.txt .

# Installer les dépendances dans un répertoire isolé (pas de pollution système)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        --prefix=/install \
        -r requirements.txt

# ─── Stage 2 : Image finale (minimale et sécurisée) ──────────────────────────
FROM python:3.11-slim AS final

# ── Bonnes pratiques de sécurité ──────────────────────────────────────────────
# 1. Mettre à jour les paquets système (corriger les CVE connues)
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends \
        curl \
 && apt-get autoremove -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 2. Créer un utilisateur non-root dédié (principe du moindre privilège)
RUN groupadd --gid 1001 appgroup \
 && useradd --uid 1001 --gid appgroup \
            --no-create-home --shell /bin/false appuser

# 3. Copier les dépendances installées depuis le builder
COPY --from=builder /install /usr/local

# 4. Répertoire de l'application
WORKDIR /app

# 5. Copier le code source
COPY src/ ./src/

# 6. Changer le propriétaire des fichiers vers l'utilisateur non-root
RUN chown -R appuser:appgroup /app

# 7. Passer à l'utilisateur non-root
USER appuser

# 8. Exposer le port (documentation — pas de sécurité à lui seul)
EXPOSE 8000

# 9. Variables d'environnement par défaut (à surcharger en production)
ENV APP_VERSION="1.0.0" \
    BUILD_NUMBER="local" \
    GIT_COMMIT="unknown" \
    ALLOWED_ORIGINS="http://localhost" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 10. Health check intégré
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 11. Point d'entrée (pas de shell pour éviter les injections)
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
