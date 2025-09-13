#!/usr/bin/env python3
"""
Script de démonstration du système de mémoire collective
Simule le scénario de la startup AI avec 3 membres d'équipe
"""

import asyncio
import json
import requests
from datetime import datetime

# Configuration du serveur MCP
MCP_SERVER_URL = "https://mistralhackathonmcp-ee61017d.alpic.live/"

class CollectiveBrainDemo:
    def __init__(self, user_id: str, workspace_id: str = "startup_ai"):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.base_url = MCP_SERVER_URL
    
    def store_memory(self, content: str, category: str = "general", tags: str = "", visibility: str = "team", importance: float = 0.5):
        """Stocker une mémoire dans le cerveau collectif"""
        # Simulation d'appel MCP - en réalité ce serait via l'interface MCP
        print(f"🧠 [{self.user_id}] Stocke: {content[:50]}...")
        return {
            "status": "stored",
            "content": content,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "category": category,
            "tags": tags,
            "visibility": visibility,
            "importance": importance,
            "timestamp": datetime.now().isoformat()
        }
    
    def search_memories(self, query: str, limit: int = 5):
        """Rechercher dans la mémoire collective"""
        print(f"🔍 [{self.user_id}] Recherche: {query}")
        # Simulation de résultats
        return {
            "query": query,
            "results": [
                {
                    "content": "Client Enterprise X se plaint que l'API retourne erreur 429",
                    "author": "charlie_cs",
                    "relevance_score": 0.95,
                    "confidence": 0.9
                }
            ]
        }
    
    def get_insights(self):
        """Obtenir des insights sur l'équipe"""
        print(f"📊 [{self.user_id}] Demande des insights équipe...")
        return {
            "total_memories": 15,
            "recent_memories_24h": 3,
            "top_categories": [("bug", 5), ("decision", 3), ("feature", 2)],
            "top_contributors": [("charlie_cs", 8), ("bob_cto", 4), ("alice_ceo", 3)]
        }

async def killer_demo():
    """Démonstration du scénario killer: Bug critique résolu grâce au cerveau collectif"""
    
    print("🎬 DEMO: Bug critique résolu grâce au cerveau collectif\n")
    print("=" * 60)
    
    # 3 membres de l'équipe
    ceo = CollectiveBrainDemo("alice_ceo", "startup_ai")
    cto = CollectiveBrainDemo("bob_cto", "startup_ai")
    customer_success = CollectiveBrainDemo("charlie_cs", "startup_ai")
    
    # Étape 1: Customer Success reçoit une plainte
    print("\n1️⃣ Charlie (Customer Success) reçoit une plainte client...")
    cs_memory = customer_success.store_memory(
        content="Client Enterprise X se plaint que l'API retourne erreur 429 depuis 14h. "
                "C'est critique, ils menacent d'annuler le contrat de 500k€/an. "
                "Impact: perte de 500k€/an si on ne résout pas rapidement.",
        category="urgent",
        tags="client,api,erreur,revenue",
        visibility="team",
        importance=0.95
    )
    print(f"   ✅ Mémoire stockée: {cs_memory['content'][:80]}...")
    
    # Étape 2: CEO cherche le contexte business
    print("\n2️⃣ Alice (CEO) cherche l'impact business...")
    ceo_search = ceo.search_memories("Enterprise X problème impact financier")
    print(f"   🔍 Résultats trouvés: {len(ceo_search['results'])} mémoires")
    for result in ceo_search['results']:
        print(f"   📝 {result['content'][:60]}... (confiance: {result['confidence']})")
    
    # Le CEO stocke sa propre analyse
    ceo_memory = ceo.store_memory(
        content="Enterprise X = 500k€/an de revenue. Problème API critique. "
                "Priorité absolue: résoudre dans les 2h ou risque d'annulation contrat.",
        category="decision",
        tags="revenue,priorité,client-enterprise",
        importance=0.9
    )
    print(f"   ✅ CEO ajoute contexte business: {ceo_memory['content'][:60]}...")
    
    # Étape 3: CTO debug avec le contexte complet
    print("\n3️⃣ Bob (CTO) investigue le problème technique...")
    cto_search = cto.search_memories("erreur 429 API client important")
    print(f"   🔍 CTO trouve {len(cto_search['results'])} mémoires pertinentes")
    
    # Le CTO voit immédiatement que c'est Enterprise X (500k€), priorité max!
    cto_memory = cto.store_memory(
        content="Trouvé! Le rate limiter était mal configuré après le deploy de 13h45. "
                "Fix: augmenter la limite à 10000 req/min pour Enterprise tier. "
                "Hotfix déployé, monitoring en place. Client Enterprise X rassuré.",
        category="solution",
        tags="fix,rate-limiter,deploy,monitoring",
        importance=0.85
    )
    print(f"   ✅ CTO résout et documente: {cto_memory['content'][:60]}...")
    
    # Étape 4: Customer Success a immédiatement la solution
    print("\n4️⃣ Charlie peut rassurer le client avec les détails techniques...")
    cs_final_search = customer_success.search_memories("Enterprise X solution fix déployé")
    print(f"   🔍 CS trouve {len(cs_final_search['results'])} mémoires avec la solution")
    
    # Le CS a tous les détails techniques sans avoir à demander au CTO
    cs_final_memory = customer_success.store_memory(
        content="Client Enterprise X rassuré. Problème résolu en 45min. "
                "Solution: rate limiter configuré pour 10k req/min. "
                "Contrat sauvé, client satisfait de la réactivité.",
        category="resolution",
        tags="client-satisfait,contrat-sauve,reactivité",
        importance=0.8
    )
    print(f"   ✅ CS confirme résolution: {cs_final_memory['content'][:60]}...")
    
    # Étape 5: Insights de l'équipe
    print("\n5️⃣ Insights de l'équipe après résolution...")
    insights = ceo.get_insights()
    print(f"   📊 Total mémoires: {insights['total_memories']}")
    print(f"   📊 Mémoires récentes (24h): {insights['recent_memories_24h']}")
    print(f"   📊 Top catégories: {insights['top_categories']}")
    print(f"   📊 Top contributeurs: {insights['top_contributors']}")
    
    print("\n" + "=" * 60)
    print("✨ RÉSULTAT: Problème résolu en 45 min au lieu de 2h")
    print("   Sans cerveau collectif: CS -> Slack -> CEO -> CTO -> Slack -> CS")
    print("   Avec cerveau collectif: Tout le monde a le contexte instantanément!")
    print("   💰 Contrat de 500k€/an sauvé grâce à la réactivité!")
    
    print("\n🎯 AVANTAGES DÉMONTRÉS:")
    print("   ✅ Partage d'information instantané")
    print("   ✅ Contexte business + technique unifié")
    print("   ✅ Traçabilité des décisions")
    print("   ✅ Réduction drastique du temps de résolution")
    print("   ✅ Amélioration de la satisfaction client")

if __name__ == "__main__":
    print("🚀 Démarrage de la démonstration du cerveau collectif...")
    asyncio.run(killer_demo())
