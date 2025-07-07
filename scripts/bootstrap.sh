#!/bin/bash

# Exit on error
set -e

AIS_ETL="$(cd "$(dirname "$0")/../"; pwd -P)"

# Function to check Python formatting
check_python_formatting() {
    err_count=0
    pylint_failed=false
    black_failed=false

    # Check python code (excluding test directories)
    echo "Running pylint..."
    for f in $(find "${AIS_ETL}/transformers/" -type f -name "*.py" ! -regex ".*__pycache__.*" ! -path "*/tests/*" | sort); do
        pylint --score=n "$f" 2>/dev/null || pylint_failed=true
        if [ "$pylint_failed" = true ]; then 
            err_count=$((err_count + 1))
            pylint_failed=false
        fi
    done

    echo "Running black formatting check on all files..."
    black --check --diff --quiet "${AIS_ETL}/transformers/" || black_failed=true
    if [ "$black_failed" = true ]; then
        printf "\nIncorrect Python formatting. Run 'make fmt-fix' to fix it.\n\n" >&2
        err_count=$((err_count + 1))
    fi

    if [ $err_count -ne 0 ]; then
        printf "\npylint failed, fix before continuing\n"
        exit 1
    fi
}

# Function to fix Python formatting
python_black_fix() {
    echo "Fixing Python formatting..."
    black "${AIS_ETL}/transformers/" --quiet
    if [ $? -eq 0 ]; then
        echo "✅ Python formatting fixed successfully"
    else
        echo "❌ Failed to fix Python formatting"
        exit 1
    fi
}

# Main script (like aistore)
case $1 in
fmt)
  case $2 in
  --fix)
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
  echo "unsupported argument $1"
  exit 1
  ;;
esac 