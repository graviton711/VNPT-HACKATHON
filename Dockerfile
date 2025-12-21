# BASE IMAGE
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

# SYSTEM DEPENDENCIES
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Link python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# PROJECT SETUP
# PROJECT SETUP
WORKDIR /code

# OPTIMIZATION: Install dependencies first (Cached)
COPY requirements.txt /code/
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --default-timeout=100 -r requirements.txt

# Strict ChromaDB Configuration to prevent timeouts/telemetry
ENV ANONYMIZED_TELEMETRY=False
ENV CHROMA_CLIENT_AUTH_PROVIDER=chromadb.auth.impl.noop.NoAuthClientProvider
ENV CHROMA_SERVER_NOINTERACTIVE=True
ENV ALLOW_RESET=True

# Copy the current directory contents into the container at /code
COPY . /code

# EXECUTION
RUN chmod +x /code/inference.sh
CMD ["bash", "inference.sh"]