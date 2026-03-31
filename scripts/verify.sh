#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  verify.sh — Vérification de la signature d'une image Docker (Cosign)
#  Usage : ./scripts/verify.sh <IMAGE:TAG> [chemin_cle_publique]
#
#  Ce script est exécuté sur le SERVEUR DE DÉPLOIEMENT avant tout
#  lancement de conteneur, pour garantir que l'image est bien signée
#  par le pipeline CI/CD Jenkins.
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

IMAGE="${1:-}"
COSIGN_PUB_KEY="${2:-/opt/devsecops/cosign.pub}"

# ─── Validation ───────────────────────────────────────────────────────────────
if [[ -z "$IMAGE" ]]; then
    echo "[ERREUR] Usage : $0 <image:tag> [cosign.pub]"
    exit 1
fi

if [[ ! -f "$COSIGN_PUB_KEY" ]]; then
    echo "[ERREUR] Clé publique Cosign introuvable : $COSIGN_PUB_KEY"
    echo "         Copiez cosign.pub sur ce serveur avant de déployer."
    exit 1
fi

# ─── Vérifier Cosign ──────────────────────────────────────────────────────────
if ! command -v cosign &>/dev/null; then
    echo "[*] Installation de Cosign..."
    COSIGN_VERSION="2.2.3"
    wget -q "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64"
    chmod +x cosign-linux-amd64
    mv cosign-linux-amd64 /usr/local/bin/cosign
fi

echo "════════════════════════════════════════"
echo " COSIGN — Vérification de la signature"
echo " Image  : $IMAGE"
echo " Clé    : $COSIGN_PUB_KEY"
echo "════════════════════════════════════════"

# ─── Vérifier la signature ────────────────────────────────────────────────────
if cosign verify \
    --key "$COSIGN_PUB_KEY" \
    "$IMAGE" 2>&1; then

    echo ""
    echo "[✔] SUCCÈS — La signature de l'image est valide."
    echo "    L'image $IMAGE peut être déployée en toute confiance."
    exit 0
else
    echo ""
    echo "[✘] ECHEC — Signature invalide ou absente !"
    echo "    DÉPLOIEMENT BLOQUÉ pour l'image : $IMAGE"
    echo "    Cette image n'a pas été produite par notre pipeline CI/CD."
    exit 1
fi
