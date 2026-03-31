#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  scan.sh — Scan de vulnérabilités avec Trivy
#  Usage : ./scripts/scan.sh <IMAGE:TAG>
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

IMAGE="${1:-}"
REPORTS_DIR="reports"
SEVERITY="${SEVERITY:-HIGH,CRITICAL}"
EXIT_ON_VULN="${EXIT_ON_VULN:-1}"

# ─── Validation ───────────────────────────────────────────────────────────────
if [[ -z "$IMAGE" ]]; then
    echo "[ERREUR] Usage : $0 <image:tag>"
    exit 1
fi

# ─── Vérifier Trivy ───────────────────────────────────────────────────────────
if ! command -v trivy &>/dev/null; then
    echo "[*] Installation de Trivy..."
    TRIVY_VERSION="0.50.1"
    wget -q "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
    tar -xzf "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
    mv trivy /usr/local/bin/trivy
    rm -f "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
fi

mkdir -p "$REPORTS_DIR"

echo "════════════════════════════════════════"
echo " TRIVY — Scan de l'image : $IMAGE"
echo " Sévérités : $SEVERITY"
echo "════════════════════════════════════════"

# ─── Rapport JSON ────────────────────────────────────────────────────────────
trivy image \
    --format json \
    --output "${REPORTS_DIR}/trivy-report.json" \
    --severity "$SEVERITY" \
    --exit-code 0 \
    "$IMAGE"

# ─── Rapport lisible (terminal) ──────────────────────────────────────────────
trivy image \
    --format table \
    --severity "$SEVERITY" \
    --exit-code "$EXIT_ON_VULN" \
    "$IMAGE"

CRITICAL_COUNT=$(python3 -c "
import json, sys
try:
    with open('${REPORTS_DIR}/trivy-report.json') as f:
        data = json.load(f)
    count = sum(
        1 for result in data.get('Results', [])
        for vuln in result.get('Vulnerabilities', [])
        if vuln.get('Severity') == 'CRITICAL'
    )
    print(count)
except Exception:
    print(0)
" 2>/dev/null)

echo ""
echo "─── Résumé ──────────────────────────────"
echo " Image   : $IMAGE"
echo " CRITICAL: $CRITICAL_COUNT vulnérabilité(s)"
echo " Rapport : ${REPORTS_DIR}/trivy-report.json"
echo "─────────────────────────────────────────"

if [[ "$CRITICAL_COUNT" -gt 0 && "$EXIT_ON_VULN" == "1" ]]; then
    echo "[ECHEC] $CRITICAL_COUNT vulnérabilité(s) CRITICAL trouvée(s). Build bloqué."
    exit 1
fi

echo "[+] Scan terminé avec succès."
