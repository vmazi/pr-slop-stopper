#!/bin/bash
# Development environment setup for PR Slop Stopper
#
# Usage: source devenv.sh
#
# This script:
# 1. Sets up uv if not already available
# 2. Creates/syncs the virtual environment
# 3. Activates the virtual environment
# 4. Sets helpful aliases

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up PR Slop Stopper development environment...${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found. Please install uv first:${NC}"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1 2>/dev/null || exit 1
fi

# Sync dependencies
echo -e "${GREEN}Syncing dependencies with uv...${NC}"
uv sync --dev

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${RED}Virtual environment not found at .venv/bin/activate${NC}"
    return 1 2>/dev/null || exit 1
fi

# Set up helpful aliases
alias test='uv run pytest -v'
alias lint='uv run ruff check .'
alias lintfix='uv run ruff check . --fix'
alias fmt='uv run ruff format .'
alias fmtcheck='uv run ruff format --check .'
alias typecheck='uv run ty check src/'
alias check='lint && fmtcheck && typecheck && test'
alias serve='uv run uvicorn pr_slop_stopper.main:app --reload --host 0.0.0.0 --port 8000'

echo ""
echo -e "${GREEN}Development environment ready!${NC}"
echo ""
echo "Available commands:"
echo "  test      - Run pytest with verbose output"
echo "  lint      - Run ruff linter"
echo "  lintfix   - Run ruff linter with auto-fix"
echo "  fmt       - Format code with ruff"
echo "  fmtcheck  - Check code formatting"
echo "  typecheck - Run type checker"
echo "  check     - Run all checks (lint, format, typecheck, test)"
echo "  serve     - Start development server with auto-reload"
echo ""
