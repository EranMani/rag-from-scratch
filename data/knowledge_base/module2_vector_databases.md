# Module 2: Fundamentals of Vector Databases

## What Is an Embedding?
An embedding is a numerical representation of meaning. An embedding model (e.g., all-MiniLM-L6-v2) converts text into a vector of floating-point numbers. Each dimension captures a semantic nuance — tone, formality, topic, sentiment.

- Standard models: 384 dimensions (all-MiniLM-L6-v2)
- Production models: 1,536 dimensions (text-embedding-3-small by OpenAI)
- Words like "holiday" and "vacation" produce similar vectors even though they share no letters

## Similarity Mathematics

### Cosine Similarity
Measures the cosine of the angle between two vectors.
- Score 1.0 = identical meaning
- Score 0.0 = completely unrelated
- Formula: cos(θ) = (A · B) / (|A| × |B|)

### Dot Product
Multiplies corresponding dimensions and sums the result. Used when vectors are normalized (same magnitude), making it equivalent to cosine similarity.

## Indexing Algorithms
Brute-force search compares every vector in the database — too slow at scale.

- **HNSW (Hierarchical Navigable Small World)**: Graph-based index. Creates layers of "skip links" for fast approximate nearest-neighbor search. Default in ChromaDB.
- **IVF (Inverted File Index)**: Clusters the vector space using k-means. Only searches nearby clusters.
- **LSH (Locality Sensitive Hashing)**: Hashes similar vectors into the same bucket for fast lookup.

## ChromaDB
ChromaDB is the vector database used in this system. It:
- Stores documents, embeddings, and metadata together
- Supports persistent storage to disk
- Provides both exact and approximate nearest-neighbor search
- Runs as a standalone server (HTTP API) or in-memory
