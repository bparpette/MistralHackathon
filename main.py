"""
MCP Collective Brain Server - Version multi-tenant optimisée pour Lambda
Système de mémoire collective avec isolation par équipe
"""

import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

# Import paresseux pour optimiser le démarrage Lambda
requests = None
QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None

# Charger les variables d'environnement depuis config.env.example si .env n'existe pas
if not os.path.exists('.env') and os.path.exists('config.env.example'):
    with open('config.env.example', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://hzoggayzniyxlbwxchcx.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

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
if IS_LAMBDA:
    # En Lambda, on désactive Qdrant au démarrage pour éviter les timeouts
    # Il sera activé seulement quand nécessaire
    USE_QDRANT = False
else:
    USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY and QDRANT_ENABLED)

# Debug minimal - seulement en local
if not IS_LAMBDA:
    print(f"🔧 Qdrant: {'Activé' if USE_QDRANT else 'Désactivé'}")
    print(f"🔧 Supabase: {'Activé' if SUPABASE_SERVICE_KEY else 'Désactivé'}")

# Import paresseux de FastMCP
def get_mcp():
    """Import paresseux de FastMCP - optimisé pour Lambda"""
    try:
        from mcp.server.fastmcp import FastMCP
        # Configuration optimisée pour Lambda
        return FastMCP(
            "Collective Brain Server", 
            port=3000, 
            stateless_http=True, 
            debug=False
        )
    except ImportError:
        if not IS_LAMBDA:
            print("❌ FastMCP non disponible")
        return None

# Variable globale pour stocker les headers de la requête courante
current_request_headers = {}

def set_request_headers(headers: dict):
    """Définir les headers de la requête courante"""
    global current_request_headers
    current_request_headers = headers

def get_request_headers() -> dict:
    """Récupérer les headers de la requête courante"""
    return current_request_headers

def extract_token_from_headers():
    """Extraire le token Bearer depuis les headers HTTP"""
    try:
        # 1. Essayer de récupérer depuis les headers de la requête courante
        request_headers = get_request_headers()
        print(f"🔍 Headers de la requête: {request_headers}")
        
        if "authorization" in request_headers:
            auth_header = request_headers["authorization"]
            if auth_header.startswith("Bearer "):
                print(f"✅ Token trouvé dans les headers de requête: {auth_header[7:]}")
                return auth_header[7:]  # Enlever "Bearer "
        
        # 2. Debug: afficher tous les headers disponibles dans l'environnement
        print("=== DEBUG HEADERS ENV ===")
        for key, value in os.environ.items():
            if "AUTH" in key.upper() or "HEADER" in key.upper() or "HTTP" in key.upper():
                print(f"{key}: {value}")
        print("========================")
        
        # 3. En Lambda, les headers sont disponibles via les variables d'environnement
        auth_header = os.getenv("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            print(f"✅ Token trouvé dans HTTP_AUTHORIZATION: {auth_header[7:]}")
            return auth_header[7:]  # Enlever "Bearer "
        
        # 4. Fallback: chercher dans d'autres variables d'environnement
        for key, value in os.environ.items():
            if "AUTHORIZATION" in key.upper() and value.startswith("Bearer "):
                print(f"✅ Token trouvé dans {key}: {value[7:]}")
                return value[7:]
        
        print("❌ Aucun token Bearer trouvé")
        return ""
    except Exception as e:
        print(f"❌ Erreur extraction token: {e}")
        return ""

# Modèle de données enrichi pour le cerveau collectif
class Memory:
    def __init__(self, content: str, user_id: str = "", team_id: str = "", 
                 timestamp: str = "", tags: List[str] = [], category: str = "general",
                 visibility: str = "team", confidence: float = 0.5):
        self.content = content
        self.user_id = user_id
        self.team_id = team_id
        self.timestamp = timestamp
        self.tags = tags
        self.category = category
        self.visibility = visibility
        self.confidence = confidence

# Stockage en mémoire simple (fallback)
memories: Dict[str, Memory] = {}

# Import paresseux de Qdrant
QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None

def ensure_qdrant_import():
    """Import paresseux de Qdrant - optimisé pour Lambda"""
    global QDRANT_AVAILABLE, QdrantClient, Distance, VectorParams, PointStruct
    
    if not QDRANT_AVAILABLE and USE_QDRANT:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            QDRANT_AVAILABLE = True
            # Pas de print en Lambda pour éviter les logs
            if not IS_LAMBDA:
                print("✅ Qdrant importé avec succès")
        except ImportError:
            QDRANT_AVAILABLE = False
            if not IS_LAMBDA:
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

def verify_user_token(user_token: str) -> Optional[Dict]:
    """Vérifier un token utilisateur via Supabase (obligatoire)"""
    global requests
    
    print(f"🔍 Début vérification token: {user_token[:10]}...")
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ Supabase non configuré - authentification obligatoire")
        return None
    
    # Import paresseux de requests
    if requests is None:
        try:
            import requests
            print("✅ Module requests importé")
        except ImportError:
            print("❌ Module requests non disponible")
            return None
    
    try:
        # Si c'est un token Bearer, enlever le préfixe
        if user_token.startswith("Bearer "):
            user_token = user_token[7:]
            print(f"🔍 Token nettoyé: {user_token[:10]}...")
        
        print(f"🔍 Appel Supabase: {SUPABASE_URL}/rest/v1/rpc/verify_user_token")
        
        # Appeler l'API Supabase pour vérifier le token
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/verify_user_token",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "apikey": SUPABASE_SERVICE_KEY
            },
            json={"token": user_token},
            timeout=3  # Timeout court pour Lambda
        )
        
        print(f"🔍 Réponse Supabase: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 Données reçues: {data}")
            if data and len(data) > 0:
                print(f"✅ Token valide pour utilisateur: {data[0]}")
                return data[0]
        
        print(f"❌ Token invalide: {user_token[:10]}... (status: {response.status_code})")
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification token: {e}")
        return None

class QdrantStorage:
    """Gestionnaire de stockage Qdrant multi-tenant"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
        self._init_attempted = False
    
    def _ensure_connected(self):
        """Connexion paresseuse avec timeout court"""
        if not self._initialized and not self._init_attempted:
            self._init_attempted = True
            
            # En Lambda, on active Qdrant seulement quand nécessaire
            if IS_LAMBDA and not QDRANT_ENABLED:
                # Vérifier si Qdrant est configuré
                if QDRANT_URL and QDRANT_API_KEY:
                    # Activer Qdrant dynamiquement
                    global USE_QDRANT
                    USE_QDRANT = True
            
            # Import paresseux
            ensure_qdrant_import()
            
            if not QDRANT_AVAILABLE:
                raise Exception("Qdrant non disponible")
            
            try:
                if not IS_LAMBDA:
                    print("🔄 Connexion Qdrant...")
                self.client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=2  # Timeout encore plus court pour Lambda
                )
                self._initialized = True
                if not IS_LAMBDA:
                    print("✅ Qdrant connecté")
            except Exception as e:
                if not IS_LAMBDA:
                    print(f"❌ Erreur Qdrant: {e}")
                self.client = None
                self._initialized = False
                raise Exception(f"Connexion Qdrant échouée: {e}")
        
        if not self._initialized:
            raise Exception("Qdrant non disponible")
    
    def _get_collection_name(self, team_id: str) -> str:
        """Générer le nom de collection pour une équipe"""
        # Nettoyer l'ID d'équipe pour créer un nom de collection valide
        clean_team_id = team_id.replace("-", "_").replace(" ", "_")
        return f"team_memories_{clean_team_id}"
    
    def _ensure_collection_exists(self, team_id: str):
        """S'assurer que la collection de l'équipe existe (paresseux)"""
        collection_name = self._get_collection_name(team_id)
        
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"✅ Collection '{collection_name}' créée pour l'équipe {team_id}")
            else:
                print(f"✅ Collection '{collection_name}' existe pour l'équipe {team_id}")
                
        except Exception as e:
            print(f"❌ Erreur collection: {e}")
            raise
    
    def store_memory(self, memory: Memory, memory_id: str, team_id: str) -> str:
        """Stocker une mémoire avec isolation par équipe"""
        try:
            self._ensure_connected()
            self._ensure_collection_exists(team_id)
            
            collection_name = self._get_collection_name(team_id)
            embedding = generate_embedding(memory.content)
            
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    "content": memory.content,
                    "timestamp": memory.timestamp,
                    "tags": memory.tags,
                    "user_id": memory.user_id,
                    "team_id": memory.team_id,
                    "category": memory.category,
                    "confidence": memory.confidence
                }
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            return memory_id
            
        except Exception as e:
            print(f"❌ Erreur stockage: {e}")
            raise
    
    def search_memories(self, query: str, team_id: str, limit: int = 5) -> List[Dict]:
        """Recherche avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            # Vérifier que la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                print(f"⚠️ Collection {collection_name} n'existe pas encore")
                return []
            
            query_embedding = generate_embedding(query)
            
            search_results = self.client.search(
                collection_name=collection_name,
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
                    "user_id": result.payload.get("user_id", "unknown"),
                    "category": result.payload.get("category", "general"),
                    "confidence": result.payload.get("confidence", 0.5),
                    "similarity_score": round(result.score, 3)
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche: {e}")
            return []
    
    def delete_memory(self, memory_id: str, team_id: str) -> bool:
        """Suppression avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=[memory_id]
            )
            return True
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
            return False
    
    def list_memories(self, team_id: str) -> List[Dict]:
        """Listage avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            # Vérifier que la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                return []
            
            points = self.client.scroll(
                collection_name=collection_name,
                limit=1000
            )[0]
            
            results = []
            for point in points:
                results.append({
                    "memory_id": point.id,
                    "content": point.payload["content"],
                    "tags": point.payload["tags"],
                    "timestamp": point.payload["timestamp"],
                    "user_id": point.payload.get("user_id", "unknown"),
                    "category": point.payload.get("category", "general"),
                    "confidence": point.payload.get("confidence", 0.5)
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

# Outils MCP avec authentification
def add_memory(
    content: str,
    user_token: str = "",
    tags: str = "",
    category: str = "general",
    visibility: str = "team"
) -> str:
    """Ajouter une mémoire au cerveau collectif avec authentification"""
    
    # Si pas de token fourni, essayer de le récupérer depuis les headers
    if not user_token:
        print("🔍 Aucun token fourni, recherche dans les headers...")
        user_token = extract_token_from_headers()
        print(f"🔍 Token extrait: {user_token[:10]}..." if user_token else "🔍 Aucun token trouvé")
        
        # MODE TEST: Si aucun token trouvé, utiliser le token de test
        if not user_token:
            print("🧪 MODE TEST: Utilisation du token de test")
            user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    print(f"🔍 Vérification du token: {user_token[:10]}...")
    user_info = verify_user_token(user_token)
    if not user_info:
        print(f"❌ Token invalide ou erreur de vérification: {user_token[:10]}...")
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    user_id = user_info["user_id"]
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Générer un ID unique
    memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}{user_id}".encode()).hexdigest()
    
    # Parser les tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Détection automatique de l'importance
    confidence = 0.5
    if any(word in content.lower() for word in ["décision", "important", "critique", "urgent", "bug", "erreur"]):
        confidence = 0.8
    elif any(word in content.lower() for word in ["solution", "résolu", "fix", "correction"]):
        confidence = 0.7
    
    # Détection automatique de catégorie
    if category == "general":
        if any(word in content.lower() for word in ["bug", "erreur", "problème", "issue"]):
            category = "bug"
        elif any(word in content.lower() for word in ["décision", "choix", "stratégie"]):
            category = "decision"
        elif any(word in content.lower() for word in ["feature", "fonctionnalité", "nouveau"]):
            category = "feature"
        elif any(word in content.lower() for word in ["réunion", "meeting", "call"]):
            category = "meeting"
    
    # Créer la mémoire enrichie
    memory = Memory(
        content=content,
        user_id=user_id,
        team_id=team_id,
        timestamp=datetime.now().isoformat(),
        tags=tag_list,
        category=category,
        visibility=visibility,
        confidence=confidence
    )
    
    # Stocker via le système de stockage
    storage = get_storage()
    if storage:
        try:
            storage.store_memory(memory, memory_id, team_id)
            message = f"Mémoire ajoutée au cerveau collectif de l'équipe (Qdrant)"
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            memories[memory_id] = memory
            message = f"Mémoire ajoutée au cerveau collectif (mémoire - fallback)"
    else:
        memories[memory_id] = memory
        message = f"Mémoire ajoutée au cerveau collectif (mémoire)"
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": message,
        "user": user_name,
        "team": team_id
    })

def search_memories(
    query: str,
    user_token: str = "",
    limit: int = 5
) -> str:
    """Rechercher dans le cerveau collectif avec authentification"""
    
    # Si pas de token fourni, essayer de le récupérer depuis les headers
    if not user_token:
        user_token = extract_token_from_headers()
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    print(f"🔍 Vérification du token: {user_token[:10]}...")
    user_info = verify_user_token(user_token)
    if not user_info:
        print(f"❌ Token invalide ou erreur de vérification: {user_token[:10]}...")
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    storage = get_storage()
    if storage:
        try:
            results = storage.search_memories(query, team_id, limit)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            results = []
    else:
        results = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not results:
        scored_memories = []
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:  # Isolation par équipe
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
                    "user_id": memory.user_id,
                    "category": memory.category,
                    "confidence": memory.confidence,
                    "similarity_score": round(similarity, 3)
                })
    
    return json.dumps({
        "status": "success",
        "query": query,
        "results": results,
        "total_found": len(results),
        "user": user_name,
        "team": team_id
    })

def delete_memory(memory_id: str, user_token: str = "") -> str:
    """Supprimer une mémoire du cerveau collectif avec authentification"""
    
    # Si pas de token fourni, essayer de le récupérer depuis les headers
    if not user_token:
        user_token = extract_token_from_headers()
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    print(f"🔍 Vérification du token: {user_token[:10]}...")
    user_info = verify_user_token(user_token)
    if not user_info:
        print(f"❌ Token invalide ou erreur de vérification: {user_token[:10]}...")
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    storage = get_storage()
    if storage:
        try:
            success = storage.delete_memory(memory_id, team_id)
            if success:
                return json.dumps({
                    "status": "success",
                    "message": f"Mémoire {memory_id} supprimée du cerveau collectif (Qdrant)"
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
    
    # Vérifier que la mémoire appartient à l'équipe de l'utilisateur
    memory = memories[memory_id]
    if memory.team_id != team_id:
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette mémoire"
        })
    
    del memories[memory_id]
    
    return json.dumps({
        "status": "success",
        "message": f"Mémoire {memory_id} supprimée du cerveau collectif (mémoire)"
    })

def list_memories(user_token: str = "") -> str:
    """Lister toutes les mémoires du cerveau collectif avec authentification"""
    
    # Si pas de token fourni, essayer de le récupérer depuis les headers
    if not user_token:
        user_token = extract_token_from_headers()
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    print(f"🔍 Vérification du token: {user_token[:10]}...")
    user_info = verify_user_token(user_token)
    if not user_info:
        print(f"❌ Token invalide ou erreur de vérification: {user_token[:10]}...")
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    storage = get_storage()
    if storage:
        try:
            all_memories = storage.list_memories(team_id)
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
                "message": "Aucune mémoire dans le cerveau collectif",
                "total": 0,
                "memories": [],
                "user": user_name,
                "team": team_id
            })
        
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:  # Isolation par équipe
                all_memories.append({
                    "memory_id": memory_id,
                    "content": memory.content,
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "user_id": memory.user_id,
                    "category": memory.category,
                    "confidence": memory.confidence
                })
    
    return json.dumps({
        "status": "success",
        "total": len(all_memories),
        "memories": all_memories,
        "user": user_name,
        "team": team_id
    })

def get_team_insights(user_token: str = "") -> str:
    """Obtenir des insights sur l'activité de l'équipe avec authentification"""
    
    # Si pas de token fourni, essayer de le récupérer depuis les headers
    if not user_token:
        user_token = extract_token_from_headers()
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    print(f"🔍 Vérification du token: {user_token[:10]}...")
    user_info = verify_user_token(user_token)
    if not user_info:
        print(f"❌ Token invalide ou erreur de vérification: {user_token[:10]}...")
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Récupérer toutes les mémoires de l'équipe
    all_memories = []
    storage = get_storage()
    
    if storage:
        try:
            all_memories = storage.list_memories(team_id)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
    
    # Fallback vers mémoire locale
    if not all_memories:
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:
                all_memories.append({
                    "memory_id": memory_id,
                    "content": memory.content,
                    "category": getattr(memory, 'category', 'general'),
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "user_id": getattr(memory, 'user_id', 'unknown'),
                    "confidence": getattr(memory, 'confidence', 0.5)
                })
    
    # Analyser les patterns
    categories = {}
    contributors = {}
    tags_count = {}
    high_confidence = 0
    
    for memory in all_memories:
        # Compter les catégories
        category = memory.get('category', 'general')
        categories[category] = categories.get(category, 0) + 1
        
        # Compter les contributeurs
        user = memory.get('user_id', 'unknown')
        contributors[user] = contributors.get(user, 0) + 1
        
        # Compter les tags
        for tag in memory.get('tags', []):
            tags_count[tag] = tags_count.get(tag, 0) + 1
        
        # Compter les mémoires importantes
        if memory.get('confidence', 0) > 0.7:
            high_confidence += 1
    
    # Top 5 de chaque catégorie
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
    top_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:5]
    top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    insights = {
        "team_id": team_id,
        "total_memories": len(all_memories),
        "high_confidence_memories": high_confidence,
        "top_categories": [{"category": cat, "count": count} for cat, count in top_categories],
        "top_contributors": [{"user": user, "contributions": count} for user, count in top_contributors],
        "trending_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
        "knowledge_health": {
            "coverage": len(categories),
            "activity_level": "high" if len(all_memories) > 20 else "medium" if len(all_memories) > 5 else "low",
            "collaboration_score": len(contributors) / max(len(all_memories), 1)
        }
    }
    
    return json.dumps({
        "status": "success",
        "insights": insights,
        "user": user_name,
        "team": team_id
    })

# Middleware pour capturer les headers
def capture_headers_middleware(request, call_next):
    """Middleware pour capturer les headers HTTP"""
    try:
        # Capturer les headers de la requête
        headers = dict(request.headers)
        set_request_headers(headers)
        print(f"🔍 Headers capturés: {headers}")
    except Exception as e:
        print(f"❌ Erreur capture headers: {e}")
    
    response = call_next(request)
    return response

# Initialisation paresseuse de MCP
def initialize_mcp():
    """Initialiser MCP de manière paresseuse"""
    global mcp
    
    if mcp is None:
        mcp = get_mcp()
        
        if mcp:
            # Ajouter le middleware pour capturer les headers
            try:
                # FastMCP utilise uvicorn, on doit accéder à l'app FastAPI différemment
                if hasattr(mcp, '_app') and mcp._app:
                    mcp._app.middleware("http")(capture_headers_middleware)
                    print("✅ Middleware headers ajouté")
                else:
                    print("⚠️ App FastAPI non accessible pour le middleware")
            except Exception as e:
                print(f"⚠️ Impossible d'ajouter le middleware: {e}")
            
            # Enregistrer les outils
            mcp.tool(
                title="Add Memory",
                description="Ajouter une mémoire au cerveau collectif de l'équipe",
            )(add_memory)
            
            mcp.tool(
                title="Search Memories",
                description="Rechercher dans le cerveau collectif de l'équipe",
            )(search_memories)
            
            mcp.tool(
                title="Delete Memory",
                description="Supprimer une mémoire du cerveau collectif",
            )(delete_memory)
            
            mcp.tool(
                title="List All Memories",
                description="Lister toutes les mémoires du cerveau collectif",
            )(list_memories)
            
            mcp.tool(
                title="Get Team Insights",
                description="Obtenir des insights sur l'activité de l'équipe",
            )(get_team_insights)
            
            if not IS_LAMBDA:
                print("✅ MCP initialisé avec succès")
        else:
            if not IS_LAMBDA:
                print("❌ Impossible d'initialiser MCP")
    
    return mcp

if __name__ == "__main__":
    if not IS_LAMBDA:
        print("🎯 Démarrage du serveur MCP Collective Brain...")
    
    # Initialisation paresseuse
    mcp = initialize_mcp()
    
    if mcp:
        if not IS_LAMBDA:
            print("🚀 Serveur MCP Collective Brain démarré - prêt à recevoir des requêtes")
        mcp.run(transport="streamable-http")
    else:
        if not IS_LAMBDA:
            print("❌ Impossible de démarrer le serveur MCP")
