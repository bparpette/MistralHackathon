"""
MCP Simple Brain Server
Bucket de mémoire partagé - tout le monde peut ajouter/lire
"""

import hashlib
import json
from datetime import datetime
from typing import List, Dict

from mcp.server.fastmcp import FastMCP
from pydantic import Field, BaseModel

# Configuration
mcp = FastMCP("Simple Brain Server", port=3000, stateless_http=True, debug=False)

# Modèle de données simplifié
class Memory(BaseModel):
    content: str
    timestamp: str = ""
    tags: List[str] = []

# Stockage en mémoire simple
memories: Dict[str, Memory] = {}

def calculate_similarity(text1: str, text2: str) -> float:
    """Calcule la similarité entre deux textes"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return intersection / union if union > 0 else 0.0


@mcp.tool(
    title="Add Memory",
    description="Ajouter une mémoire au bucket partagé",
)
def add_memory(
    content: str = Field(description="Le contenu de la mémoire à ajouter"),
    tags: str = Field(description="Tags séparés par des virgules", default="")
) -> str:
    """Ajouter une mémoire au bucket partagé"""
    
    # Générer un ID unique
    memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()
    
    # Parser les tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Créer la mémoire
    memory = Memory(
        content=content,
        timestamp=datetime.now().isoformat(),
        tags=tag_list
    )
    
    # Stocker dans le bucket
    memories[memory_id] = memory
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": "Mémoire ajoutée au bucket partagé"
    })

@mcp.tool(
    title="Search Memories",
    description="Rechercher dans le bucket de mémoires partagé",
)
def search_memories(
    query: str = Field(description="Requête de recherche"),
    limit: int = Field(description="Nombre maximum de résultats", default=5)
) -> str:
    """Rechercher dans le bucket de mémoires partagé"""
    
    # Calculer la similarité pour toutes les mémoires
    scored_memories = []
    for memory_id, memory in memories.items():
        similarity = calculate_similarity(query, memory.content)
        scored_memories.append((similarity, memory_id, memory))
    
    # Trier par similarité
    scored_memories.sort(key=lambda x: x[0], reverse=True)
    
    # Formatter les résultats
    results = []
    for similarity, memory_id, memory in scored_memories[:limit]:
        if similarity > 0:  # Seulement les résultats avec une similarité > 0
            results.append({
                "memory_id": memory_id,
                "content": memory.content,
                "tags": memory.tags,
                "timestamp": memory.timestamp,
                "similarity_score": round(similarity, 3)
            })
    
    return json.dumps({
        "status": "success",
        "query": query,
        "results": results,
        "total_found": len(results)
    })

@mcp.tool(
    title="Delete Memory",
    description="Supprimer une mémoire du bucket partagé",
)
def delete_memory(
    memory_id: str = Field(description="ID de la mémoire à supprimer")
) -> str:
    """Supprimer une mémoire du bucket partagé"""
    
    if memory_id not in memories:
        return json.dumps({
            "status": "error",
            "message": "Mémoire non trouvée"
        })
    
    # Supprimer la mémoire
    del memories[memory_id]
    
    return json.dumps({
        "status": "success",
        "message": f"Mémoire {memory_id} supprimée du bucket"
    })

@mcp.tool(
    title="List All Memories",
    description="Lister toutes les mémoires du bucket",
)
def list_memories() -> str:
    """Lister toutes les mémoires du bucket partagé"""
    
    if not memories:
        return json.dumps({
            "status": "success",
            "message": "Aucune mémoire dans le bucket",
            "total": 0,
            "memories": []
        })
    
    # Formatter toutes les mémoires
    all_memories = []
    for memory_id, memory in memories.items():
        all_memories.append({
            "memory_id": memory_id,
            "content": memory.content,
            "tags": memory.tags,
            "timestamp": memory.timestamp
        })
    
    return json.dumps({
        "status": "success",
        "total": len(all_memories),
        "memories": all_memories
    })

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
