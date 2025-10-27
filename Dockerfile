# Ubuntu 22.04 base
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# OS deps
RUN apt-get update && apt-get install -y \
    wget curl gnupg2 ca-certificates git \
    python3 python3-pip make build-essential \
    ghostscript fontconfig software-properties-common \
 && rm -rf /var/lib/apt/lists/*

# --- MiKTeX repo & install ---
RUN wget -qO - https://miktex.org/download/gpg/miktex.gpg | gpg --dearmor > /usr/share/keyrings/miktex.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/miktex.gpg] http://miktex.org/download/ubuntu jammy universe" \
    > /etc/apt/sources.list.d/miktex.list \
 && apt-get update \
 && apt-get install -y miktex \
 && rm -rf /var/lib/apt/lists/*

# Configure MiKTeX for headless auto-install of packages
RUN miktexsetup --shared=yes finish \
 && initexmf --admin --set-config-value=[MPM]AutoInstall=1 \
 && initexmf --admin --update-fndb \
 && mpm --admin --update-db \
 && mpm --admin --update
# Optional: prewarm tools to avoid first-run lag
# RUN mpm --admin --install=latexmk && initexmf --admin --update-fndb

# App setup
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY . /app

# Default command (NOTE: your entry is main.py)
CMD ["python3", "main.py"]
