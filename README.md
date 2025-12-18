# VNPT AI - Age of AInicorns (Track 2: The Builder)
**Team: The Builder**

## 1. Overview
This project implements an Agentic RAG (Retrieval-Augmented Generation) pipeline designed for the VNPT AI Hackathon (Track 2). It specializes in answering Vietnamese multiple-choice questions across various domains (Law, History, STEM, etc.) by leveraging a vector database constructed from diverse data sources.

## 2. Key Features
*   **Robust Data Indexing**: The `src/indexer.py` module is improved to support ingesting diverse file formats (both `.json` and `.jsonl`) from the `data/` directory. It includes intelligent rate limiting (adapting to 450 RPM) and quota tracking to ensure safe API usage.
*   **Vector Database**: Utilizes ChromaDB for efficient dense retrieval. The system is upgraded to use deterministic content hashing (MD5) for IDs, enabling idempotent indexing (upserts) and preventing duplicates.
*   **Context Retrieval**: `src/retriever.py` fetches the most relevant document chunks to augment LLM prompts, improving accuracy on domain-specific questions.
*   **Submission Ready**: Fully compatible with contest requirements, including a dedicated `Dockerfile` and `inference.sh` for seamless evaluation.

## 3. Setup & Installation

### Requirements
*   Python 3.10+
*   16GB+ RAM (Recommended for local vector store operations)
*   Docker (for submission verification)

### Installation
1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd VNPT
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **API Configuration**:
    *   Navigate to `api_keys/`.
    *   Ensure `api-keys.json` is present and contains your valid VNPT AI `access_token` and `token_key`.

## 4. Usage Guide

### Step 1: Build the Knowledge Base (Indexing)
Before running inference, you must index your data. The indexer will scan the `data/` folder for all supported files.
```bash
python src/indexer.py
```
*   **Note**: This process may take time depending on the volume of data. The script will automatically pause if API rate limits are approached.
*   **Artifact**: Creates/Updates the `chroma_db` directory (Vector Store).

### Step 2: Run Inference
Generate predictions for the test set.
```bash
python predict.py
```
*   **Input**: Reads questions from `public_test/test.json` (default configuration).
*   **Output**: Generates `submission.csv` containing question IDs and predicted answers.

## 5. Docker Submission
Follow these steps to package your solution for the contest system:

1.  **Build Docker Image**:
    ```bash
    docker build -t vnpt-submission .
    ```

2.  **Test Container Locally**:
    ```bash
    # Mount your data directory to test with local data
    docker run --gpus all -v $(pwd)/public_test:/app/public_test vnpt-submission
    ```

## 6. Project Structure
*   `data/`: Contains raw knowledge files (e.g., `law.jsonl`, `vietnam.jsonl`, `computer_science.jsonl`).
*   `src/`: Core logic modules:
    *   `indexer.py`: Handles data ingestion and embedding.
    *   `vector_store.py`: ChromaDB wrapper with upsert logic.
    *   `retriever.py`: Logic for querying the vector DB.
*   `scripts/`: Utility scripts for coverage analysis and model evaluation.
*   `predict.py`: Main entry point for generating results.
*   `Dockerfile` & `inference.sh`: Configuration for the submission environment.

