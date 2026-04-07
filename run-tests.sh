#!/bin/bash
# Quick test script for Docker Compose testing

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  DataCite 4.7 + PIDINST Extension Test Suite           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Function to run tests with nice output
run_test() {
    local name=$1
    local command=$2
    
    echo "┌──────────────────────────────────────────────────────────┐"
    echo "│  Running: $name"
    echo "└──────────────────────────────────────────────────────────┘"
    eval $command
    if [ $? -eq 0 ]; then
        echo "✓ $name passed"
    else
        echo "✗ $name failed"
        exit 1
    fi
    echo ""
}

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Build the image first
echo "Building Docker image..."
docker-compose build latest
echo ""

# Run test suites
run_test "All Unit Tests" "docker-compose run --rm latest"
run_test "PIDINST Tests" "docker-compose run --rm latest pytest tests/test_pidinst.py -v"
run_test "Legacy Tests" "docker-compose run --rm latest pytest tests/test_generate.py -v"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ All tests passed successfully!                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  • Review test output above"
echo "  • Check coverage report"
echo "  • Test with your PIDINST schema data"
echo ""
