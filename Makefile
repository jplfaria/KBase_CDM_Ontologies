# Makefile for CDM Ontologies Workflow

# Set shell to bash for consistent behavior
SHELL := /bin/bash

# Auto-export UID/GID for Docker - no manual setup needed
export UID := $(shell id -u)
export GID := $(shell id -g)

# Configuration
PYTHON := python3
REPO_PATH := $(shell pwd)
SCRIPTS_DIR := $(REPO_PATH)/scripts

# Load environment variables from .env file if specified
ifneq ($(ENV_FILE),)
	include $(ENV_FILE)
	export
endif

# Default target
.PHONY: all
all: run-workflow

# Create necessary directories (test-mode aware)
.PHONY: setup
setup:
	@echo "Setting up directories..."
	@if echo "$(ONTOLOGIES_SOURCE_FILE)" | grep -q "test"; then \
		echo "Creating test mode directories..."; \
		mkdir -p outputs_test outputs_test/tsv_tables ontology_data_owl_test/non-base-ontologies ontology_versions_test; \
	else \
		echo "Creating production mode directories..."; \
		mkdir -p outputs outputs/tsv_tables ontology_data_owl/non-base-ontologies ontology_versions; \
	fi
	@mkdir -p logs

# Install Python dependencies
.PHONY: install
install:
	@echo "Installing Python dependencies..."
	@$(PYTHON) -m pip install -r requirements.txt

# Run the complete workflow
.PHONY: run-workflow
run-workflow: setup
	@echo "Starting CDM Ontologies workflow..."
	@echo "Dataset size: $(DATASET_SIZE)"
	@echo "Java memory: $(ROBOT_JAVA_ARGS)"
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli run-all

# Run individual workflow steps
.PHONY: analyze-core
analyze-core: setup
	@echo "Analyzing core ontologies..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli analyze-core

.PHONY: analyze-non-core
analyze-non-core: setup
	@echo "Analyzing non-core ontologies..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli analyze-non-core

.PHONY: create-base
create-base: setup
	@echo "Creating pseudo-base ontologies..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-base

.PHONY: merge
merge: setup
	@echo "Merging ontologies..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli merge

.PHONY: create-db
create-db: setup
	@echo "Creating semantic SQL database..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-db

.PHONY: extract-tables
extract-tables: setup
	@echo "Extracting SQL tables to TSV..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli extract-tables

.PHONY: create-parquet
create-parquet: setup
	@echo "Creating Parquet files..."
	@PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-parquet

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning up output files..."
	@rm -rf outputs/*
	@rm -rf logs/*

# Clean everything including downloaded ontologies
.PHONY: clean-all
clean-all: clean
	@echo "Cleaning all data including downloaded ontologies..."
	@rm -rf ontology_data_owl/*.owl
	@rm -rf ontology_data_owl/non-base-ontologies/*.owl

# Test targets
.PHONY: test-analyze-core
test-analyze-core: setup
	@echo "Testing core ontology analysis with test dataset..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli analyze-core

.PHONY: test-analyze-non-core
test-analyze-non-core: setup
	@echo "Testing non-core ontology analysis..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli analyze-non-core

.PHONY: test-create-base
test-create-base: setup
	@echo "Testing pseudo-base ontology creation..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-base

.PHONY: test-merge
test-merge: setup
	@echo "Testing ontology merging..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli merge

.PHONY: test-create-db
test-create-db: setup
	@echo "Testing semantic SQL database creation..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-db

.PHONY: test-extract-tables
test-extract-tables: setup
	@echo "Testing SQL table extraction..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli extract-tables

.PHONY: test-create-parquet
test-create-parquet: setup
	@echo "Testing Parquet file creation..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli create-parquet

.PHONY: test-workflow
test-workflow: setup
	@echo "Testing complete workflow with test dataset..."
	@ONTOLOGIES_SOURCE_FILE=config/ontologies_source_test.txt PYTHONPATH=$(SCRIPTS_DIR):$(PYTHONPATH) $(PYTHON) -m cdm_ontologies.cli run-all

# Docker targets
.PHONY: docker-build
docker-build:
	@echo "Building Docker image with UID=$(UID) GID=$(GID)..."
	@docker build --build-arg USER_ID=$(UID) --build-arg GROUP_ID=$(GID) -t kbase-cdm-ontologies:latest .

.PHONY: docker-run-production
docker-run-production: docker-build
	@echo "Running pipeline with production dataset..."
	@ENV_FILE=.env UID=$(UID) GID=$(GID) docker compose run --rm cdm-ontologies
	@echo "Fixing any permission issues..."
	@docker run --rm -v "$(PWD):/workspace" --user root alpine:latest sh -c "chown -R $(UID):$(GID) /workspace/outputs /workspace/ontology_data_owl /workspace/logs 2>/dev/null || true"

.PHONY: docker-run-prod
docker-run-prod: docker-build
	@echo "Running pipeline with production dataset (30+ ontologies)..."
	@ENV_FILE=.env UID=$(UID) GID=$(GID) docker compose run --rm cdm-ontologies
	@echo "Fixing any permission issues..."
	@docker run --rm -v "$(PWD):/workspace" --user root alpine:latest sh -c "chown -R $(UID):$(GID) /workspace/outputs /workspace/ontology_data_owl /workspace/logs 2>/dev/null || true"

.PHONY: docker-run-prod-nohup
docker-run-prod-nohup: docker-build
	@echo "Starting production pipeline in background with nohup..."
	@mkdir -p logs
	@nohup bash -c 'ENV_FILE=.env UID=$(UID) GID=$(GID) docker compose run --rm cdm-ontologies && \
	docker run --rm -v "$(PWD):/workspace" --user root alpine:latest sh -c "chown -R $(UID):$(GID) /workspace/outputs /workspace/ontology_data_owl /workspace/logs 2>/dev/null || true"' \
	> logs/nohup_cdm_prod.out 2>&1 &
	@echo "Production pipeline started in background. PID: $$!"
	@echo "Monitor progress with: make docker-prod-status"
	@echo "Or check the log file: tail -f logs/nohup_cdm_prod.out"

.PHONY: docker-prod-status
docker-prod-status:
	@if [ -f logs/nohup_cdm_prod.out ]; then \
		tail -f logs/nohup_cdm_prod.out; \
	else \
		echo "No production run log found. Start with: make docker-run-prod-nohup"; \
	fi

.PHONY: docker-test
docker-test: docker-build
	@echo "Running pipeline with test dataset in Docker..."
	@ENV_FILE=.env.test UID=$(UID) GID=$(GID) docker compose run --rm cdm-ontologies make test-workflow
	@echo "Fixing any permission issues..."
	@docker run --rm -v "$(PWD):/workspace" --user root alpine:latest sh -c "chown -R $(UID):$(GID) /workspace/outputs_test /workspace/ontology_data_owl_test /workspace/logs 2>/dev/null || true"

.PHONY: docker-test-nohup
docker-test-nohup: docker-build
	@echo "Starting test pipeline in background with nohup..."
	@mkdir -p logs
	@nohup bash -c 'ENV_FILE=.env.test UID=$(UID) GID=$(GID) docker compose run --rm cdm-ontologies make test-workflow && \
	docker run --rm -v "$(PWD):/workspace" --user root alpine:latest sh -c "chown -R $(UID):$(GID) /workspace/outputs_test /workspace/ontology_data_owl_test /workspace/logs 2>/dev/null || true"' \
	> logs/nohup_cdm_test.out 2>&1 &
	@echo "Test pipeline started in background. PID: $$!"
	@echo "Monitor progress with: make docker-test-status"
	@echo "Or check the log file: tail -f logs/nohup_cdm_test.out"

.PHONY: docker-test-status
docker-test-status:
	@if [ -f logs/nohup_cdm_test.out ]; then \
		tail -f logs/nohup_cdm_test.out; \
	else \
		echo "No test run log found. Start with: make docker-test-nohup"; \
	fi

# Help target
.PHONY: help
help:
	@echo "CDM Ontologies Pipeline - Available targets:"
	@echo ""
	@echo "Workflow targets:"
	@echo "  make run-workflow    - Run the complete workflow"
	@echo "  make analyze-core    - Analyze core ontologies only"
	@echo "  make analyze-non-core - Analyze non-core ontologies only"
	@echo "  make create-base     - Create pseudo-base ontologies"
	@echo "  make merge           - Merge ontologies"
	@echo "  make create-db       - Create semantic SQL database"
	@echo "  make extract-tables  - Extract SQL tables to TSV"
	@echo "  make create-parquet  - Create Parquet files from database"
	@echo ""
	@echo "Test targets (use 6 test ontologies):"
	@echo "  make test-workflow   - Run complete workflow with test dataset"
	@echo "  make test-analyze-core - Test core ontology analysis"
	@echo "  make test-analyze-non-core - Test non-core ontology analysis"
	@echo "  make test-create-base - Test pseudo-base creation"
	@echo "  make test-merge      - Test ontology merging"
	@echo "  make test-create-db  - Test database creation"
	@echo "  make test-extract-tables - Test table extraction"
	@echo "  make test-create-parquet - Test Parquet file creation"
	@echo ""
	@echo "Utility targets:"
	@echo "  make setup           - Create necessary directories"
	@echo "  make install         - Install Python dependencies"
	@echo "  make clean           - Clean output files"
	@echo "  make clean-all       - Clean everything including downloads"
	@echo ""
	@echo "Docker targets:"
	@echo "  make docker-build       - Build Docker image"
	@echo "  make docker-run-production - Run with production dataset in Docker"
	@echo "  make docker-test        - Run with test dataset in Docker"
	@echo "  make docker-test-nohup  - Run test in background with nohup"
	@echo "  make docker-test-status - Monitor test run progress"
	@echo "  make docker-run-prod    - Run with production dataset (30+ ontologies)"
	@echo "  make docker-run-prod-nohup - Run production in background with nohup"
	@echo "  make docker-prod-status - Monitor production run progress"
	@echo ""
	@echo "Environment variables:"
	@echo "  ENV_FILE=.env      - Use production dataset configuration (default)"
	@echo "  ENV_FILE=.env.test - Use test dataset configuration"
