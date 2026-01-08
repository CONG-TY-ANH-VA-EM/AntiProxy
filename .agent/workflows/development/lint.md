---
description: how to run code quality checks
---

# Code Quality & Linting Workflow

## Frontend Linting (TypeScript/JavaScript)

### Run ESLint
// turbo
1. Check for issues: `npm run lint`
2. Auto-fix issues: `npm run lint -- --fix`
3. Check specific file: `npx eslint src/path/to/file.ts`

### TypeScript Type Checking
// turbo
1. Run type check: `npx tsc --noEmit`
2. Check specific file: `npx tsc --noEmit src/path/to/file.ts`

## Backend Linting (Python)

### Code Formatting (if configured)
1. Check formatting with black: `black --check src/`
2. Format code: `black src/`

### Linting with flake8/pylint (if configured)
1. Run flake8: `flake8 src/`
2. Run pylint: `pylint src/`

## Pre-commit Checks
// turbo-all
1. Run all linters: `npm run lint && pytest`
2. Format all code
3. Run type checks
4. Run tests

## Fix Common Issues

### Import Errors
1. Check for missing dependencies: `npm install`
2. Verify import paths are correct
3. Check `tsconfig.json` path aliases

### Type Errors
1. Add proper type annotations
2. Check for `any` types that should be specific
3. Ensure all dependencies have type definitions

### Zod Import Issues (v4 migration)
1. Update from `zod` to `zod/v4`: Change imports from `import { z } from 'zod'` to `import { z } from 'zod/v4'`
2. Run lint again to verify

## Notes
- Linting configuration in `eslint.config.mjs`
- TypeScript config in `tsconfig.json`
- Fix linting issues before committing
- Some issues can be auto-fixed with `--fix` flag
