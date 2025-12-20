# BASE IMAGE
FROM nvidia/cuda:12.2.0-devel-ubuntu20.04

# SYSTEM DEPENDENCIES
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    libsqlite3-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Link python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# PROJECT SETUP
WORKDIR /code
COPY . /code

# INSTALL LIBRARIES
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --default-timeout=1000 --no-cache-dir -r requirements.txt

# EXECUTION
RUN chmod +x /code/inference.sh
CMD ["bash", "inference.sh"]
