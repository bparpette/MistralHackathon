"""
MCP Collective Brain Server
Système de mémoire collective pour équipes
"""

import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from mcp.server.fastmcp import FastMCP
from pydantic import Field, BaseModel
import mcp.types as types

# Import Qdrant (optionnel)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️ Qdrant non disponible - utilisation du stockage en mémoire")

# Configuration
mcp = FastMCP("Collective Brain Server", port=3000, stateless_http=True, debug=False)

# Modèles de données
class Memory(BaseModel):
    content: str
    user_id: str
    workspace_id: str
    category: str = "general"
    tags: List[str] = []
    visibility: str = "team"  # private, team, public
    confidence: float = 0.5
    timestamp: str = ""
    source_chat_id: str = ""
    verified_by: List[str] = []
    interactions: int = 0

class MemorySearchRequest(BaseModel):
    query: str
    workspace_id: str
    user_id: str
    limit: int = 5
    category_filter: Optional[str] = None
    visibility_filter: Optional[str] = None

# Stockage en mémoire (fallback si Qdrant n'est pas disponible)
collective_memories: Dict[str, Memory] = {}
workspace_memories: Dict[str, List[str]] = {}  # workspace_id -> list of memory_ids

class CollectiveBrainStorage:
    """Gestionnaire de stockage pour le cerveau collectif"""
    
    def __init__(self):
        self.use_qdrant = False  # Désactiver Qdrant par défaut pour le déploiement
        self.client = None
        self.collection_name = "collective_memories"
        
        # Essayer de se connecter à Qdrant seulement si explicitement configuré
        qdrant_url = os.getenv("QDRANT_URL")
        if QDRANT_AVAILABLE and qdrant_url and qdrant_url != "http://localhost:6333":
            try:
                qdrant_api_key = os.getenv("QDRANT_API_KEY")
                
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key if qdrant_api_key else None
                )
                self._init_collection()
                self.use_qdrant = True
                print("✅ Qdrant connecté avec succès")
            except Exception as e:
                print(f"⚠️ Erreur connexion Qdrant: {e} - utilisation du stockage en mémoire")
                self.use_qdrant = False
        else:
            print("📝 Utilisation du stockage en mémoire (Qdrant non configuré)")
    
    def _init_collection(self):
        """Initialiser la collection Qdrant"""
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,  # Taille pour all-MiniLM-L6-v2
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Collection '{self.collection_name}' créée")
        except Exception as e:
            # Collection existe déjà
            pass
    
    def store_memory(self, memory: Memory) -> str:
        """Stocker une mémoire"""
        memory_id = hashlib.md5(f"{memory.content}{memory.timestamp}{memory.user_id}".encode()).hexdigest()
        
        if self.use_qdrant:
            try:
                # Générer l'embedding
                embedding = generate_embedding(memory.content)
                
                # Créer le point
                point = PointStruct(
                    id=memory_id,
                    vector=embedding,
                    payload={
                        "content": memory.content,
                        "user_id": memory.user_id,
                        "workspace_id": memory.workspace_id,
                        "category": memory.category,
                        "tags": memory.tags,
                        "visibility": memory.visibility,
                        "confidence": memory.confidence,
                        "timestamp": memory.timestamp,
                        "interactions": memory.interactions,
                        "verified_by": memory.verified_by
                    }
                )
                
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                
            except Exception as e:
                print(f"⚠️ Erreur stockage Qdrant: {e} - fallback en mémoire")
                self.use_qdrant = False
        
        # Fallback en mémoire
        if not self.use_qdrant:
            collective_memories[memory_id] = memory
            if memory.workspace_id not in workspace_memories:
                workspace_memories[memory.workspace_id] = []
            workspace_memories[memory.workspace_id].append(memory_id)
        
        return memory_id
    
    def search_memories(self, query: str, workspace_id: str, user_id: str, limit: int = 5, 
                       category_filter: str = "", visibility_filter: str = "") -> List[Dict]:
        """Rechercher des mémoires"""
        
        if self.use_qdrant:
            try:
                query_embedding = generate_embedding(query)
                
                # Construire les filtres
                must_conditions = [
                    FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
                ]
                
                # Filtres de visibilité
                should_conditions = [
                    FieldCondition(key="visibility", match=MatchValue(value="team")),
                    FieldCondition(key="visibility", match=MatchValue(value="public")),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ]
                
                if category_filter:
                    must_conditions.append(
                        FieldCondition(key="category", match=MatchValue(value=category_filter))
                    )
                
                if visibility_filter:
                    must_conditions.append(
                        FieldCondition(key="visibility", match=MatchValue(value=visibility_filter))
                    )
                
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    query_filter=Filter(
                        must=must_conditions,
                        should=should_conditions
                    ),
                    limit=limit,
                    with_payload=True
                )
                
                # Formatter les résultats
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "content": result.payload["content"],
                        "author": result.payload["user_id"],
                        "category": result.payload["category"],
                        "tags": result.payload["tags"],
                        "timestamp": result.payload["timestamp"],
                        "relevance_score": round(result.score, 3),
                        "confidence": result.payload["confidence"],
                        "verified_by": result.payload.get("verified_by", []),
                        "interactions": result.payload.get("interactions", 0),
                        "visibility": result.payload["visibility"]
                    })
                
                return formatted_results
                
            except Exception as e:
                print(f"⚠️ Erreur recherche Qdrant: {e} - fallback en mémoire")
                self.use_qdrant = False
        
        # Fallback en mémoire
        if not self.use_qdrant:
            workspace_memory_ids = workspace_memories.get(workspace_id, [])
            accessible_memories = []
            
            for memory_id in workspace_memory_ids:
                memory = collective_memories.get(memory_id)
                if not memory:
                    continue
                    
                can_access = (
                    memory.visibility == "public" or
                    memory.visibility == "team" or
                    memory.user_id == user_id
                )
                
                if can_access:
                    accessible_memories.append(memory)
            
            # Appliquer les filtres
            filtered_memories = accessible_memories
            
            if category_filter:
                filtered_memories = [m for m in filtered_memories if m.category == category_filter]
            
            if visibility_filter:
                filtered_memories = [m for m in filtered_memories if m.visibility == visibility_filter]
            
            # Calculer la similarité et trier
            scored_memories = []
            for memory in filtered_memories:
                similarity = calculate_similarity(query, memory.content)
                score = similarity * memory.confidence
                scored_memories.append((score, memory))
            
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            
            # Formatter les résultats
            results = []
            for score, memory in scored_memories[:limit]:
                memory.interactions += 1
                
                results.append({
                    "content": memory.content,
                    "author": memory.user_id,
                    "category": memory.category,
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "relevance_score": round(score, 3),
                    "confidence": memory.confidence,
                    "verified_by": memory.verified_by,
                    "interactions": memory.interactions,
                    "visibility": memory.visibility
                })
            
            return results
        
        return []

# Initialiser le stockage de manière paresseuse
storage = None

def get_storage():
    """Obtenir l'instance de stockage (initialisation paresseuse)"""
    global storage
    if storage is None:
        storage = CollectiveBrainStorage()
    return storage

def generate_embedding(text: str) -> List[float]:
    """Génère un embedding simple basé sur le hash du texte (placeholder)"""
    # En production, utiliser FastEmbed ou l'API Mistral
    import hashlib
    hash_obj = hashlib.md5(text.encode())
    # Convertir le hash en vecteur de 384 dimensions
    hash_bytes = hash_obj.digest()
    vector = []
    for i in range(384):
        vector.append((hash_bytes[i % 16] - 128) / 128.0)
    return vector

def calculate_similarity(text1: str, text2: str) -> float:
    """Calcule la similarité entre deux textes (placeholder)"""
    # En production, utiliser la similarité cosinus des embeddings
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return intersection / union if union > 0 else 0.0

@mcp.tool(
    title="Store Collective Memory",
    description="Stocker une mémoire dans le cerveau collectif de l'équipe",
)
def store_memory(
    content: str = Field(description="Le contenu de la mémoire à stocker"),
    user_id: str = Field(description="ID de l'utilisateur qui crée la mémoire"),
    workspace_id: str = Field(description="ID du workspace/équipe"),
    category: str = Field(description="Catégorie de la mémoire", default="general"),
    tags: str = Field(description="Tags séparés par des virgules", default=""),
    visibility: str = Field(description="Visibilité: private, team, public", default="team"),
    importance: float = Field(description="Niveau d'importance (0-1)", default=0.5)
) -> str:
    """Stocker une mémoire collective avec contexte enrichi"""
    
    # Générer un ID unique
    memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}{user_id}".encode()).hexdigest()
    
    # Parser les tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Détection automatique de l'importance
    important_keywords = ["décision", "important", "critique", "urgent", "bug", "fix", "solution"]
    if any(keyword in content.lower() for keyword in important_keywords):
        importance = max(importance, 0.8)
    
    # Créer la mémoire
    memory = Memory(
        content=content,
        user_id=user_id,
        workspace_id=workspace_id,
        category=category,
        tags=tag_list,
        visibility=visibility,
        confidence=importance,
        timestamp=datetime.now().isoformat(),
        verified_by=[user_id]
    )
    
    # Stocker via le système de stockage
    memory_id = get_storage().store_memory(memory)
    
    # Trouver des mémoires similaires
    related_memories = []
    if not get_storage().use_qdrant:
        # Fallback pour le stockage en mémoire
        for mid, existing_memory in collective_memories.items():
            if (mid != memory_id and 
                existing_memory.workspace_id == workspace_id and
                calculate_similarity(content, existing_memory.content) > 0.3):
                related_memories.append(mid)
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": f"Mémoire collective ajoutée pour l'équipe {workspace_id}",
        "related_memories": related_memories[:3],  # Top 3
        "confidence": importance
    })

@mcp.tool(
    title="Search Collective Memories",
    description="Rechercher dans la mémoire collective de l'équipe",
)
def search_memories(
    query: str = Field(description="Requête de recherche"),
    workspace_id: str = Field(description="ID du workspace/équipe"),
    user_id: str = Field(description="ID de l'utilisateur qui recherche"),
    limit: int = Field(description="Nombre maximum de résultats", default=5),
    category_filter: str = Field(description="Filtrer par catégorie", default=""),
    visibility_filter: str = Field(description="Filtrer par visibilité", default="")
) -> str:
    """Rechercher dans la mémoire collective avec filtres"""
    
    # Utiliser le système de stockage pour la recherche
    results = get_storage().search_memories(
        query=query,
        workspace_id=workspace_id,
        user_id=user_id,
        limit=limit,
        category_filter=category_filter,
        visibility_filter=visibility_filter
    )
    
    return json.dumps({
        "status": "success",
        "query": query,
        "workspace_id": workspace_id,
        "results": results,
        "total_found": len(results)
    })

@mcp.tool(
    title="Get Team Insights",
    description="Obtenir des insights sur l'activité de l'équipe",
)
def get_team_insights(
    workspace_id: str = Field(description="ID du workspace/équipe"),
    timeframe: str = Field(description="Période: day, week, month", default="week")
) -> str:
    """Générer des insights sur l'activité de l'équipe"""
    
    workspace_memory_ids = workspace_memories.get(workspace_id, [])
    memories = [collective_memories[mid] for mid in workspace_memory_ids if mid in collective_memories]
    
    if not memories:
        return json.dumps({
            "status": "success",
            "insights": {
                "message": "Aucune mémoire trouvée pour ce workspace",
                "total_memories": 0
            }
        })
    
    # Analyser les patterns
    categories = {}
    tags = {}
    authors = {}
    recent_memories = []
    
    for memory in memories:
        # Catégories
        categories[memory.category] = categories.get(memory.category, 0) + 1
        
        # Tags
        for tag in memory.tags:
            tags[tag] = tags.get(tag, 0) + 1
        
        # Auteurs
        authors[memory.user_id] = authors.get(memory.user_id, 0) + 1
        
        # Mémoires récentes (dernières 24h)
        memory_time = datetime.fromisoformat(memory.timestamp)
        if (datetime.now() - memory_time).days <= 1:
            recent_memories.append(memory)
    
    # Top topics
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
    top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]
    top_contributors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Mémoires importantes récentes
    important_recent = [m for m in recent_memories if m.confidence > 0.7]
    
    insights = {
        "total_memories": len(memories),
        "recent_memories_24h": len(recent_memories),
        "important_recent": len(important_recent),
        "top_categories": top_categories,
        "top_tags": top_tags,
        "top_contributors": top_contributors,
        "most_interactive_memories": sorted(memories, key=lambda x: x.interactions, reverse=True)[:3]
    }
    
    return json.dumps({
        "status": "success",
        "workspace_id": workspace_id,
        "timeframe": timeframe,
        "insights": insights
    })

@mcp.tool(
    title="Verify Memory",
    description="Vérifier/confirmer une mémoire existante",
)
def verify_memory(
    memory_id: str = Field(description="ID de la mémoire à vérifier"),
    user_id: str = Field(description="ID de l'utilisateur qui vérifie"),
    workspace_id: str = Field(description="ID du workspace")
) -> str:
    """Permettre à un utilisateur de confirmer/vérifier une mémoire"""
    
    if memory_id not in collective_memories:
        return json.dumps({
            "status": "error",
            "message": "Mémoire non trouvée"
        })
    
    memory = collective_memories[memory_id]
    
    # Vérifier que l'utilisateur a accès à cette mémoire
    if (memory.workspace_id != workspace_id and 
        memory.visibility not in ["team", "public"] and 
        memory.user_id != user_id):
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette mémoire"
        })
    
    # Ajouter l'utilisateur aux vérificateurs
    if user_id not in memory.verified_by:
        memory.verified_by.append(user_id)
        # Augmenter la confiance
        memory.confidence = min(1.0, memory.confidence + 0.1)
    
    return json.dumps({
        "status": "success",
        "message": f"Mémoire vérifiée par {user_id}",
        "new_confidence": memory.confidence,
        "verified_by": memory.verified_by
    })

@mcp.tool(
    title="Echo Tool",
    description="Echo the input text (legacy tool)",
)
def echo(text: str = Field(description="The text to echo")) -> str:
    return text

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
