# 🧠 De la mémoire individuelle au cerveau collectif

## Comprendre les Vector DBs (pour débutants)

### C'est quoi un embedding ?
```python
# Un texte devient un vecteur (liste de nombres)
"Le projet deadline est vendredi" → [0.23, -0.45, 0.67, ...]

# Des textes similaires ont des vecteurs proches
"La date limite du projet" → [0.21, -0.43, 0.65, ...] # Très proche !
"J'aime les pizzas" → [0.89, 0.12, -0.34, ...] # Très différent !
```

### Pourquoi c'est génial pour ton idée ?
- **Recherche sémantique** : "bug authentication" trouve aussi "problème de login"
- **Cross-language** : "server down" trouve aussi "serveur en panne"
- **Contexte** : Retrouve les infos pertinentes même avec des mots différents

## Architecture modifiée pour le cerveau collectif

### 1. Structure de données enrichie

```python
# Au lieu de stocker juste le texte, on ajoute du contexte
class CollectiveMemory:
    content: str           # Le contenu original
    embedding: List[float] # Le vecteur pour la recherche
    
    # Nouveaux champs pour le collectif
    user_id: str          # Qui a créé cette mémoire
    workspace_id: str     # Quelle équipe/projet
    visibility: str       # "private", "team", "public"
    category: str         # "decision", "bug", "feature", "meeting"
    confidence: float     # Importance de l'info (0-1)
    timestamp: datetime   
    related_memories: List[str]  # Liens vers d'autres mémoires
    
    # Metadata enrichie
    tags: List[str]       # ["backend", "urgent", "customer-X"]
    source_chat_id: str   # Pour tracer l'origine
    verified_by: List[str] # Autres users qui confirment l'info
```

### 2. MCP Server modifié

```python
# mcp_collective_brain.py
import asyncio
import os
from typing import List, Dict, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import hashlib
import json

class CollectiveBrainMCP:
    def __init__(self):
        # Connection Qdrant
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        # Collections séparées par type de données
        self.collections = {
            "memories": "collective_memories",
            "decisions": "team_decisions",
            "knowledge": "shared_knowledge"
        }
        
        # Créer les collections si elles n'existent pas
        self._init_collections()
    
    def _init_collections(self):
        """Créer les collections avec les bons paramètres"""
        for name, collection in self.collections.items():
            try:
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=384,  # Taille pour all-MiniLM-L6-v2
                        distance=Distance.COSINE
                    )
                )
            except:
                pass  # Collection existe déjà
    
    async def store_collective_memory(
        self,
        content: str,
        user_id: str,
        workspace_id: str,
        category: str = "general",
        tags: List[str] = None,
        visibility: str = "team",
        confidence: float = 0.5
    ) -> Dict:
        """
        Stocker une mémoire partagée avec contexte enrichi
        """
        # Générer l'embedding (ici on simule, en prod utiliser Mistral ou FastEmbed)
        embedding = await self._generate_embedding(content)
        
        # ID unique basé sur le contenu + timestamp
        memory_id = hashlib.md5(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        # Détection automatique de l'importance
        if any(word in content.lower() for word in ["décision", "important", "critique", "urgent"]):
            confidence = max(confidence, 0.8)
        
        # Créer le point pour Qdrant
        point = PointStruct(
            id=memory_id,
            vector=embedding,
            payload={
                "content": content,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "category": category,
                "tags": tags or [],
                "visibility": visibility,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "interactions": 0,  # Compteur d'utilisation
                "verified_by": [user_id]
            }
        )
        
        # Stocker dans la collection appropriée
        collection = self.collections.get(category, self.collections["memories"])
        self.client.upsert(
            collection_name=collection,
            points=[point]
        )
        
        # Détecter et créer des liens avec des mémoires similaires
        related = await self._find_related_memories(content, workspace_id, exclude_id=memory_id)
        
        return {
            "id": memory_id,
            "status": "stored",
            "related_memories": related,
            "message": f"Mémoire collective ajoutée pour l'équipe {workspace_id}"
        }
    
    async def search_team_knowledge(
        self,
        query: str,
        workspace_id: str,
        user_id: str,
        limit: int = 5,
        category_filter: Optional[str] = None,
        time_range: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Rechercher dans la mémoire collective de l'équipe
        """
        query_embedding = await self._generate_embedding(query)
        
        # Construire les filtres
        must_conditions = [
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]
        
        # Ajouter filtre de visibilité (respecter la privacy)
        should_conditions = [
            FieldCondition(key="visibility", match=MatchValue(value="team")),
            FieldCondition(key="visibility", match=MatchValue(value="public")),
            FieldCondition(key="user_id", match=MatchValue(value=user_id))  # Ses propres mémoires privées
        ]
        
        if category_filter:
            must_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category_filter))
            )
        
        # Recherche dans toutes les collections pertinentes
        all_results = []
        for collection in self.collections.values():
            try:
                results = self.client.search(
                    collection_name=collection,
                    query_vector=query_embedding,
                    query_filter=Filter(
                        must=must_conditions,
                        should=should_conditions
                    ),
                    limit=limit,
                    with_payload=True
                )
                all_results.extend(results)
            except:
                continue
        
        # Trier par score et confidence
        all_results.sort(key=lambda x: x.score * x.payload.get("confidence", 0.5), reverse=True)
        
        # Incrémenter le compteur d'interactions
        for result in all_results[:limit]:
            self._increment_interaction_count(result.id, collection)
        
        # Formatter les résultats
        formatted_results = []
        for result in all_results[:limit]:
            formatted_results.append({
                "content": result.payload["content"],
                "author": result.payload["user_id"],
                "category": result.payload["category"],
                "tags": result.payload["tags"],
                "timestamp": result.payload["timestamp"],
                "relevance_score": result.score,
                "confidence": result.payload["confidence"],
                "verified_by": result.payload.get("verified_by", []),
                "interactions": result.payload.get("interactions", 0)
            })
        
        return formatted_results
    
    async def get_team_insights(
        self,
        workspace_id: str,
        timeframe: str = "week"
    ) -> Dict:
        """
        Générer des insights sur l'activité de l'équipe
        """
        # Analyser les patterns dans les mémoires
        insights = {
            "top_topics": [],
            "active_contributors": [],
            "recent_decisions": [],
            "knowledge_gaps": [],
            "trending_tags": []
        }
        
        # Récupérer toutes les mémoires récentes de l'équipe
        # ... (logique d'analyse)
        
        return insights
    
    async def verify_memory(
        self,
        memory_id: str,
        user_id: str,
        workspace_id: str
    ) -> Dict:
        """
        Permettre à un utilisateur de confirmer/vérifier une mémoire
        """
        # Ajouter l'utilisateur à la liste verified_by
        # Augmenter le score de confidence
        pass
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Générer l'embedding du texte"""
        # En production: utiliser FastEmbed ou l'API Mistral
        # Pour le hackathon, vous pouvez utiliser sentence-transformers
        import numpy as np
        return np.random.rand(384).tolist()  # Placeholder
    
    async def _find_related_memories(
        self,
        content: str,
        workspace_id: str,
        exclude_id: str = None,
        threshold: float = 0.7
    ) -> List[str]:
        """Trouver des mémoires liées pour créer un knowledge graph"""
        # Rechercher des mémoires similaires
        # Retourner leurs IDs pour créer des liens
        pass
    
    def _increment_interaction_count(self, memory_id: str, collection: str):
        """Tracker combien de fois une mémoire est utilisée"""
        # Utile pour identifier les infos importantes
        pass
```

### 3. Agent Mistral adapté pour le collectif

```python
# collective_brain_agent.py
import asyncio
import os
from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.extra.mcp.sse import MCPClientSSE, SSEServerParams
from mistralai.extra.run.context import RunContext

load_dotenv()

class CollectiveBrainAgent:
    def __init__(self, user_id: str, workspace_id: str):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.client = Mistral(os.environ["MISTRAL_API_KEY"])
        
        # Instructions spécifiques pour le cerveau collectif
        self.agent = self.client.beta.agents.create(
            model=os.environ["MISTRAL_MODEL"],
            name=f"collective-brain-{workspace_id}",
            description="Agent qui partage et accède à la mémoire collective de l'équipe",
            instructions="""
            Tu es un assistant avec accès à la mémoire collective de l'équipe.
            
            RÈGLES IMPORTANTES:
            1. Toujours vérifier la mémoire collective avant de répondre
            2. Enrichir tes réponses avec le contexte de l'équipe
            3. Stocker automatiquement les informations importantes:
               - Décisions prises
               - Problèmes résolus
               - Connaissances partagées
               - Action items
            4. Catégoriser automatiquement les mémoires (decision, bug, feature, meeting, etc.)
            5. Identifier et taguer les sujets importants
            6. Faire des connexions entre différentes mémoires
            
            WORKFLOW:
            - D'abord, cherche dans la mémoire collective
            - Ensuite, réponds en utilisant ce contexte
            - Enfin, stocke les nouvelles infos importantes
            
            Utilise tes outils:
            - collective_store: pour sauvegarder dans la mémoire partagée
            - collective_search: pour chercher dans la mémoire de l'équipe
            - get_insights: pour avoir une vue d'ensemble
            - verify_info: pour confirmer une information
            """
        )
    
    async def process_message(self, message: str) -> str:
        """
        Traiter un message avec le contexte collectif
        """
        async with RunContext(
            agent_id=self.agent.id,
            continue_on_fn_error=True
        ) as ctx:
            # Enregistrer le serveur MCP avec contexte utilisateur
            sse_params = SSEServerParams(
                url=os.environ["MCP_SERVER_URL"],
                timeout=100,
                headers={
                    "X-User-Id": self.user_id,
                    "X-Workspace-Id": self.workspace_id
                }
            )
            
            await ctx.register_mcp_client(
                mcp_client=MCPClientSSE(sse_params=sse_params)
            )
            
            # Enrichir le message avec le contexte
            enriched_prompt = f"""
            [User: {self.user_id}]
            [Workspace: {self.workspace_id}]
            
            Message: {message}
            
            Rappel: Consulte d'abord la mémoire collective, puis réponds.
            """
            
            result = await self.client.beta.conversations.run_async(
                run_ctx=ctx,
                inputs=enriched_prompt
            )
            
            return result.output_as_text
```

### 4. Scénario de démo killer

```python
# demo_scenario.py
"""
DEMO: Startup AI - Résolution collaborative d'un bug critique
"""

async def killer_demo():
    # 3 membres de l'équipe
    ceo = CollectiveBrainAgent("alice_ceo", "startup_ai")
    cto = CollectiveBrainAgent("bob_cto", "startup_ai")
    customer_success = CollectiveBrainAgent("charlie_cs", "startup_ai")
    
    print("🎬 DEMO: Bug critique résolu grâce au cerveau collectif\n")
    
    # Étape 1: Customer Success reçoit une plainte
    print("1️⃣ Charlie (Customer Success) reçoit une plainte client...")
    await customer_success.process_message(
        "Client Enterprise X se plaint que l'API retourne erreur 429 depuis 14h. "
        "C'est critique, ils menacent d'annuler le contrat de 500k€/an."
    )
    
    # Étape 2: CEO cherche le contexte business
    print("\n2️⃣ Alice (CEO) cherche l'impact business...")
    ceo_response = await ceo.process_message(
        "Quel est le problème avec le client Enterprise X? Impact financier?"
    )
    print(f"CEO: {ceo_response}")
    # -> Le CEO obtient instantanément le contexte du CS
    
    # Étape 3: CTO debug avec le contexte complet
    print("\n3️⃣ Bob (CTO) investigue le problème technique...")
    cto_response = await cto.process_message(
        "Erreur 429 sur l'API, qu'est-ce qui peut causer ça? Client important?"
    )
    print(f"CTO: {cto_response}")
    # -> Le CTO voit immédiatement que c'est Enterprise X (500k€), priorité max!
    
    # Étape 4: CTO trouve et partage la solution
    await cto.process_message(
        "Trouvé! Le rate limiter était mal configuré après le deploy de 13h45. "
        "Fix: augmenter la limite à 10000 req/min pour Enterprise tier. "
        "Hotfix déployé, monitoring en place."
    )
    
    # Étape 5: Customer Success a immédiatement la solution
    print("\n4️⃣ Charlie peut rassurer le client avec les détails techniques...")
    cs_final = await customer_success.process_message(
        "Comment expliquer la résolution au client Enterprise X?"
    )
    print(f"CS: {cs_final}")
    # -> Le CS a tous les détails techniques sans avoir à demander au CTO
    
    print("\n✨ RÉSULTAT: Problème résolu en 10 min au lieu de 2h")
    print("   Sans cerveau collectif: CS -> Slack -> CEO -> CTO -> Slack -> CS")
    print("   Avec cerveau collectif: Tout le monde a le contexte instantanément!")
```

## Points clés pour implémenter

### 1. **Différenciation avec l'exemple de base**
- **Multi-tenant**: Chaque workspace a ses données isolées
- **Permissions granulaires**: Private/Team/Public
- **Enrichissement automatique**: Tags, catégories, importance
- **Knowledge graph**: Connexions entre mémoires

### 2. **Défis techniques à résoudre**
```python
# Gestion des conflits
if memory_exists_with_different_info:
    create_version()
    notify_team_of_discrepancy()

# Éviter la duplication
if similar_memory_exists(threshold=0.9):
    merge_or_update()
    
# Pertinence temporelle
decay_factor = calculate_time_decay(memory.timestamp)
final_score = relevance_score * decay_factor
```

### 3. **Architecture serveur MCP**
Le serveur MCP doit exposer ces outils:
- `collective_store`: Sauvegarder avec contexte
- `collective_search`: Recherche filtrée par workspace
- `get_insights`: Analytics de l'équipe
- `verify_info`: Validation collaborative
- `link_memories`: Créer des connexions

### 4. **Optimisations Qdrant**
```python
# Collections séparées pour performance
collections = {
    "hot": "memories_24h",      # Recherche rapide récente
    "warm": "memories_week",    # Cette semaine
    "cold": "memories_archive"  # Historique
}

# Index optimisés
index_config = IndexParams(
    metric="cosine",
    ef_construct=512,  # Plus précis
    m=16
)
```

## Plan d'action concret pour le hackathon

### Samedi matin (3h)
1. **Setup Qdrant Cloud** ✓ (fourni gratuitement)
2. **Fork le mcp-server-qdrant** et modifier pour multi-users
3. **Créer les structures de données** enrichies

### Samedi après-midi (4h)
1. **Implémenter les fonctions core** (store/search collectifs)
2. **Système de permissions** basique
3. **Tests avec 2-3 agents** simultanés

### Samedi soir (4h)
1. **UI dashboard** simple (React/Streamlit)
2. **Visualisation du knowledge graph**
3. **Métriques en temps réel**

### Dimanche matin (3h)
1. **Scénario de démo** béton
2. **Polish et debug**
3. **Documentation**

## Tips spécifiques Qdrant

1. **Batch operations** pour performance:
```python
# Au lieu de stocker une par une
points = [create_point(memory) for memory in memories]
client.upsert(collection_name="collective", points=points)
```

2. **Payloads indexés** pour filtrage rapide:
```python
client.create_payload_index(
    collection_name="collective",
    field_name="workspace_id",
    field_type="keyword"
)
```

3. **Snapshots** pour backup/restore rapide pendant la démo

Dis-moi ce qui n'est pas clair et on creuse ! L'avantage c'est que tu as déjà 50% du code avec leur exemple, il faut "juste" l'adapter pour le multi-users/multi-workspace 🚀