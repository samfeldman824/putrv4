# Test Suite Documentation

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── factories.py             # Test data factories
├── unit/                    # Unit tests (isolated, fast)
│   ├── test_models.py
│   ├── test_dao.py
│   ├── test_services.py
│   └── test_api_endpoints.py
├── integration/             # Integration tests (real components)
│   └── test_api_integration.py
├── performance/             # Performance benchmarks
│   └── test_import_performance.py
└── edge_cases/              # Edge case and error scenarios
    └── test_import_edge_cases.py
```

## Running Tests

### All Tests
```bash
uv run pytest
```

### Unit Tests Only
```bash
uv run pytest tests/unit/
```

### Integration Tests Only
```bash
uv run pytest tests/integration/
```

### Performance Tests (marked as slow)
```bash
uv run pytest -m performance
```

### Coverage Report
```bash
uv run pytest --cov=src --cov-report=html
```

## Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.edge_case`: Edge case tests

## Fixtures

### Database Fixtures
- `session`: In-memory SQLite database session
- `isolated_test_db`: Completely isolated test database
- `test_engine`: SQLAlchemy test engine

### Data Fixtures
- `sample_player`: Single test player
- `sample_players_batch`: Multiple test players
- `sample_game`: Single test game
- `sample_games`: Chronological game sequence

### Performance Fixtures
- `performance_timer`: Context manager for timing operations

## Writing New Tests

### Unit Tests
- Use `@patch` for external dependencies
- Focus on single function/class behavior
- Keep tests fast and isolated

### Integration Tests
- Test component interactions
- Use real database (SQLite in-memory)
- Focus on API contract validation

### Performance Tests
- Use `@pytest.mark.performance` and `@pytest.mark.slow`
- Include timing assertions
- Test with realistic data sizes

## Best Practices

1. **Descriptive Names**: Test methods should clearly describe what they test
2. **AAA Pattern**: Arrange, Act, Assert
3. **One Assertion Per Test**: When possible
4. **Test Data Factories**: Use factories instead of hardcoded data
5. **Mock External Dependencies**: Database, filesystem, network calls
6. **Cleanup**: Ensure proper cleanup in fixtures
7. **Documentation**: Add docstrings for complex test scenarios

## Coverage Requirements

- Minimum 80% line coverage required
- All new features must include tests
- Critical paths require near 100% coverage
