#!/bin/bash
# build-layer.sh
# Builds Lambda Layer with Python dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build/layer"
OUTPUT_DIR="$PROJECT_ROOT/build/output"

echo "🏗️  Building Lambda Layer..."
echo "Project root: $PROJECT_ROOT"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p "$BUILD_DIR/python"
mkdir -p "$OUTPUT_DIR"

# Install dependencies
echo "📦 Installing dependencies from requirements-lambda.txt..."
pip install -r "$PROJECT_ROOT/requirements-lambda.txt" -t "$BUILD_DIR/python" --upgrade

# Remove unnecessary files to reduce size
echo "🗑️  Removing unnecessary files..."
cd "$BUILD_DIR/python"
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "📦 Creating layer.zip..."
cd "$BUILD_DIR"
zip -r9 "$OUTPUT_DIR/layer.zip" python -x "*.pyc" "*.pyo"

# Report size
LAYER_SIZE=$(du -h "$OUTPUT_DIR/layer.zip" | cut -f1)
echo "✅ Lambda Layer built successfully!"
echo "📊 Size: $LAYER_SIZE"
echo "📁 Location: $OUTPUT_DIR/layer.zip"

# Check if size exceeds Lambda limits
LAYER_SIZE_BYTES=$(wc -c < "$OUTPUT_DIR/layer.zip")
MAX_SIZE=$((50 * 1024 * 1024))  # 50 MB unzipped limit

if [ $LAYER_SIZE_BYTES -gt $MAX_SIZE ]; then
    echo "⚠️  Warning: Layer might be too large. Consider using Container Image deployment instead."
fi
