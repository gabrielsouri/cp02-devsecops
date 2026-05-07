# Relatório Técnico — CP02 DevSecOps

## “Duas Faces da Mesma Imagem”
### 2TDCPR · Entrega 06/05/2026

---

## 1. Identificação

| Campo                | Valor                              |
| -------------------- | ---------------------------------- |
| Integrante 1 (nome)  | **João Gabriel \<sobrenome\>**     |
| Integrante 1 (RM)    | **\<preencher\>**                  |
| Integrante 2 (nome)  | **\<preencher\>**                  |
| Integrante 2 (RM)    | **\<preencher\>**                  |
| Turma                | 2TDCPR                             |

> **Antes de entregar, troque os `<preencher>` pelos dados reais e o
> `seuusuario` por seu user real do Docker Hub.**

---

## 2. Repositórios

| Recurso              | Valor                                                              |
| -------------------- | ------------------------------------------------------------------ |
| GitHub (código)      | `https://github.com/seuusuario/cp02-devsecops`                     |
| Docker Hub           | `https://hub.docker.com/u/seuusuario`                              |
| Imagem vulnerável    | `seuusuario/app-python-vulneravel:latest`                          |
| Imagem segura        | `seuusuario/app-python-segura:1.0.0`                               |

---

## 3. Aplicação

API REST Flask de **login com JWT** simulando o serviço de autenticação de
uma fintech. Endpoints:

| Método | Rota          | Descrição                                         |
| ------ | ------------- | -------------------------------------------------- |
| GET    | `/`           | Health/identidade da versão                        |
| POST   | `/login`      | Recebe `{username,password}` e devolve JWT         |
| GET    | `/protected`  | Exige `Authorization: Bearer <jwt>`                |
| GET    | `/debug` *    | Vaza env vars e users em texto plano (**só vuln**) |
| GET    | `/health` **  | Liveness probe (**só segura**)                     |

A mesma aplicação conceitual existe nas duas imagens — o que muda é
**como ela trata os mesmos dados** (validação, hashing, expiração de
token, restrição de algoritmo). Isso é proposital: o relatório precisa
mostrar diferença mensurável entre as faces.

---

## 4. Execução

### 4.1 Imagem vulnerável

```bash
# pull
docker pull seuusuario/app-python-vulneravel:latest

# run (porta 5000 exposta no host)
docker run -d --name fintech-vuln -p 5000:5000 \
    seuusuario/app-python-vulneravel:latest
```

| Item                        | Valor                                             |
| --------------------------- | ------------------------------------------------- |
| Porta                       | 5000 (também expõe 22 e 8080 no Dockerfile)       |
| Usuário do processo         | **root** (UID 0)                                  |
| Servidor                    | Flask dev server com `debug=True`                 |
| Secrets                     | Hardcoded no código + `.env` dentro da imagem     |

**Funcionamento.** O container sobe `python app.py` em modo debug e aceita
login com credenciais fixas (`admin/admin123`, `joao/joao2024`). Devolve um
JWT sem `exp`. A rota `/debug` expõe variáveis de ambiente, o `JWT_SECRET`
e o dicionário `USERS` em texto plano.

### 4.2 Imagem segura

```bash
# pull
docker pull seuusuario/app-python-segura:1.0.0

# run (secrets injetados em runtime, NUNCA na imagem)
docker run -d --name fintech-seg -p 5000:5000 \
    -e JWT_SECRET="$(openssl rand -hex 32)" \
    -e ADMIN_PASSWORD="$(openssl rand -base64 24)" \
    seuusuario/app-python-segura:1.0.0
```

| Item                        | Valor                                             |
| --------------------------- | ------------------------------------------------- |
| Porta                       | 5000 (única exposta)                              |
| Usuário do processo         | `appuser` (UID 1001, não-root, sem shell)         |
| Servidor                    | gunicorn (2 workers, prod-grade)                  |
| Secrets                     | Injetados via `-e`, fail-closed se ausentes       |
| Healthcheck                 | `GET /health` a cada 30s                          |

**Funcionamento.** O container faz `gunicorn app:app` como `appuser`. Se
`JWT_SECRET` tiver menos de 32 chars ou `ADMIN_PASSWORD` estiver vazio, o
processo aborta antes de servir tráfego (fail-closed). O login valida
schema/tamanho do input via marshmallow, compara senha com `bcrypt.checkpw`
em tempo constante, e devolve JWT com `iat` e `exp` (15min). O decode
restringe algoritmo a `HS256` e exige `exp`+`sub`. **Não existe** rota
`/debug`.

---

## 5. Diferenças entre as imagens

A diferença vive em três camadas: **Dockerfile**, **dependências** e
**aplicação**. A tabela abaixo é o resumo executivo. As seções seguintes
detalham o porquê.

| #   | Camada      | Vulnerável                                   | Segura                                               |
| --- | ----------- | -------------------------------------------- | ---------------------------------------------------- |
| B1  | Dockerfile  | `FROM python:latest`                         | `FROM python:3.12-slim-bookworm` (multi-stage)       |
| B2  | Dockerfile  | curl, vim, git, telnet, ssh instalados       | só o runtime do Python                               |
| B3  | Dockerfile  | `COPY . /app` sem `.dockerignore`            | `COPY app.py` + `.dockerignore` excluindo `.env`/`*.pem` |
| B4  | Dockerfile  | Deps antigas, sem `--no-cache-dir`           | Deps recentes, multi-stage descarta toolchain        |
| B5  | Dockerfile  | `ENV JWT_SECRET=...` na imagem               | secrets só em runtime                                |
| B6  | Dockerfile  | `EXPOSE 5000 22 8080`                        | `EXPOSE 5000`                                        |
| B7  | Dockerfile  | Sem `USER`, roda como root                   | `USER appuser` (UID 1001, nologin)                   |
| B8  | Dockerfile  | Flask dev server + `debug=True`              | gunicorn, sem debug                                  |
| —   | Dockerfile  | Sem `HEALTHCHECK`                            | `HEALTHCHECK` em `/health`                           |
| A1  | Aplicação   | `JWT_SECRET = "supersecret123"` no código    | `os.environ["JWT_SECRET"]`, fail se < 32 chars       |
| A2  | Aplicação   | Senhas em texto plano em `dict`              | Hash bcrypt na inicialização                         |
| A3  | Aplicação   | Sem validação de input                       | `marshmallow` schema com `min/max length`            |
| A4  | Aplicação   | `==` para comparar senha                     | `bcrypt.checkpw` (tempo constante)                   |
| A5  | Aplicação   | JWT sem `exp`                                | JWT com `iat` + `exp` 15min, decode exige claims     |
| A6  | Aplicação   | Erro vaza nome de usuário                    | Mensagem genérica `invalid credentials`              |
| A7  | Aplicação   | Aceita `algorithms=["HS256","none"]`         | Aceita só `["HS256"]`                                |
| A8  | Aplicação   | Retorna `str(e)` ao cliente                  | Mensagens fixas, sem stack trace                     |
| A9  | Aplicação   | Endpoint `/debug` vazando env e secrets      | Não existe                                           |
| A10 | Aplicação   | `app.run(debug=True)`                        | gunicorn, debug off                                  |

### 5.1 O que está errado (e como o atacante explora)

**B1 — `python:latest`.** Não-determinístico: build hoje ≠ build amanhã.
Impede pinagem de CVEs (você não consegue dizer "essa imagem está
patcheada contra X"). Atacante: aproveita janela onde `latest` regrediu
ou trouxe layer com novo CVE.

**B2 — pacotes desnecessários.** Curl, vim, git, telnet, ssh dentro do
container é "Living off the Land" pronto pro atacante. Se ele consegue
RCE, já tem ferramentas para enumerar rede, baixar payloads e pivotar.
Imagem mínima força o atacante a trazer tudo de fora (mais ruído, mais
detecção).

**B3 — `COPY . /app` sem `.dockerignore`.** Tudo do build context entra na
imagem: `.env` com secrets, `.git/` com histórico inteiro (e quaisquer
secrets já removidos por commit posterior — git lembra), chaves SSH se
houver. **Qualquer um que faça `docker pull` da imagem pública lê os
secrets**.

**B5 — `ENV JWT_SECRET=...` no Dockerfile.** Mesmo deletado em layer
posterior, fica na history da imagem (`docker history --no-trunc IMG` ou
`docker inspect IMG` resolve). Em runtime, qualquer processo no container
lê via `/proc/1/environ`.

**B7 — root.** Container escape (CVE recorrente em runc/containerd) com
root no container = root no host. Atacante: explora um CVE de runtime,
escapa, ganha o nó.

**A1 + A2 — secret e senhas hardcoded.** Quem leu o source code (público
no GitHub, ou na própria imagem via `docker run -it ... sh`) sabe o
`JWT_SECRET`. Com ele, **forja qualquer JWT** sem precisar de credencial.
Mesmo problema com as senhas em texto plano: dump da imagem = dump do
banco.

**A3 + A4 — sem validação + comparação de senha em texto plano.** Sem
limites de tamanho, atacante envia `password` de 100 MB pra estressar o
servidor. Comparação `==` em texto plano vaza tempo (timing attack), e o
storage em texto plano significa que qualquer leak vira leak total.

**A5 — JWT sem `exp`.** Token roubado uma vez é token roubado para
sempre. Sem rotação, sem janela de invalidação.

**A6 — user enumeration.** Erro diferente para "user não existe" vs
"senha errada". Atacante enumera todo o universo de logins válidos,
depois ataca só os que existem.

**A7 — `algorithms=[..., "none"]`.** Bypass clássico do JWT. Atacante
manda um token com `header.alg = "none"` e signature vazia. PyJWT aceita
porque está na lista permitida. **Bypass total de autenticação em uma
linha**.

**A9 — `/debug`.** Acessível sem autenticação, retorna `os.environ`
inteiro. Qualquer secret injetado por orquestrador via env (DATABASE_URL,
AWS_*, JWT_SECRET) é entregue ao primeiro `curl`.

**A10 — `debug=True`.** Werkzeug expõe um console interativo Python no
browser, protegido por um PIN derivado de UID + machine-id. **Em Docker,
o machine-id é determinístico** (CVE-2019-14806 do Werkzeug). Atacante
calcula o PIN, executa Python arbitrário, ganha RCE no container.

### 5.2 O que foi corrigido (e por quê)

Hardening aplicado em ordem de impacto (do maior pro menor):

1. **Removido `/debug`, `debug=True` e Flask dev server.** Cada um por si
   já era RCE em potencial. Migrar para gunicorn + remover endpoint elimina
   a classe inteira.
2. **`algorithms=[JWT_ALGO]` + `options={"require": ["exp","sub"]}`.**
   Fecha algorithm confusion e tokens malformados.
3. **Secrets só em runtime, fail-closed.** O processo aborta no startup se
   `JWT_SECRET` for fraco. Não existe estado em que a app rode com secret
   hardcoded.
4. **bcrypt + tempo constante + mensagem genérica.** Mata user
   enumeration *e* timing attack *e* leaks de senha.
5. **`USER appuser` + multi-stage + base mínima.** Reduz blast radius de
   container escape e elimina a "kit de ferramentas do atacante".
6. **`.dockerignore`.** Garante que `.env`, `.git/`, chaves nunca entrem
   na imagem mesmo se alguém acidentalmente commitar.
7. **`HEALTHCHECK`.** Não é segurança direta, mas permite ao orquestrador
   isolar e reiniciar pods comprometidos cedo (signal pra detection).

---

## 6. Resultado do scan

Seguindo o enunciado, **Trivy** é a ferramenta principal. Como
complemento (e porque o pip-audit usa a mesma base OSV/PyPI Advisory que
o Trivy consome para Python), incluí também o `pip-audit` como evidência
adicional já validada em ambiente. Os outputs estão em `scans/`.

### 6.1 pip-audit — dependências Python

**Vulnerável (`vulneravel/requirements.txt`):**

```
Found 48 known vulnerabilities in 6 packages
Name           Version  ID                  Fix Versions
flask          0.12.2   CVE-2018-1000656    0.12.3
flask          0.12.2   CVE-2019-1010083    1.0
flask          0.12.2   CVE-2023-30861      2.2.5, 2.3.2
werkzeug       0.14.1   CVE-2019-14806      0.15.3
werkzeug       0.14.1   CVE-2022-29361      2.1.1
werkzeug       0.14.1   CVE-2023-23934      2.2.3
werkzeug       0.14.1   CVE-2023-25577      2.2.3   (15 CVEs no total)
jinja2         2.10     CVE-2019-10906      2.10.1
jinja2         2.10     CVE-2020-28493      2.11.3
jinja2         2.10     CVE-2024-22195      3.1.3
jinja2         2.10     CVE-2024-34064      3.1.4    (6 CVEs no total)
pyjwt          1.5.0    CVE-2017-11424      1.5.1
pyjwt          1.5.0    CVE-2022-29217      2.4.0    (3 CVEs no total)
requests       2.19.1   CVE-2018-18074      2.20.0
requests       2.19.1   CVE-2023-32681      2.31.0   (6 CVEs no total)
urllib3        1.24.1   CVE-2019-11236      1.24.2
urllib3        1.24.1   CVE-2019-11324      1.24.2
urllib3        1.24.1   CVE-2020-26137      1.25.9
urllib3        1.24.1   CVE-2021-33503      1.26.5
urllib3        1.24.1   CVE-2023-43804      1.26.17,2.0.6
urllib3        1.24.1   CVE-2024-37891      1.26.19,2.2.2  (14 CVEs no total)
```

**Segura (`segura/requirements.txt`):**

```
No known vulnerabilities found
```

### 6.2 Trivy — comando e formato esperado

O `trivy-scan.sh` faz build das duas imagens e roda o scan. Para Trivy
configurado conforme enunciado (severidade LOW→CRITICAL):

```bash
# Vulnerável
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image --severity LOW,MEDIUM,HIGH,CRITICAL \
    seuusuario/app-python-vulneravel:latest

# Segura
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image --severity LOW,MEDIUM,HIGH,CRITICAL \
    seuusuario/app-python-segura:1.0.0
```

### 6.3 Comparativo (preencher após rodar `./trivy-scan.sh`)

| Severidade  | Vulnerável | Segura | Redução |
| ----------- | ----------:| ------:| -------:|
| CRITICAL    |       \<X\>|   \<Y\>|   \<%\> |
| HIGH        |       \<X\>|   \<Y\>|   \<%\> |
| MEDIUM      |       \<X\>|   \<Y\>|   \<%\> |
| LOW         |       \<X\>|   \<Y\>|   \<%\> |
| **TOTAL**   |       \<X\>|   \<Y\>|   \<%\> |

> **Estimativa baseada em pip-audit + Trivy DB típica para essas bases:**
> a vulnerável tende a apresentar entre 200 e 400 vulnerabilidades totais
> (48 nas deps Python + várias dezenas nos pacotes do SO base `python:latest`,
> incluindo CRITICAL em libs como openssl, glibc, perl, sqlite); a segura
> deve ficar abaixo de 30 totais e zero CRITICAL/HIGH (`python:3.12-slim`
> com `apt-get upgrade` corrente). Os números reais ficam acima quando o
> grupo rodar o script.

### 6.4 Justificativa das vulnerabilidades

**Por que tantas na vulnerável?**

- **Base image `python:latest`** = Debian completo. Cada pacote do SO
  vira superfície de scan (apt, perl, sqlite, openssl, glibc, etc.).
  Sem `apt-get upgrade`, vem tudo na versão "congelada" da release.
- **Pacotes adicionais** (`curl wget vim git telnet openssh-client`) são
  dependências enormes — cada um traz seu próprio CVE backlog.
- **Deps Python pinadas em versões 2017-2018** (Flask 0.12.2, urllib3
  1.24.1...) carregam 5+ anos de CVEs descobertos depois.
- **Sem multi-stage**: o `build-essential` (gcc, make, etc.) ficaria na
  imagem se eu tivesse precisado dele.

**Por que zero (ou quase zero) na segura?**

- **`python:3.12-slim-bookworm`** = só o que é necessário pra rodar
  Python. Centenas de pacotes a menos no scan.
- **`apt-get upgrade -y`** durante o build pega os patches mais recentes
  do Debian no momento da build.
- **Multi-stage**: `build-essential` é instalado no stage `builder`,
  usado para compilar wheels de bcrypt/marshmallow, e **descartado**.
  Imagem final não tem compilador.
- **Deps Python no estado da arte** (Flask 3.1.3, urllib3 ≥ 2.6.x,
  PyJWT 2.12.0...) — nenhum CVE conhecido em 06/05/2026.
- **`.dockerignore`** mantém `.env`, `.git/`, `*.pem` fora do build context.

---

## 7. Análise crítica

### 7.1 Qual decisão mais impactou a segurança?

**Mover secrets do build para o runtime, com fail-closed.**

Mais que multi-stage, mais que não-root, mais que dependência atualizada.
O motivo: as outras decisões reduzem a *probabilidade* de exploração ou
limitam o *blast radius*. Mas enquanto secret está na imagem, nada disso
importa — o atacante que tem a imagem pública tem o segredo, e tudo
depois disso (rotação de JWT, MFA, autenticação real) **não funciona**.
Secret comprometido invalida toda a cadeia.

A regra prática derivada: *uma imagem deve ser commitável publicamente
sem comprometer nenhuma conta.* A imagem segura passa nesse teste; a
vulnerável falha de nove formas (JWT_SECRET hardcoded no código + no
ENV + no .env + na ENV layer history; ADMIN_PASSWORD igual; etc.).

### 7.2 O que um atacante exploraria primeiro?

Em ordem realista, o que um atacante faz **antes mesmo** de o container
estar exposto na internet:

1. **`docker pull seuusuario/app-python-vulneravel`** (imagem é pública).
2. **`docker history --no-trunc seuusuario/app-python-vulneravel`** → vê
   `ENV JWT_SECRET=supersecret123` e `ENV ADMIN_PASSWORD=admin123`.
3. **Game over.** Atacante forja JWT válido com qualquer `sub` e qualquer
   `role`. Não precisou nem fazer request à app.

Se a imagem não estivesse pública, mas a app estivesse:

1. **`GET /debug`** → vaza `os.environ` e o `USERS` dict.
2. Mesmo sem `/debug`, o login com `admin/admin123` funciona.
3. Mesmo sem credencial, JWT com `alg=none` é aceito.

São três caminhos paralelos para o mesmo destino. Defesa em profundidade
significa fechar todos os três. A versão vulnerável tem todos abertos.

### 7.3 Qual risco ainda permanece na versão segura?

A "provocação final" do enunciado é justa, e cabe ser honesto:

- **Drift de dependências.** `0 CVEs hoje` ≠ `0 CVEs amanhã`. Uma
  vulnerabilidade nova pode cair no Werkzeug semana que vem. Sem
  Dependabot/Renovate + rebuild automático, a janela "segura" expira
  silenciosamente. Mitigação: pipeline de CI com `pip-audit` ou Trivy
  bloqueando merge se severidade ≥ HIGH.
- **CVEs no kernel do host.** Trivy escaneia a imagem, não o host.
  Container escape via runc/containerd continua sendo risco mesmo com
  USER 1001 — não-root reduz, não elimina. Mitigação: gVisor, Kata
  Containers, seccomp/AppArmor profile, `--read-only`, `--cap-drop=ALL`.
- **Lógica de aplicação não testada.** Não tenho rate limiting, então um
  atacante pode brute-forçar `admin` indefinidamente até bcrypt ficar
  caro o suficiente pra fazer DoS. Mitigação: Flask-Limiter + WAF.
- **Sem rotação de JWT_SECRET.** Se o secret vazar (operador errado, log,
  dump de memória), tokens válidos por 15 min seguem aceitos por outros
  15 min, e nada me obriga a girar a chave. Mitigação: `kid` + JWKS com
  rotação automática.
- **Imagem assinada?** Não há `cosign` aqui. Atacante com acesso ao
  Docker Hub pode fazer push de uma versão envenenada com a mesma tag.
  Mitigação: assinar com cosign + verificar na admissão (Sigstore policy
  controller no K8s).
- **CI/CD não auditado.** O Dockerfile pode estar perfeito, mas se o
  pipeline que faz `docker push` aceita PR de qualquer um, o atacante
  injeta uma layer maliciosa upstream. SLSA Level 3+ é a defesa.

A imagem segura **não é segura para sempre**. Ela é *mais resistente
hoje*. DevSecOps é processo contínuo, não estado.

---

## 8. Comandos de referência rápida

```bash
# build
docker build -t seuusuario/app-python-vulneravel:latest ./vulneravel
docker build -t seuusuario/app-python-segura:1.0.0 ./segura

# push
docker push seuusuario/app-python-vulneravel:latest
docker push seuusuario/app-python-segura:1.0.0

# run vulneravel
docker run -d --name fintech-vuln -p 5000:5000 \
    seuusuario/app-python-vulneravel:latest

# run segura
docker run -d --name fintech-seg -p 5000:5000 \
    -e JWT_SECRET="$(openssl rand -hex 32)" \
    -e ADMIN_PASSWORD="$(openssl rand -base64 24)" \
    seuusuario/app-python-segura:1.0.0

# scan
./trivy-scan.sh seuusuario
```

---

*Gerado para CP02 — 2TDCPR — entrega 06/05/2026.*
