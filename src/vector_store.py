import os
import uuid
import hashlib

class VectorStore:
    def __init__(self, collection_name="vnpt_rag_collection", persist_directory="chroma_db"):
        """
        Initialize ChromaDB Persistent Client.
        Data will be stored in 'persist_directory'.
        """
        # Disable ChromaDB Telemetry to speed up init
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        # Lazy import to avoid startup lag if not used
        import chromadb
        
        # Ensure directory exists (Chroma handles this, but good practice)
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize Client
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Get or Create Collection
        # metadata={"hnsw:space": "cosine"} defines the distance metric
        # embedding_function=None: Disable default model loading (we provide embeddings manually)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, 
            metadata={"hnsw:space": "cosine"},
            embedding_function=None
        )
        print(f"[VectorStore] Initialized ChromaDB at '{self.persist_directory}' with collection '{self.collection_name}'.")

    def has_file(self, filename):
        """Check if any document in the collection has source_file=filename in metadata."""
        try:
            # We only need to check if ANY document exists
            results = self.collection.get(
                where={"source_file": filename},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception:
            return False

    def add_batch(self, texts, embeddings, metadatas=None):
        """
        Add a batch of documents + embeddings to the collection.
        """
        if not texts or not embeddings:
            return

        batch_size = len(texts)
        # Generate stable IDs based on content hash
        ids = [hashlib.md5(t.encode('utf-8')).hexdigest() for t in texts]

        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in range(batch_size)]

        # Deduplicate items in the batch based on ID
        unique_ids = set()
        unique_indices = []
        for i, doc_id in enumerate(ids):
            if doc_id not in unique_ids:
                unique_ids.add(doc_id)
                unique_indices.append(i)
        
        # Filter duplicates
        final_ids = [ids[i] for i in unique_indices]
        final_texts = [texts[i] for i in unique_indices]
        final_embeddings = [embeddings[i] for i in unique_indices]
        final_metadatas = [metadatas[i] for i in unique_indices]

        try:
            self.collection.upsert(
                embeddings=final_embeddings,
                documents=final_texts,
                metadatas=final_metadatas,
                ids=final_ids
            )
        except Exception as e:
            print(f"[VectorStore] Error adding batch: {e}")

    def search(self, query_embedding, k=5, filter_dict=None):
        """
        Search for nearest neighbors using query embedding.
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_dict # Optional: {"category": "History"}
            )
            
            # Chroma returns lists of lists (for multiple queries). We take the first.
            # Structure: {'ids': [['id1', 'id2']], 'distances': [[0.1, 0.2]], 'metadatas': [[{}, {}]], 'documents': [['text1', 'text2']]}
            
            parsed_results = []
            if results['documents']:
                for i in range(len(results['documents'][0])):
                    doc = results['documents'][0][i]
                    meta = results['metadatas'][0][i]
                    # Check if ids exist in results structure
                    doc_id = results['ids'][0][i] if 'ids' in results else None
                    dist = results['distances'][0][i]
                    # Convert cosine distance to similarity score
                    score = 1.0 - dist 
                    
                    parsed_results.append({
                        "id": doc_id,
                        "text": doc,
                        "metadata": meta,
                        "score": score
                    })
            
            return parsed_results

        except Exception as e:
            print(f"[VectorStore] Error during search: {e}")
            return []

    def count(self):
        """Return number of documents in collection."""
        return self.collection.count()

    def delete_by_metadata(self, filter_dict):
        """
        Delete documents matching the metadata filter.
        Example: vector_store.delete_by_metadata({"original_source": "file.json"})
        """
        try:
            # Optimize: Only fetch IDs/Metadata to check existence/count, not full content (documents/embeddings)
            # IDs are always returned. We request 'metadatas' as a lightweight field to satisfy 'include' validation.
            existing = self.collection.get(where=filter_dict, include=['metadatas'])
            count = len(existing['ids']) if existing and 'ids' in existing else 0
            
            if count == 0:
                print(f"[VectorStore] No documents found matching: {filter_dict}")
                return False

            print(f"[VectorStore] Found {count} documents matching {filter_dict}. Deleting...")
            self.collection.delete(where=filter_dict)
            print("[VectorStore] Deletion complete.")
            return True
        except Exception as e:
            print(f"[VectorStore] Error deleting documents: {e}")
            return False

    def reset(self):
        """Dangerous: Delete collection to start over."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name, 
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Error resetting collection: {e}")
    def get_all_documents(self):
        """
        Retrieve all documents from the collection.
        Useful for building in-memory indices (e.g., BM25).
        """
        try:
            # ChromaDB get() without arguments returns all
            # But for large collections, we might need pagination if it hits limits.
            # However, simpler to just get all for now for < 1M docs.
            results = self.collection.get()
            return results['documents'], results['metadatas'], results['ids']
        except Exception as e:
            print(f"[VectorStore] Error fetching all docs: {e}")
            return [], [], []

    def get_all_ids(self):
        """
        Retrieve only IDs of all documents.
        Optimized for incremental updates.
        """
        try:
            results = self.collection.get(include=[]) # No docs/metadatas
            return set(results['ids'])
        except Exception as e:
            print(f"[VectorStore] Error fetching IDs: {e}")
            return set()

