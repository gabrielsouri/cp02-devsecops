# =============================================================================
# CP02 - 2TDCPR - DEVSECOPS
# Dockerfile VULNERAVEL - falhas INTENCIONAIS para fins didaticos
# =============================================================================

# VULN B1 - tag 'latest': base nao reproduzivel, pode introduzir regressoes
#           e impede pinning para auditoria de CVEs.
FROM python:latest

# VULN B2 - pacotes desnecessarios na imagem final.
#           Curl/wget/vim/git/telnet/ssh viram ferramentas para o atacante
#           se ele conseguir um shell no container (LotL - living off the land).
RUN apt-get update && apt-get install -y \
    curl wget vim git net-tools telnet openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# VULN B3 - COPY do diretorio inteiro SEM .dockerignore.
#           Resultado: .env, .git/, *.pem, etc. vao parar dentro da imagem
#           e ficam acessiveis a qualquer um que faca `docker pull`.
COPY . /app

# VULN B4 - Instala dependencias desatualizadas, sem --no-cache-dir
#           (cache do pip vira lixo dentro da imagem).
RUN pip install -r requirements.txt

# VULN B5 - Secret no ENV. Vai para a layer history da imagem.
#           Qualquer um com acesso a imagem ve via `docker history` ou
#           `docker inspect`.
ENV JWT_SECRET=supersecret123
ENV ADMIN_PASSWORD=admin123
ENV DEBUG=True

# VULN B6 - Portas extras expostas sem necessidade
#           (aumenta superficie de ataque)
EXPOSE 5000
EXPOSE 22
EXPOSE 8080

# VULN B7 - Sem USER => roda como root (UID 0).
#           Container escape => root no host.
# VULN B8 - Servidor de desenvolvimento Flask em producao.
#           Werkzeug debug pin = RCE potencial.
CMD ["python", "app.py"]
