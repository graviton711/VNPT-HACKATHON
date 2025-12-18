#!/bin/bash

# Run prediction
# Check if index exists, if not build it
if [ ! -d "chroma_db" ]; then
    echo "Index not found. Building index..."
    python src/indexer.py
else
    echo "Index found. Skipping build."
fi

# Run prediction
python predict.py
