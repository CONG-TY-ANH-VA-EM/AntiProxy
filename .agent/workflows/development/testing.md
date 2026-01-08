---
description: how to run tests
---

# Testing Workflow

## Frontend Tests
// turbo
1. Run Next.js/React tests: `npm test`
2. Run tests in watch mode: `npm test -- --watch`

## Backend Tests
1. Ensure you're in the project root
// turbo
2. Run Python tests: `pytest`
3. Run with coverage: `pytest --cov=src`
4. Run specific test file: `pytest tests/test_agent.py`

## Linting (See also: lint.md)
// turbo
1. Check TypeScript/JavaScript: `npm run lint`
2. Fix auto-fixable issues: `npm run lint -- --fix`

## Integration Tests
1. Ensure Docker services are running: `docker-compose up -d`
2. Run integration tests: `pytest tests/integration/`

## Notes
- Make sure environment variables are set correctly
- Backend tests may require Redis to be running
- Check `package.json` and `pytest.ini` for test configuration
