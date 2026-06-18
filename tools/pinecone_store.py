from pinecone import Pinecone
from anthropic import Anthropic
import os
import json
from datetime import datetime

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
anthropic_client = Anthropic()

def embed_text(text: str) -> list:
    """Use Anthropic embeddings or a simple hash fallback for demo."""
    # For demo purposes, use OpenAI-compatible embedding endpoint
    # In production, use a proper embedding model
    import hashlib
    # Simple demo: use a 1024-dim zero vector with checksum
    # Replace this with real embeddings in production
    checksum = int(hashlib.md5(text.encode()).hexdigest(), 16) % 1000
    vector = [0.0] * 1024
    vector[checksum] = 1.0
    return vector

def store_discharge_summary(patient_id: str, text: str, metadata: dict) -> bool:
    """Chunk and store discharge summary in Pinecone."""
    namespace = f"patient_{patient_id}"
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    vectors = []
    for i, chunk in enumerate(chunks):
        vector_id = f"{patient_id}_discharge_{i}"
        vectors.append({
            "id": vector_id,
            "values": embed_text(chunk),
            "metadata": {
                **metadata,
                "text": chunk,
                "chunk_index": i,
                "type": "discharge_summary"
            }
        })

    try:
        index.upsert(vectors=vectors, namespace=namespace)
        return True
    except Exception as e:
        print(f"Pinecone upsert failed: {e}")
        return False

def store_check_in(patient_id: str, check_in: dict) -> bool:
    """Store a daily check-in record."""
    namespace = f"patient_{patient_id}"
    vector_id = f"{patient_id}_checkin_{check_in['day']}"

    # Pinecone metadata only supports str/number/bool/list-of-str.
    # Serialize nested dicts and lists-of-non-str as JSON strings.
    metadata = {
        "type": "check_in",
        "stored_at": datetime.now().isoformat(),
        "day": check_in.get("day", 0),
        "timestamp": check_in.get("timestamp", ""),
        "classification": check_in.get("classification", ""),
        "summary": check_in.get("summary", ""),
        "recommended_action": check_in.get("recommended_action", ""),
        "responses_json": json.dumps(check_in.get("responses", {})),
        "flags_json": json.dumps(check_in.get("flags", [])),
    }

    try:
        index.upsert(
            vectors=[{
                "id": vector_id,
                "values": embed_text(json.dumps(check_in)),
                "metadata": metadata
            }],
            namespace=namespace
        )
        return True
    except Exception as e:
        print(f"Pinecone check-in store failed: {e}")
        return False

def retrieve_patient_history(patient_id: str, query: str, top_k: int = 5) -> list:
    """Retrieve relevant patient history chunks."""
    namespace = f"patient_{patient_id}"
    try:
        results = index.query(
            vector=embed_text(query),
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )
        return [match.metadata for match in results.matches]
    except Exception as e:
        print(f"Pinecone query failed: {e}")
        return []

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks