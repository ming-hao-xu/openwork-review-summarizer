# Contributing to OpenWork Review Summarizer

Thank you for considering contributing to **OpenWork Review Summarizer**! This guide outlines the key steps to set up your environment, follow our coding standards, and submit changes.

## Development Setup

1. Set up a virtual environment (optional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # For Linux/Mac
   .\venv\Scripts\activate   # For Windows
   ```

2. Install dependencies:  
   Production:
   ```bash
   pip install -r requirements.txt
   ```
   Development:
   ```bash
   pip install -r dev/dev-requirements.txt
   ```

3. Install pre-commit hooks
   ```bash
   pre-commit install
   ```

## Coding Standards

- FormattingUse `black` and `isort` to maintain code consistency:
  ```bash
  black .
  isort .
  ```

- LintingEnsure code passes all `flake8` checks:
  ```bash
  flake8 .
  ```

- Commit Messages: Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard:
  ```
  <type>[optional scope]: <description>

  [optional body]

  [optional footer(s)]
  ```
  Examples:
  - `feat: add support for summarizing reviews in markdown format`
  - `fix: resolve issue with OpenAI API authentication`
  - `docs: update README with usage examples`

  Common types:
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation changes
  - `style`: Code style updates (non-functional)
  - `refactor`: Code restructuring (no feature or bug changes)
  - `test`: Adding or updating tests
  - `chore`: Miscellaneous tasks (e.g., dependency updates)

## Submitting Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Open a Pull Request (PR) and include:
   - A summary of your changes.
   - Any issues this PR addresses (e.g., "Fixes #123").

## Pull Request Checklist

Before submitting your PR, ensure:
- [ ] Code is formatted with `black` and `isort`.
- [ ] Code passes `flake8` checks.
- [ ] Pre-commit hooks are installed and run successfully.
