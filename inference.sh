#!/bin/bash

# Check if index exists, build if not
if [ ! -d "chroma_db" ]; then
    echo "Index not found. Building index..."
    python src/indexer.py
else
    echo "Index found. Skipping build."
fi


# Run prediction
echo "Starting prediction..."
python predict.py --input "$1" --output "$2"
