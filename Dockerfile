# Multi-stage Dockerfile for KBase CDM Ontologies Pipeline
FROM ubuntu:22.04 AS base

# Accept build arguments for dynamic user creation
ARG USER_ID=1000
ARG GROUP_ID=1000

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
    # For dynamic user switching
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Set Python3 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Create non-root user with dynamic UID/GID matching the host system
RUN groupadd -g ${GROUP_ID} ontology || true && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash ontology || true && \
    mkdir -p /home/ontology/tools /home/ontology/workspace && \
    chown -R ${USER_ID}:${GROUP_ID} /home/ontology || true

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
# Memory settings are provided by .env file, not hardcoded here

# Copy requirements and install Python dependencies globally as root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy and append custom prefixes to SemsQL
COPY semsql_custom_prefixes/custom_prefixes.csv /tmp/custom_prefixes.csv
RUN python3 -c "import semsql; print(semsql.__file__.replace('__init__.py', 'builder/prefixes/prefixes.csv'))" > /tmp/semsql_prefix_path.txt && \
    SEMSQL_PREFIX_PATH=$(cat /tmp/semsql_prefix_path.txt) && \
    tail -n +2 /tmp/custom_prefixes.csv >> "${SEMSQL_PREFIX_PATH}" && \
    echo "✅ Appended $(tail -n +2 /tmp/custom_prefixes.csv | wc -l) custom prefixes to SemsQL" && \
    rm /tmp/custom_prefixes.csv /tmp/semsql_prefix_path.txt

# Copy entrypoint script
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Copy the application code with proper ownership
COPY --chown=${USER_ID}:${GROUP_ID} . .

# Set working directory
WORKDIR /home/ontology/workspace

# Note: Output directories are created by host mount and script logic

# Use entrypoint for dynamic user handling
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "cdm_ontologies", "--help"]