# Quick test script for Docker Compose testing (Windows PowerShell)
#
# Usage:
#   .\run-tests.ps1                                      # run all tests (default)
#   .\run-tests.ps1 -ShowLogs                            # run all tests with full log output
#   .\run-tests.ps1 -TestFile tests/test_pidinst.py      # run a specific test file
#   .\run-tests.ps1 -TestFile tests/test_pidinst.py -ShowLogs  # specific file + logs
#
[CmdletBinding()]
param(
    # Show captured log output for every test function (adds -s --log-cli-level=DEBUG).
    [switch]$ShowLogs,

    # Run only the given test file (path relative to repo root, e.g. tests/test_pidinst.py).
    # Omit to run the full suite.
    [string]$TestFile
)

$ErrorActionPreference = "Stop"

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  DataCite 4.7 + PIDINST Extension Test Suite             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if docker-compose is available
try {
    docker-compose version | Out-Null
} catch {
    Write-Host "Error: docker-compose not found. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

# Build the image first
Write-Host "Building Docker image..." -ForegroundColor Cyan
docker-compose build latest
Write-Host ""

# ---------------------------------------------------------------------------
# Assemble the pytest command
# ---------------------------------------------------------------------------
if ($TestFile) {
    # Normalise separators for the Linux container path
    $containerPath = $TestFile -replace '\\', '/'
    $pytestArgs = "$containerPath --ckan-ini=/base/src/ckanext-doi/test.ini -v"
    $label = $TestFile
} else {
    # Default: let the image's built-in run-tests.sh handle the full suite
    $pytestArgs = $null
    $label = "All Unit Tests"
}

if ($ShowLogs) {
    $pytestArgs = "$pytestArgs -s --log-cli-level=DEBUG"
}

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
Write-Host "┌──────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
Write-Host "│  Running: $label" -ForegroundColor Yellow
if ($ShowLogs)  { Write-Host "│  Logs:    enabled (--log-cli-level=DEBUG)" -ForegroundColor Yellow }
if ($TestFile)  { Write-Host "│  File:    $TestFile" -ForegroundColor Yellow }
Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow

if ($pytestArgs) {
    docker-compose run --rm latest pytest $pytestArgs.Split(' ')
} else {
    docker-compose run --rm latest
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✓ $label passed" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ $label failed" -ForegroundColor Red
    exit 1
}
Write-Host ""
