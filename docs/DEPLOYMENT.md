# Production Deployment Guide

This guide covers deploying the CDM Ontologies Pipeline in production environments, from single servers to Kubernetes clusters.

## Deployment Options

### 1. Docker Compose (Recommended for Single Server)
### 2. Kubernetes (Recommended for HPC/Cloud)
### 3. Native Installation (Development Only)

## Docker Compose Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- Sufficient RAM based on dataset size:
  - Test: 1.5TB allocated (same as production)
  - Production: 1.5TB+ allocated to container

### Quick Deployment

```bash
# Clone repository
git clone <repository-url>
cd KBase_CDM_Ontologies

# Build container
make docker-build

# Deploy with appropriate configuration
make docker-run-prod  # For production datasets

# Or run in background
make docker-run-prod-nohup
```

### Custom Configuration

Create a custom environment file:

```bash
# Copy and modify configuration
cp .env .env.production

# Edit for your environment
nano .env.production
```

Key production settings:

```bash
# Memory Configuration (1.5TB unified settings)
ROBOT_JAVA_ARGS=-Xmx1500g -XX:MaxMetaspaceSize=8g -XX:+UseG1GC
RELATION_GRAPH_JAVA_ARGS=-Xmx1500g -XX:MaxMetaspaceSize=8g -XX:+UseG1GC
SEMSQL_MEMORY_LIMIT=1500g
PYTHON_MEMORY_LIMIT=1500g

# Dataset Configuration
ONTOLOGIES_SOURCE_FILE=config/ontologies_source.txt
DATASET_SIZE=production

# Performance Tuning
PARALLEL_DOWNLOADS=20
BATCH_SIZE=200
MAX_ONTOLOGY_SIZE_MB=5000

# Logging
LOG_LEVEL=INFO
ENABLE_DETAILED_LOGGING=true
```

Deploy with custom configuration:

```bash
ENV_FILE=.env.production docker-compose up -d
```

### Volume Management

Ensure persistent storage for important data:

```yaml
# docker-compose.yml volumes section
volumes:
  - ./ontology_data_owl:/workspace/ontology_data_owl
  - ./outputs:/workspace/outputs
  - ./logs:/workspace/logs
  - ./ontology_versions:/workspace/ontology_versions
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.20+
- kubectl configured
- Sufficient cluster resources
- Persistent storage provisioner

### Resource Requirements

| Dataset | CPU | Memory | Storage |
|---------|-----|--------|---------|
| Test | 2 cores | 8GB | 10GB |
| Small | 4 cores | 32GB | 50GB |
| Large | 8+ cores | 1TB+ | 500GB+ |

### Deployment Steps

1. **Create Namespace**

```bash
kubectl apply -f k8s/namespace.yaml
```

2. **Configure Resources**

Edit `k8s/configmap.yaml` for your environment:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cdm-ontologies-config
  namespace: cdm-ontologies
data:
  ROBOT_JAVA_ARGS: "-Xmx800g"
  _JAVA_OPTIONS: "-Xmx800g"
  DATASET_SIZE: "large"
  PARALLEL_DOWNLOADS: "20"
```

3. **Create Persistent Storage**

```bash
kubectl apply -f k8s/pvc.yaml
```

4. **Deploy Job**

```bash
kubectl apply -f k8s/job.yaml
```

5. **Monitor Progress**

```bash
# Watch job status
kubectl get jobs -n cdm-ontologies -w

# View logs
kubectl logs -f job/cdm-ontologies-pipeline -n cdm-ontologies

# Check pod status
kubectl get pods -n cdm-ontologies
```

### Kubernetes Configuration Examples

#### High-Memory Job (1TB+ RAM)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cdm-ontologies-pipeline-large
  namespace: cdm-ontologies
spec:
  template:
    spec:
      containers:
      - name: pipeline
        image: cdm-ontologies:latest
        resources:
          requests:
            memory: "1000Gi"
            cpu: "8"
          limits:
            memory: "1200Gi"
            cpu: "16"
        env:
        - name: ROBOT_JAVA_ARGS
          value: "-Xmx900g"
        - name: DATASET_SIZE
          value: "large"
```

#### Multi-Step Pipeline Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cdm-ontologies-step1
spec:
  template:
    spec:
      containers:
      - name: analyze-core
        image: cdm-ontologies:latest
        command: ["python", "-m", "cdm_ontologies", "analyze-core"]
        resources:
          requests:
            memory: "100Gi"
            cpu: "4"
```

## Native Installation

**Note**: Native installation is recommended only for development. Production deployments should use Docker.

### System Requirements

- Ubuntu 20.04+ or CentOS 8+
- Python 3.10+
- Java 17+
- 32GB+ RAM minimum

### Installation Steps

1. **Install System Dependencies**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip openjdk-17-jdk make curl wget

# CentOS/RHEL
sudo dnf install -y python3.10 python3-pip java-17-openjdk make curl wget
```

2. **Install ROBOT**

```bash
# Download and install ROBOT
cd /opt
sudo wget https://github.com/ontodev/robot/releases/download/v1.9.0/robot.jar
sudo chmod +x robot.jar

# Create wrapper script
sudo tee /usr/local/bin/robot > /dev/null <<EOF
#!/bin/bash
java -jar /opt/robot.jar "\$@"
EOF
sudo chmod +x /usr/local/bin/robot
```

3. **Install relation-graph**

```bash
# Download and install relation-graph
cd /opt
sudo wget https://github.com/balhoff/relation-graph/releases/download/v2.3.1/relation-graph-2.3.1.tgz
sudo tar -xzf relation-graph-2.3.1.tgz
sudo ln -s /opt/relation-graph-2.3.1/bin/relation-graph /usr/local/bin/
```

4. **Setup Python Environment**

```bash
# Clone repository
git clone <repository-url>
cd KBase_CDM_Ontologies

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
make install
```

5. **Configure Environment**

```bash
# Set memory limits
export ROBOT_JAVA_ARGS="-Xmx32g"
export _JAVA_OPTIONS="-Xmx32g"

# Add to shell profile
echo 'export ROBOT_JAVA_ARGS="-Xmx32g"' >> ~/.bashrc
echo 'export _JAVA_OPTIONS="-Xmx32g"' >> ~/.bashrc
```

## Production Considerations

### Resource Planning

#### Memory Requirements

- **Test dataset**: 8GB minimum, 16GB recommended
- **Small dataset**: 32GB minimum, 64GB recommended  
- **Full dataset**: 1TB minimum, 1.5TB recommended

#### Storage Requirements

- **Input data**: 50GB for full ontology set
- **Processing temp**: 200GB during pipeline execution
- **Output data**: 100GB for databases and exports
- **Logs and versions**: 10GB for tracking data

#### CPU Requirements

- **Minimum**: 4 cores
- **Recommended**: 8+ cores
- **Parallel downloads**: Scale with available bandwidth

### Performance Optimization

#### Java Heap Tuning

```bash
# Conservative (safe for most systems)
export ROBOT_JAVA_ARGS="-Xmx32g -XX:+UseG1GC"

# Aggressive (for high-memory systems)
export ROBOT_JAVA_ARGS="-Xmx800g -XX:+UseG1GC -XX:+UseStringDeduplication"
```

#### Parallel Processing

```bash
# Increase concurrent downloads
export PARALLEL_DOWNLOADS=20

# Increase batch processing
export BATCH_SIZE=200
```

#### Disk I/O Optimization

```bash
# Use SSD storage for temporary files
export TEMP_DIR=/fast/ssd/tmp

# Separate input/output directories across disks
export INPUT_DIR=/disk1/ontology_data
export OUTPUT_DIR=/disk2/outputs
```

### Monitoring and Logging

#### Log Management

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/cdm-ontologies > /dev/null <<EOF
/path/to/KBase_CDM_Ontologies/logs/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

#### Resource Monitoring

```bash
# Monitor memory usage during pipeline
watch -n 10 'free -h && ps aux | grep -E "(robot|python)" | head -10'

# Monitor disk usage
watch -n 30 'df -h'

# Monitor Java heap usage
jstat -gc -t $(pgrep java) 10s
```

### Security Considerations

#### Container Security

```dockerfile
# Run as non-root user
USER ontology:ontology

# Drop unnecessary capabilities
--cap-drop=ALL

# Read-only root filesystem where possible
--read-only --tmpfs /tmp
```

#### Network Security

```bash
# Restrict outbound connections to necessary ontology sources
# Configure firewall rules for ontology source URLs
```

#### Data Security

```bash
# Secure sensitive configuration
chmod 600 .env.production

# Use secrets management for production
kubectl create secret generic cdm-ontologies-config \
  --from-env-file=.env.production
```

### Backup and Recovery

#### Version Tracking Backup

```bash
# Backup version registry
cp ontology_versions/ontology_versions.json /backup/location/

# Backup complete version directory
tar -czf ontology_versions_backup_$(date +%Y%m%d).tar.gz ontology_versions/
```

#### Output Backup

```bash
# Backup critical outputs
rsync -av outputs/ /backup/location/outputs/

# Backup databases separately
cp outputs/*.db /backup/databases/
```

### Maintenance

#### Regular Updates

```bash
# Check for ontology updates
python scripts/version_manager.py status

# Update only changed ontologies
make analyze-core

# Full pipeline if updates detected
if python scripts/version_manager.py check-updates; then
    make run-workflow
fi
```

#### Cleanup Tasks

```bash
# Clean old version backups (keep 30 days)
python scripts/version_manager.py clean --days 30

# Clean temporary files
make clean

# Archive old logs
find logs/ -name "*.log" -mtime +30 -exec gzip {} \;
```

### Troubleshooting Production Issues

#### Out of Memory

```bash
# Check current memory usage
cat /proc/meminfo

# Adjust Java heap size
export ROBOT_JAVA_ARGS="-Xmx$(( $(free -g | awk 'NR==2{print $2}') * 80 / 100 ))g"

# Use smaller dataset for testing
ENV_FILE=.env.small make run-workflow
```

#### Network Issues

```bash
# Check download history for failures
python scripts/version_manager.py history | grep FAILED

# Test connectivity to ontology sources
curl -I http://purl.obolibrary.org/obo/bfo.owl

# Increase retry attempts
export MAX_RETRIES=5
export TIMEOUT_SECONDS=60
```

#### Storage Issues

```bash
# Check disk space
df -h

# Clean temporary files
make clean-all

# Move large files to different disk
mv outputs/ /larger/disk/outputs/
ln -s /larger/disk/outputs outputs
```

This deployment guide provides comprehensive instructions for running the CDM Ontologies Pipeline in production environments. Choose the deployment method that best fits your infrastructure and scale requirements.