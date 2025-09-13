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
QDRANT_URL = os.getenv("QDRANT_URL")  # Ex: https://your-cluster.qdrant.tech
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # Votre clé API Qdrant
QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "false").lower() == "true"

# Détection environnement Lambda pour optimisation
IS_LAMBDA = (
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None or
    os.getenv("AWS_EXECUTION_ENV") is not None or
    os.getenv("LAMBDA_TASK_ROOT") is not None
)

# En Lambda, désactiver Qdrant au démarrage pour éviter les timeouts
# Il sera activé à la première utilisation
if IS_LAMBDA and QDRANT_ENABLED:
    print("🚀 Environnement Lambda détecté - Qdrant activé en mode paresseux")
    USE_QDRANT = True  # Configuré mais pas initialisé
else:
    USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY and QDRANT_ENABLED)

# Debug de la configuration
print(f"🔧 Configuration Qdrant:")
print(f"   QDRANT_ENABLED: {QDRANT_ENABLED}")
print(f"   QDRANT_URL: {QDRANT_URL}")
print(f"   QDRANT_API_KEY: {'***' if QDRANT_API_KEY else 'None'}")
print(f"   USE_QDRANT: {USE_QDRANT}")

# Configuration - optimisée pour démarrage rapide
mcp = FastMCP("Simple Brain Server", port=3000, stateless_http=True, debug=False)

# Message de démarrage rapide
print("🚀 Serveur MCP démarré - prêt à recevoir des requêtes")
if IS_LAMBDA:
    print("⚡ Mode Lambda optimisé - Qdrant initialisé à la première utilisation")
else:
    print("⚡ Démarrage optimisé - Qdrant sera initialisé à la première utilisation")

# Modèle de données simplifié
class Memory(BaseModel):
    content: str
    timestamp: str = ""
    tags: List[str] = []

# Stockage en mémoire simple (fallback)
memories: Dict[str, Memory] = {}

# Import Qdrant si disponible (seulement si activé) - optimisé pour démarrage rapide
QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None

if USE_QDRANT:
    try:
        # Import paresseux pour éviter les timeouts au démarrage
        print("🔗 Qdrant configuré - import paresseux activé")
        QDRANT_AVAILABLE = True
    except ImportError:
        QDRANT_AVAILABLE = False
        print("⚠️ Qdrant client non disponible, utilisation du stockage en mémoire")
else:
    print("📝 Utilisation du stockage en mémoire (Qdrant désactivé)")

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
    """Gestionnaire de stockage Qdrant avec lazy initialization optimisé pour Lambda"""
    
    def __init__(self):
        if not QDRANT_AVAILABLE:
            raise Exception("Qdrant non disponible")
        
        # Lazy initialization - pas de connexion au démarrage
        self.client = None
        self.collection_name = "shared_memories"
        self._initialized = False
        self._init_attempted = False
    
    def _ensure_connected(self):
        """S'assurer que la connexion Qdrant est établie avec gestion d'erreur robuste"""
        if not self._initialized and not self._init_attempted:
            self._init_attempted = True
            try:
                print("🔄 Connexion à Qdrant...")
                
                # Import paresseux des modules Qdrant
                global QdrantClient, Distance, VectorParams, PointStruct
                if QdrantClient is None:
                    from qdrant_client import QdrantClient
                    from qdrant_client.models import Distance, VectorParams, PointStruct
                
                self.client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=5  # Timeout très court pour Lambda
                )
                self._init_collection()
                self._initialized = True
                print("✅ Qdrant connecté et initialisé")
            except Exception as e:
                print(f"❌ Erreur connexion Qdrant: {e}")
                # En cas d'erreur, on continue sans Qdrant
                self.client = None
                self._initialized = False
                raise Exception(f"Impossible de se connecter à Qdrant: {e}")
        
        if not self._initialized:
            raise Exception("Qdrant non disponible - connexion échouée")
    
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
            # S'assurer que la connexion est établie
            self._ensure_connected()
            
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
            # S'assurer que la connexion est établie
            self._ensure_connected()
            
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
            # S'assurer que la connexion est établie
            self._ensure_connected()
            
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
            # S'assurer que la connexion est établie
            self._ensure_connected()
            
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
            # Créer l'instance SANS connexion réseau
            storage = QdrantStorage()
        else:
            print("📝 Qdrant Cloud désactivé - utilisation du stockage en mémoire")
            storage = None
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
        try:
            # Utiliser Qdrant
            storage.store_memory(memory, memory_id)
            message = "Mémoire ajoutée au bucket partagé (Qdrant Cloud)"
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            # Fallback vers stockage en mémoire
            memories[memory_id] = memory
            message = "Mémoire ajoutée au bucket partagé (mémoire - fallback)"
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
        try:
            # Utiliser Qdrant
            results = storage.search_memories(query, limit)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            # Fallback vers stockage en mémoire
            results = []
    else:
        # Utiliser le stockage en mémoire
        results = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not results:
        scored_memories = []
        for memory_id, memory in memories.items():
            similarity = calculate_similarity(query, memory.content)
            scored_memories.append((similarity, memory_id, memory))
        
        # Trier par similarité
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Formatter les résultats
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
        try:
            # Utiliser Qdrant
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
            # Fallback vers stockage en mémoire
            pass
    
    # Utiliser le stockage en mémoire (fallback ou par défaut)
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
        try:
            # Utiliser Qdrant
            all_memories = storage.list_memories()
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            # Fallback vers stockage en mémoire
            all_memories = []
    else:
        # Utiliser le stockage en mémoire
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
        
        # Formatter toutes les mémoires
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
    print("🎯 Démarrage du serveur MCP...")
    mcp.run(transport="streamable-http")
