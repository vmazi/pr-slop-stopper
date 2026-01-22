#!/usr/bin/env bash
set -euo pipefail

# Default to podman
RUNTIME="podman"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --runtime)
            RUNTIME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./build.sh [--runtime podman|docker]"
            echo ""
            echo "Build pr-slop-stopper container image after running quality checks."
            echo ""
            echo "Options:"
            echo "  --runtime    Container runtime to use (default: podman)"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

IMAGE_NAME="pr-slop-stopper"
IMAGE_TAG="latest"

echo "=== PR Slop Stopper Build ==="
echo "Runtime: $RUNTIME"
echo ""

# Step 1: Ensure dependencies are installed
echo ">>> Syncing dependencies..."
uv sync --extra dev
echo ""

# Step 2: Lint check
echo ">>> Running ruff lint check..."
uv run ruff check .
echo "✓ Lint check passed"
echo ""

# Step 3: Format check
echo ">>> Running ruff format check..."
uv run ruff format --check .
echo "✓ Format check passed"
echo ""

# Step 4: Type check
echo ">>> Running ty type check..."
uv run ty check src/
echo "✓ Type check passed"
echo ""

# Step 5: Run tests
echo ">>> Running tests..."
uv run pytest -v
echo "✓ Tests passed"
echo ""

echo ">>> All checks passed! Building container image..."
echo ""

# Step 6: Build container
$RUNTIME build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f Containerfile .

echo ""
echo "=== Build complete ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Run with: $RUNTIME run -p 8000:8000 ${IMAGE_NAME}:${IMAGE_TAG}"
