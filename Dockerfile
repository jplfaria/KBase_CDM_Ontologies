# Multi-stage Dockerfile for KBase CDM Ontologies Pipeline
FROM ubuntu:22.04 AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Python and pip
    python3.10 \
    python3-pip \
    python3-venv \
    # Java for ROBOT and relation-graph
    openjdk-17-jre-headless \
    # Build tools
    build-essential \
    curl \
    wget \
    git \
    # Rust for rdftab.rs
    cargo \
    rustc \
    # Database tools
    sqlite3 \
    # Required for some Python packages
    libxml2-dev \
    libxslt1-dev \
    # Utilities
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Set Python3 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Create non-root user with matching host UID to avoid permission issues
RUN useradd -u 502 -m -s /bin/bash ontology && \
    mkdir -p /home/ontology/tools /home/ontology/workspace

# Install ROBOT (latest version)
ENV ROBOT_VERSION=1.9.8
RUN cd /home/ontology/tools && \
    wget https://github.com/ontodev/robot/releases/download/v${ROBOT_VERSION}/robot.jar && \
    wget https://raw.githubusercontent.com/ontodev/robot/master/bin/robot && \
    chmod +x robot && \
    sed -i 's|^\(java\)|/usr/bin/java|' robot

# Install relation-graph (latest version)
ENV RELATION_GRAPH_VERSION=2.3.2
RUN cd /home/ontology/tools && \
    wget https://github.com/INCATools/relation-graph/releases/download/v${RELATION_GRAPH_VERSION}/relation-graph-cli-${RELATION_GRAPH_VERSION}.tgz && \
    tar -xzf relation-graph-cli-${RELATION_GRAPH_VERSION}.tgz && \
    rm relation-graph-cli-${RELATION_GRAPH_VERSION}.tgz && \
    mv relation-graph-cli-${RELATION_GRAPH_VERSION} relation-graph

# Install rdftab.rs (required for semsql make) from git
RUN cargo install --git https://github.com/ontodev/rdftab.rs --root /home/ontology/tools

# Set up environment paths
ENV PATH="/home/ontology/tools/bin:/home/ontology/tools:/home/ontology/tools/relation-graph/bin:${PATH}"
ENV ROBOT_JAVA_ARGS="-Xmx8g"
ENV _JAVA_OPTIONS="-Xmx8g"

# Copy requirements and install Python dependencies globally as root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Switch to non-root user
USER ontology
WORKDIR /home/ontology/workspace

# Copy the application code
COPY --chown=ontology:ontology . .

# Note: Output directories are created by host mount and script logic

# Default command
CMD ["python", "-m", "cdm_ontologies", "--help"]