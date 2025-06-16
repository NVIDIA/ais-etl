#!/bin/bash

# Exit on error
set -e

AIS_ETL="$(cd "$(dirname "$0")/../"; pwd -P)"

# Function to check Python formatting
check_python_formatting() {
    echo "Checking Python formatting..."
    black --check --quiet --diff "${AIS_ETL}/transformers/"
}

# Function to fix Python formatting
python_black_fix() {
    echo "Fixing Python formatting..."
    black "${AIS_ETL}/transformers/" --quiet
}

# Main script
case "$1" in
    "fmt")
        case "$2" in
            "--fix")
                echo "Running style fixing..." >&2
                python_black_fix
                ;;
            *)
                echo "Running style check..." >&2
                check_python_formatting
                ;;
        esac
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac 