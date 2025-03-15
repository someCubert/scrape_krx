#!/bin/bash

# Download All Script for Foreign Ownership Data
# This script runs all the required download and processing steps

echo -e "\033[0;32mStarting data download process...\033[0m"

# Step 1: Download Foreign ownership by issue
echo -e "\033[0;36mStep 1/3: Downloading Foreign ownership by issue data...\033[0m"
DATA_DIR="./data"
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
fi
cd "$DATA_DIR"
python ../download_fobi.py
cd ..

# Step 2: Download ICBI data
echo -e "\033[0;36mStep 2/3: Downloading ICBI data...\033[0m"
python download_icbi.py

# Step 3: Process the downloaded data
echo -e "\033[0;36mStep 3/3: Processing downloaded data...\033[0m"
python readJSON.py

echo -e "\033[0;32mDownload and processing complete!\033[0m"
