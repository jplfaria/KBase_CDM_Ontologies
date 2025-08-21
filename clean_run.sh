#!/bin/bash
# Clean up all outputs from a previous run to start fresh

echo "🧹 Cleaning up previous run data..."

# Remove downloaded ontologies
echo "  Removing ontology data..."
rm -rf ontology_data_owl/*
rm -rf ontology_data_owl_test/*

# Remove outputs
echo "  Removing outputs..."
rm -rf outputs/*
rm -rf outputs_test/*

# Remove version tracking
echo "  Removing version tracking..."
rm -rf ontology_versions/*
rm -rf ontology_versions_test/*

# Remove logs
echo "  Removing logs..."
rm -rf logs/*

# Remove cache
echo "  Removing cache..."
rm -rf .cache/*

echo "✅ Cleanup complete! Ready for a fresh run."