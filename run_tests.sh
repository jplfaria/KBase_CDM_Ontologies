#!/bin/bash
# Run unit tests for CDM Ontologies Pipeline

echo "🧪 Running CDM Ontologies Unit Tests..."
echo "========================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest is not installed. Please run: pip install pytest pytest-cov pytest-mock"
    exit 1
fi

# Run tests with coverage
echo "Running unit tests with coverage..."
pytest tests/ -v --cov=scripts --cov=cdm_ontologies --cov-report=term-missing --cov-report=html

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in htmlcov/index.html"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi