# Use a lightweight Ubuntu base
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget curl gnupg2 ca-certificates git \
    python3 python3-pip make build-essential \
    ghostscript fontconfig software-properties-common \
    texlive-full latexmk && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Cloud Run port (though Discord bot won’t use HTTP)
EXPOSE 8080

# Run your bot
CMD ["python3", "main.py"]
