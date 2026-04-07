# Quick test script for Docker Compose testing (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  DataCite 4.7 + PIDINST Extension Test Suite             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function Run-Test {
    param(
        [string]$Name,
        [string]$Command
    )
    
    Write-Host "┌──────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
    Write-Host "│  Running: $Name" -ForegroundColor Yellow
    Write-Host "└──────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
    
    Invoke-Expression $Command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $Name passed" -ForegroundColor Green
    } else {
        Write-Host "✗ $Name failed" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

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

# Run test suites
Run-Test "All Unit Tests" "docker-compose run --rm latest"

# Optional: Run specific test suites individually for debugging
# Run-Test "PIDINST Tests" "docker-compose run --rm latest pytest tests/test_pidinst.py --ckan-ini=/base/src/ckanext-doi/test.ini -v"
# Run-Test "Legacy Tests" "docker-compose run --rm latest pytest tests/test_generate.py --ckan-ini=/base/src/ckanext-doi/test.ini -v"

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✓ All tests passed successfully!                       ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  • Review test output above"
Write-Host "  • Check coverage report"
Write-Host "  • Test with your PIDINST schema data"
Write-Host ""
