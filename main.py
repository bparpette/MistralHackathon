"""
MCP Simple Brain Server - Version ultra-optimisée pour Lambda
Démarrage minimal avec initialisation paresseuse
"""

import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

# Charger les variables d'environnement depuis config.env.example si .env n'existe pas
if not os.path.exists('.env') and os.path.exists('config.env.example'):
    with open('config.env.example', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Configuration Qdrant - optimisée pour démarrage rapide
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "false").lower() == "true"

# Détection environnement Lambda
IS_LAMBDA = (
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None or
    os.getenv("AWS_EXECUTION_ENV") is not None or
    os.getenv("LAMBDA_TASK_ROOT") is not None
)

# En Lambda, mode paresseux pour éviter les timeouts
if IS_LAMBDA and QDRANT_ENABLED:
    print("🚀 Mode Lambda - Qdrant en mode paresseux")
    USE_QDRANT = True
else:
    USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY and QDRANT_ENABLED)

# Debug minimal
print(f"🔧 Qdrant: {'Activé' if USE_QDRANT else 'Désactivé'}")

# Import paresseux de FastMCP
def get_mcp():
    """Import paresseux de FastMCP"""
    try:
        from mcp.server.fastmcp import FastMCP
        return FastMCP("Simple Brain Server", port=3000, stateless_http=True, debug=False)
    except ImportError:
        print("❌ FastMCP non disponible")
        return None

# Modèle de données simplifié
class Memory:
    def __init__(self, content: str, timestamp: str = "", tags: List[str] = []):
        self.content = content
        self.timestamp = timestamp
        self.tags = tags

# Stockage en mémoire simple (fallback)
memories: Dict[str, Memory] = {}

# Import paresseux de Qdrant
QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None

def ensure_qdrant_import():
    """Import paresseux de Qdrant"""
    global QDRANT_AVAILABLE, QdrantClient, Distance, VectorParams, PointStruct
    
    if not QDRANT_AVAILABLE and USE_QDRANT:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            QDRANT_AVAILABLE = True
            print("✅ Qdrant importé avec succès")
        except ImportError:
            QDRANT_AVAILABLE = False
            print("❌ Qdrant non disponible")

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
    """Gestionnaire de stockage Qdrant ultra-optimisé"""
    
    def __init__(self):
        self.client = None
        self.collection_name = "shared_memories"
        self._initialized = False
        self._init_attempted = False
    
    def _ensure_connected(self):
        """Connexion paresseuse avec timeout court"""
        if not self._initialized and not self._init_attempted:
            self._init_attempted = True
            
            # Import paresseux
            ensure_qdrant_import()
            
            if not QDRANT_AVAILABLE:
                raise Exception("Qdrant non disponible")
            
            try:
                print("🔄 Connexion Qdrant...")
                self.client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=3  # Timeout très court pour Lambda
                )
                self._init_collection()
                self._initialized = True
                print("✅ Qdrant connecté")
            except Exception as e:
                print(f"❌ Erreur Qdrant: {e}")
                self.client = None
                self._initialized = False
                raise Exception(f"Connexion Qdrant échouée: {e}")
        
        if not self._initialized:
            raise Exception("Qdrant non disponible")
    
    def _init_collection(self):
        """Initialisation rapide de la collection"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"✅ Collection '{self.collection_name}' créée")
            else:
                print(f"✅ Collection '{self.collection_name}' existe")
                
        except Exception as e:
            print(f"❌ Erreur collection: {e}")
            raise
    
    def store_memory(self, memory: Memory, memory_id: str) -> str:
        """Stocker une mémoire avec timeout court"""
        try:
            self._ensure_connected()
            
            embedding = generate_embedding(memory.content)
            
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    "content": memory.content,
                    "timestamp": memory.timestamp,
                    "tags": memory.tags
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return memory_id
            
        except Exception as e:
            print(f"❌ Erreur stockage: {e}")
            raise
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche avec timeout court"""
        try:
            self._ensure_connected()
            
            query_embedding = generate_embedding(query)
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            
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
            print(f"❌ Erreur recherche: {e}")
            return []
    
    def delete_memory(self, memory_id: str) -> bool:
        """Suppression avec timeout court"""
        try:
            self._ensure_connected()
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[memory_id]
            )
            return True
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
            return False
    
    def list_memories(self) -> List[Dict]:
        """Listage avec timeout court"""
        try:
            self._ensure_connected()
            
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000
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
            print(f"❌ Erreur listage: {e}")
            return []

# Initialisation paresseuse du stockage
storage = None

def get_storage():
    """Obtenir l'instance de stockage avec initialisation paresseuse"""
    global storage
    if storage is None:
        if USE_QDRANT:
            storage = QdrantStorage()
        else:
            storage = None
    return storage

# Initialisation paresseuse de MCP
mcp = None

def get_mcp_instance():
    """Obtenir l'instance MCP avec initialisation paresseuse"""
    global mcp
    if mcp is None:
        mcp = get_mcp()
    return mcp

# Outils MCP avec initialisation paresseuse
def add_memory(
    content: str,
    tags: str = ""
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
        try:
            storage.store_memory(memory, memory_id)
            message = "Mémoire ajoutée au bucket partagé (Qdrant Cloud)"
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            memories[memory_id] = memory
            message = "Mémoire ajoutée au bucket partagé (mémoire - fallback)"
    else:
        memories[memory_id] = memory
        message = "Mémoire ajoutée au bucket partagé (mémoire)"
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": message
    })

def search_memories(
    query: str,
    limit: int = 5
) -> str:
    """Rechercher dans le bucket de mémoires partagé"""
    
    storage = get_storage()
    if storage:
        try:
            results = storage.search_memories(query, limit)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            results = []
    else:
        results = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not results:
        scored_memories = []
        for memory_id, memory in memories.items():
            similarity = calculate_similarity(query, memory.content)
            scored_memories.append((similarity, memory_id, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        for similarity, memory_id, memory in scored_memories[:limit]:
            if similarity > 0:
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

def delete_memory(memory_id: str) -> str:
    """Supprimer une mémoire du bucket partagé"""
    
    storage = get_storage()
    if storage:
        try:
            success = storage.delete_memory(memory_id)
            if success:
                return json.dumps({
                    "status": "success",
                    "message": f"Mémoire {memory_id} supprimée du bucket (Qdrant Cloud)"
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Erreur lors de la suppression"
                })
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
    
    # Utiliser le stockage en mémoire (fallback ou par défaut)
    if memory_id not in memories:
        return json.dumps({
            "status": "error",
            "message": "Mémoire non trouvée"
        })
    
    del memories[memory_id]
    
    return json.dumps({
        "status": "success",
        "message": f"Mémoire {memory_id} supprimée du bucket (mémoire)"
    })

def list_memories() -> str:
    """Lister toutes les mémoires du bucket partagé"""
    
    storage = get_storage()
    if storage:
        try:
            all_memories = storage.list_memories()
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            all_memories = []
    else:
        all_memories = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not all_memories:
        if not memories:
            return json.dumps({
                "status": "success",
                "message": "Aucune mémoire dans le bucket",
                "total": 0,
                "memories": []
            })
        
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

# Initialisation paresseuse de MCP
def initialize_mcp():
    """Initialiser MCP de manière paresseuse"""
    global mcp
    
    if mcp is None:
        mcp = get_mcp()
        
        if mcp:
            # Enregistrer les outils
            mcp.tool(
                title="Add Memory",
                description="Ajouter une mémoire au bucket partagé",
            )(add_memory)
            
            mcp.tool(
                title="Search Memories",
                description="Rechercher dans le bucket de mémoires partagé",
            )(search_memories)
            
            mcp.tool(
                title="Delete Memory",
                description="Supprimer une mémoire du bucket partagé",
            )(delete_memory)
            
            mcp.tool(
                title="List All Memories",
                description="Lister toutes les mémoires du bucket",
            )(list_memories)
            
            print("✅ MCP initialisé avec succès")
        else:
            print("❌ Impossible d'initialiser MCP")
    
    return mcp

if __name__ == "__main__":
    print("🎯 Démarrage du serveur MCP optimisé...")
    
    # Initialisation paresseuse
    mcp = initialize_mcp()
    
    if mcp:
        print("🚀 Serveur MCP démarré - prêt à recevoir des requêtes")
        mcp.run(transport="streamable-http")
    else:
        print("❌ Impossible de démarrer le serveur MCP")
