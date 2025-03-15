# Download All Script for Foreign Ownership Data
# This script runs all the required download and processing steps

Write-Host "Starting data download process..." -ForegroundColor Green

# Step 1: Download Foreign ownership by issue
Write-Host "Step 1/3: Downloading Foreign ownership by issue data..." -ForegroundColor Cyan
$dataDir = Join-Path $PSScriptRoot "data"
if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force
}
Set-Location $dataDir
python ../download_fobi.py
Set-Location $PSScriptRoot

# Step 2: Download ICBI data
Write-Host "Step 2/3: Downloading ICBI data..." -ForegroundColor Cyan
python download_icbi.py

# Step 3: Process the downloaded data
Write-Host "Step 3/3: Processing downloaded data..." -ForegroundColor Cyan
python readJSON.py

Write-Host "Download and processing complete!" -ForegroundColor Green
