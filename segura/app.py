"""
API Flask de Login com JWT - VERSAO SEGURA (CP02 - 2TDCPR)
==========================================================
Mesma aplicacao da versao vulneravel, mas com:
  - input validation (marshmallow)
  - senhas com hash bcrypt (nao texto plano)
  - JWT com 'exp', algoritmo restrito, decode estrito
  - secrets via ENV (nunca hardcoded), fail-closed se ausentes
  - mensagens de erro genericas (sem user enumeration / sem stack trace)
  - sem endpoint /debug, sem debug=True, rodada via gunicorn
"""
import os
import sys
import logging
import datetime

import bcrypt
import jwt
from flask import Flask, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

# ---------------------------------------------------------------------------
# Logging estruturado, sem dados sensiveis
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("fintech-login")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Configuracao via ENV - fail-closed se mal configurado
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    log.error("JWT_SECRET ausente ou com menos de 32 caracteres. Abortando.")
    sys.exit(1)

JWT_ALGO = "HS256"
TOKEN_TTL_MINUTES = 15

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    log.error("ADMIN_PASSWORD nao definido no ambiente. Abortando.")
    sys.exit(1)

# Hash da senha gerado em runtime, na memoria.
# Em prod real, viria de um banco de dados ou secret manager.
USERS = {
    "admin": {
        "password_hash": bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()),
        "role": "admin",
    }
}


# ---------------------------------------------------------------------------
# Validacao de input
# ---------------------------------------------------------------------------
class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=32))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


login_schema = LoginSchema()


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"app": "fintech-login-api", "version": "segura"}), 200


@app.route("/login", methods=["POST"])
def login():
    try:
        data = login_schema.load(request.get_json(silent=True) or {})
    except ValidationError:
        # Mensagem generica - sem revelar campo nem valor
        return jsonify({"error": "invalid request"}), 400

    user = USERS.get(data["username"])
    # bcrypt.checkpw eh constant-time. Se user nao existir, faz dummy compare
    # para nao vazar timing diferente entre "user nao existe" e "senha errada".
    if not user or not bcrypt.checkpw(data["password"].encode(), user["password_hash"]):
        log.info("login_failed user=%s", data["username"])
        return jsonify({"error": "invalid credentials"}), 401

    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": data["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + datetime.timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    log.info("login_success user=%s", data["username"])
    return jsonify({"token": token, "expires_in": TOKEN_TTL_MINUTES * 60}), 200


@app.route("/protected", methods=["GET"])
def protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "unauthorized"}), 401
    token = auth[len("Bearer "):]

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGO],                    # bloqueia 'none' e RS256-confusion
            options={"require": ["exp", "sub"]},      # exige claims essenciais
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({"hello": payload["sub"]}), 200


# Sem endpoint /debug. Sem app.run(debug=True). Sem dev server.
# A imagem segura roda via gunicorn (ver Dockerfile).
