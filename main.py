"""
MCP Simple Brain Server
Bucket de mémoire partagé - tout le monde peut ajouter/lire
"""

import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field, BaseModel

# Configuration Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")  # Ex: https://your-cluster.qdrant.tech
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # Votre clé API Qdrant
QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "true").lower() == "true"  # Option pour désactiver
USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY and QDRANT_ENABLED)

# Configuration
mcp = FastMCP("Simple Brain Server", port=3000, stateless_http=True, debug=False)

# Modèle de données simplifié
class Memory(BaseModel):
    content: str
    timestamp: str = ""
    tags: List[str] = []

# Stockage en mémoire simple (fallback)
memories: Dict[str, Memory] = {}

# Import Qdrant si disponible
if USE_QDRANT:
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        QDRANT_AVAILABLE = True
        print(f"🔗 Connexion à Qdrant: {QDRANT_URL}")
    except ImportError:
        QDRANT_AVAILABLE = False
        print("⚠️ Qdrant client non disponible, utilisation du stockage en mémoire")
else:
    QDRANT_AVAILABLE = False
    print("📝 Utilisation du stockage en mémoire (QDRANT_URL non configuré)")

def calculate_similarity(text1: str, text2: str) -> float:
    """Calcule la similarité entre deux textes"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return intersection / union if union > 0 else 0.0

def generate_embedding(text: str) -> List[float]:
    """Génère un embedding simple basé sur le hash du texte"""
    hash_obj = hashlib.md5(text.encode())
    hash_bytes = hash_obj.digest()
    vector = []
    for i in range(384):  # Dimension standard
        vector.append((hash_bytes[i % 16] - 128) / 128.0)
    return vector

class QdrantStorage:
    """Gestionnaire de stockage Qdrant"""
    
    def __init__(self):
        if not QDRANT_AVAILABLE:
            raise Exception("Qdrant non disponible")
        
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        self.collection_name = "shared_memories"
        self._init_collection()
    
    def _init_collection(self):
        """Initialiser la collection Qdrant"""
        try:
            # Vérifier si la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Créer la collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"✅ Collection '{self.collection_name}' créée")
            else:
                print(f"✅ Collection '{self.collection_name}' existe déjà")
                
        except Exception as e:
            print(f"❌ Erreur initialisation Qdrant: {e}")
            raise
    
    def store_memory(self, memory: Memory, memory_id: str) -> str:
        """Stocker une mémoire dans Qdrant"""
        try:
            # Générer l'embedding
            embedding = generate_embedding(memory.content)
            
            # Créer le point
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    "content": memory.content,
                    "timestamp": memory.timestamp,
                    "tags": memory.tags
                }
            )
            
            # Insérer dans Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return memory_id
            
        except Exception as e:
            print(f"❌ Erreur stockage Qdrant: {e}")
            raise
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Rechercher des mémoires dans Qdrant"""
        try:
            # Générer l'embedding de la requête
            query_embedding = generate_embedding(query)
            
            # Recherche vectorielle
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            
            # Formatter les résultats
            results = []
            for result in search_results:
                results.append({
                    "memory_id": result.id,
                    "content": result.payload["content"],
                    "tags": result.payload["tags"],
                    "timestamp": result.payload["timestamp"],
                    "similarity_score": round(result.score, 3)
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche Qdrant: {e}")
            return []
    
    def delete_memory(self, memory_id: str) -> bool:
        """Supprimer une mémoire de Qdrant"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[memory_id]
            )
            return True
        except Exception as e:
            print(f"❌ Erreur suppression Qdrant: {e}")
            return False
    
    def list_memories(self) -> List[Dict]:
        """Lister toutes les mémoires de Qdrant"""
        try:
            # Récupérer tous les points
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000  # Limite raisonnable
            )[0]
            
            results = []
            for point in points:
                results.append({
                    "memory_id": point.id,
                    "content": point.payload["content"],
                    "tags": point.payload["tags"],
                    "timestamp": point.payload["timestamp"]
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur listage Qdrant: {e}")
            return []

# Initialiser le stockage (lazy loading)
storage = None

def get_storage():
    """Obtenir l'instance de stockage avec initialisation paresseuse"""
    global storage
    if storage is None:
        if USE_QDRANT and QDRANT_AVAILABLE:
            try:
                print("🔄 Initialisation de Qdrant...")
                storage = QdrantStorage()
                print("✅ Qdrant initialisé avec succès")
            except Exception as e:
                print(f"❌ Erreur initialisation Qdrant: {e}")
                print("📝 Fallback vers stockage en mémoire")
                storage = None
        else:
            storage = None  # Utiliser le stockage en mémoire
    return storage


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
    
    # Stocker via le système de stockage
    storage = get_storage()
    if storage:
        # Utiliser Qdrant
        storage.store_memory(memory, memory_id)
        message = "Mémoire ajoutée au bucket partagé (Qdrant)"
    else:
        # Utiliser le stockage en mémoire
        memories[memory_id] = memory
        message = "Mémoire ajoutée au bucket partagé (mémoire)"
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": message
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
    
    storage = get_storage()
    if storage:
        # Utiliser Qdrant
        results = storage.search_memories(query, limit)
    else:
        # Utiliser le stockage en mémoire
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
    
    storage = get_storage()
    if storage:
        # Utiliser Qdrant
        success = storage.delete_memory(memory_id)
        if success:
            return json.dumps({
                "status": "success",
                "message": f"Mémoire {memory_id} supprimée du bucket (Qdrant)"
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Erreur lors de la suppression"
            })
    else:
        # Utiliser le stockage en mémoire
        if memory_id not in memories:
            return json.dumps({
                "status": "error",
                "message": "Mémoire non trouvée"
            })
        
        # Supprimer la mémoire
        del memories[memory_id]
        
        return json.dumps({
            "status": "success",
            "message": f"Mémoire {memory_id} supprimée du bucket (mémoire)"
        })

@mcp.tool(
    title="List All Memories",
    description="Lister toutes les mémoires du bucket",
)
def list_memories() -> str:
    """Lister toutes les mémoires du bucket partagé"""
    
    storage = get_storage()
    if storage:
        # Utiliser Qdrant
        all_memories = storage.list_memories()
    else:
        # Utiliser le stockage en mémoire
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
