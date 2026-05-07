"""
API Flask de Login com JWT - VERSAO VULNERAVEL (CP02 - 2TDCPR)
==============================================================
Esta versao contem vulnerabilidades INTENCIONAIS para fins didaticos.
NAO USE EM PRODUCAO. Cada VULN abaixo eh detalhada no RELATORIO.md.
"""
import os
import jwt
from flask import Flask, request, jsonify

app = Flask(__name__)

# VULN A1 - Secret hardcoded no codigo-fonte (vai pro git, vai pra layer da imagem)
JWT_SECRET = "supersecret123"

# VULN A2 - Senhas em texto plano, hardcoded no codigo
USERS = {
    "admin": {"password": "admin123",  "role": "admin"},
    "joao":  {"password": "joao2024",  "role": "user"},
}


@app.route("/", methods=["GET"])
def home():
    return jsonify({"app": "fintech-login-api", "version": "vulneravel"}), 200


@app.route("/login", methods=["POST"])
def login():
    # VULN A3 - Sem validacao de schema/tipo/tamanho do input
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = USERS.get(username)

    # VULN A4 - Comparacao de senha em texto plano (sem hashing nem tempo constante)
    if user and user["password"] == password:
        # VULN A5 - Token sem 'exp', sem 'iat' - JWT nunca expira
        token = jwt.encode(
            {"sub": username, "role": user["role"]},
            JWT_SECRET,
            algorithm="HS256",
        )
        return jsonify({"token": token}), 200

    # VULN A6 - Mensagem de erro vaza qual campo esta errado (user enumeration)
    if not user:
        return jsonify({"error": f"usuario '{username}' nao existe"}), 401
    return jsonify({"error": "senha incorreta"}), 401


@app.route("/protected", methods=["GET"])
def protected():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    try:
        # VULN A7 - Aceita 'none' como algoritmo (algorithm confusion / bypass total)
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256", "none"])
        return jsonify({"hello": payload.get("sub"), "role": payload.get("role")}), 200
    except Exception as e:
        # VULN A8 - Vaza detalhes da excecao para o cliente
        return jsonify({"error": str(e)}), 401


@app.route("/debug", methods=["GET"])
def debug():
    # VULN A9 - Endpoint de debug exposto em producao, vazando env e secrets
    return jsonify({
        "env": dict(os.environ),
        "jwt_secret": JWT_SECRET,
        "users": USERS,
    }), 200


if __name__ == "__main__":
    # VULN A10 - debug=True em producao expoe Werkzeug debugger (RCE com PIN)
    # VULN A11 - servidor Flask de desenvolvimento, sem WSGI prod-grade
    app.run(host="0.0.0.0", port=5000, debug=True)
