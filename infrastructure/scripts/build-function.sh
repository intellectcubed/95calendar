#!/bin/bash
# build-function.sh
# Builds Lambda function deployment package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build/function"
OUTPUT_DIR="$PROJECT_ROOT/build/output"

echo "🏗️  Building Lambda Function..."
echo "Project root: $PROJECT_ROOT"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Copy source code
echo "📋 Copying source code..."
cp -r "$PROJECT_ROOT/src" "$BUILD_DIR/"

# Copy credentials if exists (Google service account)
# Check both root and config/ directory
if [ -f "$PROJECT_ROOT/credentials.json" ]; then
    echo "🔑 Copying credentials.json from root..."
    cp "$PROJECT_ROOT/credentials.json" "$BUILD_DIR/"
elif [ -f "$PROJECT_ROOT/config/credentials.json" ]; then
    echo "🔑 Copying credentials.json from config/..."
    cp "$PROJECT_ROOT/config/credentials.json" "$BUILD_DIR/"
else
    echo "⚠️  Warning: credentials.json not found (will need to use Secrets Manager)"
fi

# Remove __pycache__ and .pyc files
echo "🗑️  Cleaning Python cache files..."
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete
find "$BUILD_DIR" -type f -name "*.pyo" -delete

# Create zip file
echo "📦 Creating function.zip..."
cd "$BUILD_DIR"
zip -r9 "$OUTPUT_DIR/function.zip" . -x "*.pyc" "*.pyo"

# Report size
FUNC_SIZE=$(du -h "$OUTPUT_DIR/function.zip" | cut -f1)
echo "✅ Lambda Function built successfully!"
echo "📊 Size: $FUNC_SIZE"
echo "📁 Location: $OUTPUT_DIR/function.zip"
