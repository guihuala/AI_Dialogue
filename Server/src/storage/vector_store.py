import chromadb
from chromadb.config import Settings
from typing import List, Dict
import uuid
from datetime import datetime
from src.models.schema import MemoryItem

class VectorStore:
    def __init__(self, persist_path: str = "chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name="memory_stream")

    def add_memories(self, memories: List[MemoryItem]):
        ids = [m.id for m in memories]
        # Use summary for embedding if available, otherwise content
        documents = [m.summary if m.summary else m.content for m in memories]
        
        metadatas = []
        for m in memories:
            meta = {
                "type": m.type, 
                "timestamp": str(m.timestamp), 
                "importance": m.importance,
                "original_content": m.content # Store original content in metadata
            }
            metadatas.append(meta)
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                meta = results['metadatas'][0][i]
                # Retrieve original content from metadata if available
                content = meta.get("original_content", results['documents'][0][i])
                
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": content,
                    "metadata": meta,
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        return formatted_results

    def update_memory(self, id: str, content: str, type: str, importance: int):
        self.collection.update(
            ids=[id],
            documents=[content],
            metadatas=[{"type": type, "timestamp": str(datetime.now()), "importance": importance}]
        )

    def delete_memory(self, id: str):
        self.collection.delete(ids=[id])

