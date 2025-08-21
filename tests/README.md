# CDM Ontologies Pipeline Tests

This directory contains the unit and integration tests for the CDM Ontologies Pipeline.

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures and test configuration
├── core/                # Core functionality tests
│   ├── test_analyze_core_ontologies.py
│   ├── test_merge_ontologies.py
│   ├── test_create_semantic_sql_db.py
│   └── test_cli.py
├── utils/               # Utility module tests
│   ├── test_enhanced_download.py
│   └── test_version_tracker.py
├── tools/               # Tool tests
│   ├── test_memory_monitor.py
│   └── test_resource_check.py
├── integration/         # Integration tests
│   └── test_workflow.py
└── fixtures/            # Test data and fixtures
    └── ontologies/      # Mini test ontologies
        ├── mini_go.owl
        └── mini_chebi.owl
```

## Running Tests

### Quick Start
```bash
# Run all tests
./run_tests.sh

# Or directly with pytest
pytest tests/ -v
```

### Running Specific Tests
```bash
# Run tests for a specific module
pytest tests/core/test_analyze_core_ontologies.py -v

# Run tests matching a pattern
pytest tests/ -k "test_download" -v

# Run with coverage report
pytest tests/ --cov=scripts --cov=cdm_ontologies --cov-report=html --cov-report=term-missing
```

### Test Coverage
- Coverage reports are generated in `htmlcov/` directory
- Open `htmlcov/index.html` in a browser to view detailed coverage
- Current coverage: ~45% (71 tests passing)

## Writing Tests

### Test Conventions
1. Test files should be named `test_*.py`
2. Test classes should be named `Test*`
3. Test functions should be named `test_*`
4. Use descriptive test names that explain what is being tested

### Common Fixtures
See `conftest.py` for shared fixtures:
- `temp_repo`: Creates a temporary repository structure
- `sample_ontology_source_file`: Creates a test ontology source file
- `mini_owl_file`: Provides minimal OWL file content
- `mock_environment`: Sets up test environment variables
- `mock_robot_command`: Mocks ROBOT tool execution

### Example Test
```python
def test_analyze_ontology_basic(temp_repo, mini_owl_file):
    """Test basic ontology analysis."""
    # Create test file
    owl_file = temp_repo / "test.owl"
    owl_file.write_text(mini_owl_file)
    
    # Run analysis
    result = analyze_ontology(str(owl_file))
    
    # Assert expected results
    assert result is not None
    assert result['file'] == 'test.owl'
```

## Continuous Integration
Tests are automatically run on GitHub Actions for:
- Every push to main/dev branches
- Every pull request
- Can be manually triggered

See `.github/workflows/ci.yml` for CI configuration.