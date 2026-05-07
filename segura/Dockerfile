# =============================================================================
# CP02 - 2TDCPR - DEVSECOPS
# Dockerfile SEGURO - hardening DevSecOps aplicado
# =============================================================================
# Tecnicas usadas:
#   - multi-stage build (descarta toolchain do build na imagem final)
#   - base minima e fixada (python:3.12-slim-bookworm)
#   - apt-get upgrade para fechar CVEs do SO no momento do build
#   - usuario nao-root com UID >= 1000
#   - .dockerignore exclui .env, .git, *.pem, etc.
#   - sem secrets na imagem (passados via runtime)
#   - HEALTHCHECK para orquestrador detectar pod degradado
#   - servidor WSGI prod-grade (gunicorn) em vez de Flask dev server
# =============================================================================

# ---------- Stage 1: builder (descartado depois) -----------------------------
FROM python:3.12-slim-bookworm AS builder

# Atualizacao do SO + toolchain so para o build
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user --upgrade pip \
 && pip install --no-cache-dir --user -r requirements.txt


# ---------- Stage 2: runtime (imagem final) ----------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Atualiza pacotes do SO (fecha CVEs conhecidos no momento do build)
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Usuario nao-root, UID nao-privilegiado, sem shell de login
RUN groupadd --system --gid 1001 appuser \
 && useradd  --system --uid 1001 --gid appuser \
              --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copia dependencias instaladas pelo builder (sem build-essential, sem cache)
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copia APENAS o codigo da aplicacao (.dockerignore exclui o resto)
COPY --chown=appuser:appuser app.py /app/app.py

# Drop de privilegios
USER appuser

# Hardening de runtime do Python
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    FLASK_ENV=production \
    PIP_NO_CACHE_DIR=1

# JWT_SECRET e ADMIN_PASSWORD NAO sao definidos aqui de proposito.
# Devem ser injetados em runtime: docker run -e JWT_SECRET=... -e ADMIN_PASSWORD=...

EXPOSE 5000

# Healthcheck simples - se /health nao responde, orquestrador reinicia
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=2).status==200 else 1)"

# Servidor WSGI de producao (gunicorn), 2 workers, log estruturado em stdout
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
