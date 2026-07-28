# Contributing to DocMeld

Thank you for your interest in contributing to DocMeld! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git

### Setup Steps

1. **Fork and clone the repository**

```bash
git clone https://github.com/agentii-ai/DocMeld.git
cd DocMeld/docmeld
```

2. **Create a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode**

```bash
pip install -e ".[dev]"
```

4. **Verify installation**

```bash
pytest tests/
```

## Development Workflow

### Test-Driven Development (TDD)

DocMeld follows strict TDD practices per the project constitution:

1. **Write tests first** - Tests must be written before implementation
2. **Ensure tests fail** - Verify tests fail (red)
3. **Implement minimum code** - Write just enough code to pass tests (green)
4. **Refactor** - Clean up while keeping tests green

### Code Style

We use automated tools to maintain code quality:

- **Formatting**: `black` (line length 100)
- **Linting**: `ruff`
- **Type checking**: `mypy` (strict mode)

Run all checks before committing:

```bash
# Format code
black docmeld/

# Check linting
ruff check docmeld/

# Type check
mypy docmeld/

# Run tests
pytest --cov=docmeld --cov-report=term-missing
```

### Commit Messages

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

**Example:**
```
feat(bronze): add support for encrypted PDFs

Implements password-protected PDF parsing using PyMuPDF's
encryption handling. Adds new parameter to BronzeProcessor.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes following TDD**

- Write tests first
- Implement feature
- Ensure all tests pass
- Run linting and type checking

3. **Update documentation**

- Update README.md if adding user-facing features
- Add docstrings to new functions/classes
- Update CHANGELOG.md

4. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

- Open a pull request on GitHub
- Fill out the PR template
- Link related issues

5. **Code review**

- Address reviewer feedback
- Keep commits clean and focused
- Squash commits if requested

## Testing Guidelines

### Test Organization

- **Unit tests**: `tests/unit/` - Test individual functions/classes
- **Integration tests**: `tests/integration/` - Test component interactions
- **Contract tests**: `tests/contract/` - Validate JSON schemas and APIs

### Writing Tests

```python
"""Unit tests for new feature."""
from docmeld.module import NewFeature


class TestNewFeature:
    def test_basic_functionality(self) -> None:
        """Test that basic feature works."""
        feature = NewFeature()
        result = feature.process("input")
        assert result == "expected"

    def test_edge_case(self) -> None:
        """Test edge case handling."""
        feature = NewFeature()
        with pytest.raises(ValueError):
            feature.process("")
```

### Coverage Requirements

- Minimum 90% overall coverage
- 100% coverage for core parser logic
- All new features must include tests

## Issue Reporting

### Bug Reports

Include:
- DocMeld version (`pip show docmeld`)
- Python version
- Operating system
- Minimal reproducible example
- Expected vs actual behavior
- Error messages and stack traces

### Feature Requests

Include:
- Use case description
- Proposed API/interface
- Why existing features don't solve the problem
- Willingness to implement (if applicable)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Unprofessional conduct

## Questions?

- Open a GitHub Discussion for general questions
- Join our community chat (link TBD)
- Email maintainers for private concerns

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
