"""
app.py — Application FastAPI déployée dans le pipeline DevSecOps
Auteur  : Projet CI/CD Sécurisé
Stack   : Python 3.11 + FastAPI
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
import logging
import os
import time
from utils import (
    get_version,
    validate_input,
    generate_request_id,
    sanitize_string,
)

# ─── Configuration du logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Application FastAPI ──────────────────────────────────────────────────────
app = FastAPI(
    title="DevSecOps FastAPI App",
    description="Application déployée via pipeline CI/CD sécurisé (Jenkins + Harbor)",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware CORS (restreint) ──────────────────────────────────────────────
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─── Sécurité : Bearer Token ──────────────────────────────────────────────────
security = HTTPBearer()
API_TOKEN = os.getenv("API_SECRET_TOKEN", "changeme-secret-token")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifie le token Bearer de l'API."""
    if credentials.credentials != API_TOKEN:
        logger.warning("Tentative d'accès avec un token invalide.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
        )
    return credentials


# ─── Modèles Pydantic ─────────────────────────────────────────────────────────
class MessageRequest(BaseModel):
    content: str
    author: str = "anonymous"

    @validator("content")
    def content_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Le contenu ne peut pas être vide.")
        if len(v) > 1000:
            raise ValueError("Le contenu dépasse 1000 caractères.")
        return sanitize_string(v)

    @validator("author")
    def author_safe(cls, v):
        return sanitize_string(v)


class MessageResponse(BaseModel):
    request_id: str
    status: str
    message: str
    timestamp: float


# ─── Routes publiques ─────────────────────────────────────────────────────────
@app.get("/", tags=["Santé"])
def root():
    """Point d'entrée public — vérification que l'app tourne."""
    return {
        "app": "DevSecOps FastAPI App",
        "version": get_version(),
        "status": "running",
    }


@app.get("/health", tags=["Santé"])
def health_check():
    """Endpoint de santé utilisé par Docker et le monitoring."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/version", tags=["Informations"])
def version():
    """Retourne la version de l'application."""
    return {
        "version": get_version(),
        "build": os.getenv("BUILD_NUMBER", "local"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
    }


# ─── Routes protégées ─────────────────────────────────────────────────────────
@app.post(
    "/api/message",
    response_model=MessageResponse,
    tags=["API"],
    dependencies=[Depends(verify_token)],
)
def post_message(request: MessageRequest):
    """
    Reçoit un message de façon sécurisée.
    Nécessite un token Bearer valide.
    """
    request_id = generate_request_id()
    logger.info(f"[{request_id}] Message reçu de '{request.author}' "
                f"({len(request.content)} chars)")

    if not validate_input(request.content):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Contenu invalide détecté.",
        )

    return MessageResponse(
        request_id=request_id,
        status="accepted",
        message=f"Message de '{request.author}' traité avec succès.",
        timestamp=time.time(),
    )


@app.get(
    "/api/secure-data",
    tags=["API"],
    dependencies=[Depends(verify_token)],
)
def get_secure_data():
    """Exemple de données sécurisées accessibles uniquement avec authentification."""
    return {
        "data": "Données confidentielles de l'application.",
        "classification": "INTERNAL",
        "timestamp": time.time(),
    }


# ─── Gestionnaire d'erreurs global ───────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Erreur non gérée : {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur."},
    )
