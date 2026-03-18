import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from src.models.schema import MemoryItem
from src.core.config import CHROMA_DB_PATH

class VectorStore:
    def __init__(self, persist_path: str = CHROMA_DB_PATH):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name="memory_stream")

    def add_memories(self, memories: List[MemoryItem], save_id: Optional[str] = None):
        ids = [m.id for m in memories]
        documents = [m.summary if m.summary else m.content for m in memories]
        
        metadatas = []
        for m in memories:
            meta = {
                "type": m.type, 
                "timestamp": str(m.timestamp), 
                "importance": m.importance,
                "original_content": m.content
            }
            if save_id:
                meta["save_id"] = save_id
            metadatas.append(meta)
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
        
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                meta = results['metadatas'][0][i]
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