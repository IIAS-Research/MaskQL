# syntax=docker/dockerfile:1.6

############################
# Stage 1: Maven Build
############################
FROM maven:3.9-eclipse-temurin-24 AS builder
WORKDIR /build
COPY ./plugins/maskql-plugin/ ./
RUN --mount=type=cache,target=/root/.m2 mvn -U -DskipTests clean package
RUN mkdir -p /out && find target -maxdepth 1 -type f -name "*.jar" \
    ! -name "*-sources.jar" ! -name "*-javadoc.jar" -exec cp -v {} /out/ \;

############################
# Stage 2: Python env + HF (CPython shared + JEP build, EL8)
############################
FROM rockylinux:8 AS pyenv
USER root

ARG PSEUDOCARE_VERSION=0.1.6

# Outils + JDK + OpenMP + Git
RUN dnf -y install \
        gcc gcc-c++ make \
        openssl-devel bzip2-devel libffi-devel zlib-devel xz wget tar curl \
        java-17-openjdk-devel \
        libgomp \
    && dnf -y clean all

# Build CPython 3.11
ENV PY_VER=3.11.9
RUN curl -fsSL https://www.python.org/ftp/python/${PY_VER}/Python-${PY_VER}.tgz -o /tmp/Python.tgz \
    && cd /tmp && tar -xzf Python.tgz && cd Python-${PY_VER} \
    && ./configure --prefix=/opt/cpython311 --enable-optimizations --enable-shared \
    && make -j"$(nproc)" && make install \
    && echo "/opt/cpython311/lib" > /etc/ld.so.conf.d/cpython311.conf && ldconfig \
    && rm -rf /tmp/Python*

ENV PATH="/opt/cpython311/bin:${PATH}"
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk

# Create venv
RUN python3.11 -m venv /opt/pyenv
ENV VIRTUAL_ENV=/opt/pyenv
ENV PATH="/opt/pyenv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_COMPILE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

RUN python -m pip install --no-cache-dir --upgrade pip wheel setuptools \
    && python -m pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "numpy>=2.0" \
        "torch==2.4.*" \
        "edsnlp[ml]" \
        "huggingface_hub>=0.23"

RUN python -m pip install --no-cache-dir "pseudocare==${PSEUDOCARE_VERSION}"

# Download EDS NLP Model
WORKDIR /app
COPY python/download_edspseudo.py /app/download_eds_pseudo.py
RUN --mount=type=secret,id=HF_TOKEN \
    python3.11 /app/download_eds_pseudo.py \
        --token "$(cat /run/secrets/HF_TOKEN)" \
        --out_dir "/opt/models/eds-pseudo-public" \
    && rm -rf /root/.cache/huggingface /root/.cache/pip "$HF_HOME"

# JEP (to allow Java <-> Python communication)
ENV LDFLAGS="-Wl,-rpath,/opt/cpython311/lib"
RUN pip install --no-cache-dir --no-build-isolation "jep==4.2.2"

# For final stage
ENV CPYTHON_PREFIX=/opt/cpython311

############################
# Stage 3: Final Trino image
############################
FROM trinodb/trino:476
USER root

# Config + plugin Java for Trino
COPY --chown=trino:trino ./etc-template/ /etc/trino/
RUN mkdir -p /usr/lib/trino/plugin/maskql-plugin
COPY --from=builder --chmod=u+rwX /out/*.jar /usr/lib/trino/plugin/maskql-plugin/

# venv + EDS Pseudo model
COPY --from=pyenv --chown=trino:trino /opt/pyenv /opt/pyenv
COPY --from=pyenv --chown=trino:trino /opt/models/eds-pseudo-public /opt/models/eds-pseudo-public

# Runtime CPython
RUN mkdir -p /opt/python/lib /opt/python/lib/python3.11

# libpython.so + symlink + stdlib Python
COPY --from=pyenv /opt/cpython311/lib/libpython3.11.so.1.0 /opt/python/lib/
RUN ln -s /opt/python/lib/libpython3.11.so.1.0 /opt/python/lib/libpython3.11.so || true
COPY --from=pyenv /opt/cpython311/lib/python3.11/ /opt/python/lib/python3.11/
COPY --from=pyenv /usr/lib64/libgomp.so.1 /opt/python/lib/
COPY --from=pyenv /usr/lib64/libffi.so.6* /opt/python/lib/
COPY --from=pyenv /usr/lib64/libssl.so.1.1* /opt/python/lib/
COPY --from=pyenv /usr/lib64/libcrypto.so.1.1* /opt/python/lib/

# Python executable
RUN mkdir -p /opt/python/bin
COPY --from=pyenv /opt/cpython311/bin/python3.11 /opt/python/bin/
RUN ln -s /opt/python/bin/python3.11 /opt/python/bin/python || true
ENV PATH=/opt/python/bin:$PATH

# EDS PSEUDO Helper for JEP
COPY python/load_edspseudo.py /app/load_edspseudo.py

# ENVs for JEP/CPython
ENV PYTHONHOME=/opt/python \
    PYTHONPATH=/opt/pyenv/lib/python3.11/site-packages \
    JEP_LIBRARY_PATH=/opt/pyenv/lib/python3.11/site-packages/jep \
    LD_LIBRARY_PATH=/opt/python/lib:$LD_LIBRARY_PATH \
    EDS_PIPELINE_DIR=/usr/lib/trino/models/eds-pseudo-public

USER trino
