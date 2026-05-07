# CP02 — DevSecOps · Duas Faces da Mesma Imagem

API Flask de login com JWT publicada em **duas versões Docker** com objetivo
didático: uma vulnerável (insegura por design) e uma segura (hardening
DevSecOps). Inclui scan Trivy comparativo.

> Disciplina: **2TDCPR**
> Entrega: **06/05/2026**

---

## Estrutura

```
cp02-devsecops/
├── vulneravel/        # app + Dockerfile vulneravel + .env vazado de proposito
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── segura/            # app + Dockerfile seguro + .dockerignore
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── scans/             # outputs do pip-audit e Trivy
├── trivy-scan.sh      # build + scan + comparativo
├── README.md
└── RELATORIO.md       # relatorio tecnico (entregavel principal)
```

---

## Build local

```bash
# vulneravel
docker build -t SEU_USUARIO/app-python-vulneravel:latest ./vulneravel

# segura
docker build -t SEU_USUARIO/app-python-segura:1.0.0 ./segura
```

---

## Execução

### Imagem vulnerável (porta 5000)

```bash
docker pull SEU_USUARIO/app-python-vulneravel:latest
docker run -d --name fintech-vuln -p 5000:5000 SEU_USUARIO/app-python-vulneravel:latest

# Login:
curl -X POST http://localhost:5000/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'

# Endpoint vazando segredos:
curl http://localhost:5000/debug
```

### Imagem segura (porta 5000)

```bash
docker pull SEU_USUARIO/app-python-segura:1.0.0
docker run -d --name fintech-seg -p 5000:5000 \
    -e JWT_SECRET="$(openssl rand -hex 32)" \
    -e ADMIN_PASSWORD="$(openssl rand -base64 24)" \
    SEU_USUARIO/app-python-segura:1.0.0

# Login (use a senha gerada acima):
curl -X POST http://localhost:5000/login \
     -H "Content-Type: application/json" \
     -d "{\"username\":\"admin\",\"password\":\"<ADMIN_PASSWORD>\"}"
```

> `JWT_SECRET` e `ADMIN_PASSWORD` **precisam** ser passados em runtime — a
> imagem segura faz fail-closed se não estiverem definidos.

---

## Scan de vulnerabilidades

### Trivy (oficial, conforme enunciado)

```bash
./trivy-scan.sh SEU_USUARIO
```

Gera em `scans/`:

- `trivy-vulneravel.txt` / `trivy-vulneravel.json`
- `trivy-segura.txt` / `trivy-segura.json`
- comparativo no terminal

### pip-audit (já executado, evidência em `scans/`)

```bash
pip-audit -r vulneravel/requirements.txt --disable-pip --no-deps   # 48 CVEs
pip-audit -r segura/requirements.txt    --disable-pip --no-deps    # 0 CVEs
```

---

## Publicação no Docker Hub

```bash
docker login
docker push SEU_USUARIO/app-python-vulneravel:latest
docker push SEU_USUARIO/app-python-segura:1.0.0
```

---

## Relatório técnico

Veja [`RELATORIO.md`](./RELATORIO.md) — diferenças entre as imagens, output do
Trivy, análise crítica e riscos residuais.
