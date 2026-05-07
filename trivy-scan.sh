#!/usr/bin/env bash
# =============================================================================
# CP02 - 2TDCPR - DevSecOps
# Script: build das duas imagens + scan Trivy + comparativo
# =============================================================================
# Uso:
#   chmod +x trivy-scan.sh
#   ./trivy-scan.sh SEU_USUARIO_DOCKERHUB
# =============================================================================

set -euo pipefail

USER="${1:-seuusuario}"
IMG_VULN="${USER}/app-python-vulneravel:latest"
IMG_SEG="${USER}/app-python-segura:1.0.0"

OUT_DIR="./scans"
mkdir -p "$OUT_DIR"

echo "=========================================="
echo "[1/4] Build da imagem VULNERAVEL"
echo "=========================================="
docker build -t "$IMG_VULN" ./vulneravel

echo
echo "=========================================="
echo "[2/4] Build da imagem SEGURA"
echo "=========================================="
docker build -t "$IMG_SEG" ./segura

echo
echo "=========================================="
echo "[3/4] Trivy scan - VULNERAVEL"
echo "=========================================="
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD/$OUT_DIR":/out \
    aquasec/trivy:latest image \
    --severity LOW,MEDIUM,HIGH,CRITICAL \
    --format table \
    --output /out/trivy-vulneravel.txt \
    "$IMG_VULN"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD/$OUT_DIR":/out \
    aquasec/trivy:latest image \
    --severity LOW,MEDIUM,HIGH,CRITICAL \
    --format json \
    --output /out/trivy-vulneravel.json \
    "$IMG_VULN"

echo
echo "=========================================="
echo "[4/4] Trivy scan - SEGURA"
echo "=========================================="
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD/$OUT_DIR":/out \
    aquasec/trivy:latest image \
    --severity LOW,MEDIUM,HIGH,CRITICAL \
    --format table \
    --output /out/trivy-segura.txt \
    "$IMG_SEG"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD/$OUT_DIR":/out \
    aquasec/trivy:latest image \
    --severity LOW,MEDIUM,HIGH,CRITICAL \
    --format json \
    --output /out/trivy-segura.json \
    "$IMG_SEG"

echo
echo "=========================================="
echo "COMPARATIVO (contagem por severidade)"
echo "=========================================="
python3 - <<PYEOF
import json
def count(path):
    with open(path) as f:
        d = json.load(f)
    sev = {"LOW":0, "MEDIUM":0, "HIGH":0, "CRITICAL":0, "UNKNOWN":0}
    for r in d.get("Results", []) or []:
        for v in r.get("Vulnerabilities", []) or []:
            s = v.get("Severity","UNKNOWN").upper()
            sev[s] = sev.get(s,0)+1
    return sev

v = count("$OUT_DIR/trivy-vulneravel.json")
s = count("$OUT_DIR/trivy-segura.json")
print(f"{'Severidade':<12} {'VULNERAVEL':>12} {'SEGURA':>10} {'Reducao':>10}")
print("-"*48)
for k in ["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]:
    red = "100%" if v[k] and not s[k] else (f"{(v[k]-s[k])/v[k]*100:.0f}%" if v[k] else "n/a")
    print(f"{k:<12} {v[k]:>12} {s[k]:>10} {red:>10}")
print("-"*48)
tv = sum(v.values()); ts = sum(s.values())
print(f"{'TOTAL':<12} {tv:>12} {ts:>10} {(tv-ts)/tv*100 if tv else 0:>9.0f}%")
PYEOF

echo
echo "Outputs salvos em: $OUT_DIR/"
echo
echo "Para publicar no Docker Hub:"
echo "  docker login"
echo "  docker push $IMG_VULN"
echo "  docker push $IMG_SEG"
