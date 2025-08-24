#!/bin/bash

# Simple RAG Seeder
# Usage: ./seed_rag.sh [options]

CSV_FILE="rag-data.csv"
SEEDER_FLAGS=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --force) SEEDER_FLAGS="$SEEDER_FLAGS --force" ;;
        --help|-h) 
            echo "Usage: $0 [--force|--help]"
            echo "  --force      Add alongside existing data"
            exit 0 ;;
        *.csv) CSV_FILE="$arg" ;;
    esac
done

# Check CSV file
if [ ! -f "$CSV_FILE" ]; then
    echo "CSV file not found: $CSV_FILE"
    exit 1
fi

echo "Seeding RAG database with $CSV_FILE"
python rag_seeder.py --csv-file "$CSV_FILE" $SEEDER_FLAGS
