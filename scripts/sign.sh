#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  sign.sh — Signature d'image Docker avec Cosign
#  Usage : ./scripts/sign.sh <IMAGE:TAG> <CHEMIN_CLE_PRIVEE>
#  Env   : COSIGN_PASSWORD (obligatoire)
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

IMAGE="${1:-}"
COSIGN_KEY="${2:-cosign.key}"

# ─── Validation ───────────────────────────────────────────────────────────────
if [[ -z "$IMAGE" ]]; then
    echo "[ERREUR] Usage : $0 <image:tag> [chemin_cle.key]"
    exit 1
fi

if [[ -z "${COSIGN_PASSWORD:-}" ]]; then
    echo "[ERREUR] Variable d'environnement COSIGN_PASSWORD non définie."
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
echo " COSIGN — Signature de l'image"
echo " Image : $IMAGE"
echo " Clé   : $COSIGN_KEY"
echo "════════════════════════════════════════"

# ─── Générer la paire de clés si elle n'existe pas ───────────────────────────
if [[ ! -f "$COSIGN_KEY" ]]; then
    echo "[*] Génération d'une nouvelle paire de clés Cosign..."
    cosign generate-key-pair
    echo "[+] Clés générées : cosign.key (privée) + cosign.pub (publique)"
fi

# ─── Signer l'image ───────────────────────────────────────────────────────────
echo "[*] Signature en cours..."
COSIGN_PASSWORD="$COSIGN_PASSWORD" cosign sign \
    --key "$COSIGN_KEY" \
    --yes \
    --annotations "signed-by=jenkins-pipeline" \
    --annotations "build-date=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$IMAGE"

echo "[+] Image signée avec succès : $IMAGE"
