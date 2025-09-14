#!/usr/bin/env python3
"""
Chat Simple avec Mistral - Intégration complète des fonctionnalités
Utilise toutes les fonctions développées pour un chat intelligent
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Ajouter le répertoire parent pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importer toutes les fonctions du main.py
from main import (
    # Fonctions de base
    verify_user_token, extract_token_from_headers,
    ensure_mistral_import, generate_embedding, get_storage,
    
    # Fonctions de conversation
    chat_with_mistral, end_chat_and_summarize,
    search_past_conversations, get_full_transcript,
    
    # Fonctions de mémoire
    add_memory, search_memories, list_memories,
    
    # Configuration
    MISTRAL_ENABLED, MISTRAL_API_KEY, IS_LAMBDA
)

class SimpleChat:
    """Chat simple avec toutes les fonctionnalités intégrées"""
    
    def __init__(self):
        self.conversation_id = None
        self.user_info = None
        self.storage = None
        self.mistral = None
        
        # Initialiser les services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialiser tous les services nécessaires"""
        print("🔧 Initialisation des services...")
        
        # Initialiser Mistral
        ensure_mistral_import()
        if MISTRAL_ENABLED and MISTRAL_API_KEY:
            from mistralai import Mistral
            self.mistral = Mistral(api_key=MISTRAL_API_KEY)
            print("✅ Mistral initialisé")
        else:
            print("❌ Mistral non configuré")
        
        # Initialiser le stockage
        self.storage = get_storage()
        if self.storage:
            print("✅ Stockage vectoriel initialisé")
        else:
            print("⚠️ Stockage vectoriel non disponible")
        
        # Mode test par défaut
        self.user_info = {
            "user_id": "user_unified_test",  # ID unifié pour toutes les conversations
            "team_id": "test-team-123",
            "user_name": "Utilisateur Test"
        }
        print("✅ Mode test activé")
    
    def start_conversation(self, user_name: str = "Utilisateur"):
        """Démarrer une nouvelle conversation"""
        self.conversation_id = hashlib.md5(f"{user_name}-{datetime.now().isoformat()}".encode()).hexdigest()
        self.user_info["user_name"] = user_name
        
        print(f"\n🎯 Nouvelle conversation démarrée")
        print(f"📝 ID: {self.conversation_id}")
        print(f"👤 Utilisateur: {user_name}")
        print(f"🧠 Stockage: {'✅' if self.storage else '❌'}")
        print(f"🤖 Mistral: {'✅' if self.mistral else '❌'}")
        print("\n" + "="*50)
        print("💬 Tapez votre message (ou 'quit' pour quitter, 'help' pour l'aide)")
        print("="*50)
    
    def _search_relevant_conversations(self, query: str) -> List[Dict]:
        """Rechercher des conversations pertinentes"""
        if not self.storage:
            return []
        
        try:
            # Rechercher dans les conversations passées
            result = search_past_conversations(query, limit=3)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("results", [])
            else:
                print(f"⚠️ Erreur recherche conversations: {data.get('message')}")
                return []
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {e}")
            return []
    
    def _search_memories(self, query: str) -> List[Dict]:
        """Rechercher dans les mémoires"""
        if not self.storage:
            return []
        
        try:
            result = search_memories(query, limit=5)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("results", [])
            else:
                print(f"⚠️ Erreur recherche mémoires: {data.get('message')}")
                return []
        except Exception as e:
            print(f"❌ Erreur lors de la recherche de mémoires: {e}")
            return []
    
    def _get_full_conversation(self, chat_id: str) -> Optional[str]:
        """Récupérer une conversation complète"""
        try:
            result = get_full_transcript(chat_id)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("transcript")
            else:
                print(f"⚠️ Erreur récupération conversation: {data.get('message')}")
                return None
        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {e}")
            return None
    
    def _add_memory(self, content: str, tags: str = "", category: str = "general"):
        """Ajouter une mémoire"""
        try:
            result = add_memory(content, tags, category)
            data = json.loads(result)
            
            if data.get("status") == "success":
                print(f"💾 Mémoire ajoutée: {data.get('message')}")
            else:
                print(f"⚠️ Erreur ajout mémoire: {data.get('message')}")
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de mémoire: {e}")
    
    def _generate_response_with_context(self, user_message: str) -> str:
        """Générer une réponse avec contexte des conversations passées"""
        if not self.mistral:
            return "❌ Mistral n'est pas configuré. Veuillez configurer MISTRAL_API_KEY."
        
        # 1. Rechercher des conversations pertinentes
        print("🔍 Recherche de conversations pertinentes...")
        relevant_conversations = self._search_relevant_conversations(user_message)
        
        # 2. Rechercher des mémoires pertinentes
        print("🧠 Recherche dans les mémoires...")
        relevant_memories = self._search_memories(user_message)
        
        # 3. Construire le contexte
        context = ""
        
        if relevant_conversations:
            context += "\n📚 CONVERSATIONS PERTINENTES TROUVÉES:\n"
            for i, conv in enumerate(relevant_conversations, 1):
                context += f"\n--- Conversation {i} ---\n"
                context += f"Résumé: {conv.get('summary', 'N/A')}\n"
                context += f"Score: {conv.get('score', 0):.3f}\n"
                context += f"Date: {conv.get('timestamp', 'N/A')}\n"
        
        if relevant_memories:
            context += "\n💾 MÉMOIRES PERTINENTES:\n"
            for i, mem in enumerate(relevant_memories, 1):
                context += f"\n--- Mémoire {i} ---\n"
                context += f"Contenu: {mem.get('content', 'N/A')}\n"
                context += f"Catégorie: {mem.get('category', 'N/A')}\n"
                context += f"Score: {mem.get('similarity_score', 0):.3f}\n"
        
        # 4. Si des conversations sont très pertinentes, récupérer les détails
        detailed_context = ""
        if relevant_conversations:
            # Prendre la conversation la plus pertinente
            best_conv = max(relevant_conversations, key=lambda x: x.get('score', 0))
            if best_conv.get('score', 0) > 0.7:  # Seuil de pertinence
                print(f"📖 Récupération des détails de la conversation {best_conv.get('chat_id')}...")
                full_transcript = self._get_full_conversation(best_conv.get('chat_id'))
                if full_transcript:
                    detailed_context = f"\n📖 DÉTAILS DE LA CONVERSATION LA PLUS PERTINENTE:\n{full_transcript}\n"
        
        # 5. Construire le prompt final
        system_prompt = f"""Tu es un assistant IA expert avec accès à une mémoire collective et aux conversations passées.

CONTEXTE DISPONIBLE:
{context}
{detailed_context}

INSTRUCTIONS:
- Utilise le contexte fourni pour répondre de manière pertinente
- Si tu trouves des informations utiles dans les conversations/mémoires, cite-les
- Si l'utilisateur pose une question spécifique, cherche dans le contexte
- Si tu ajoutes de nouvelles informations importantes, mentionne-le
- Sois précis et utile en utilisant toutes les informations disponibles

Réponds de manière naturelle et utile en français."""

        try:
            # Appel à Mistral avec le contexte
            response = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"❌ Erreur lors de la génération de réponse: {e}"
    
    def _summarize_conversation(self) -> str:
        """Résumer la conversation actuelle"""
        if not self.conversation_id:
            return "Aucune conversation en cours"
        
        try:
            result = end_chat_and_summarize(self.conversation_id)
            data = json.loads(result)
            
            if data.get("status") == "success":
                summary = data.get("summary", "Résumé non disponible")
                print(f"\n📝 RÉSUMÉ DE LA CONVERSATION:")
                print(f"{summary}")
                print(f"\n💾 Conversation sauvegardée avec l'ID: {self.conversation_id}")
                return summary
            else:
                print(f"⚠️ Erreur lors du résumé: {data.get('message')}")
                return "Erreur lors du résumé"
        except Exception as e:
            print(f"❌ Erreur lors du résumé: {e}")
            return "Erreur lors du résumé"
    
    def chat_loop(self):
        """Boucle principale du chat"""
        if not self.mistral:
            print("❌ Impossible de démarrer le chat: Mistral non configuré")
            return
        
        print("🚀 Démarrage du chat simple...")
        self.start_conversation()
        
        while True:
            try:
                # Lire l'entrée utilisateur
                user_input = input("\n👤 Vous: ").strip()
                
                # Commandes spéciales
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Fin de la conversation...")
                    self._summarize_conversation()
                    break
                
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                elif user_input.lower() == 'summary':
                    self._summarize_conversation()
                    continue
                
                elif user_input.lower() == 'memories':
                    self._show_memories()
                    continue
                
                elif user_input.lower() == 'search':
                    self._interactive_search()
                    continue
                
                elif not user_input:
                    continue
                
                # Traiter le message
                print("\n🤖 Assistant: ", end="", flush=True)
                response = self._generate_response_with_context(user_input)
                print(response)
                
                # Ajouter automatiquement des informations importantes à la mémoire
                if any(keyword in user_input.lower() for keyword in ['important', 'souviens-toi', 'note', 'décision', 'solution']):
                    print("💾 Ajout automatique à la mémoire...")
                    self._add_memory(user_input, category="important")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interruption détectée...")
                self._summarize_conversation()
                break
            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                continue
    
    def _show_help(self):
        """Afficher l'aide"""
        print("\n📚 COMMANDES DISPONIBLES:")
        print("  help     - Afficher cette aide")
        print("  summary  - Résumer la conversation actuelle")
        print("  memories - Afficher les mémoires récentes")
        print("  search   - Recherche interactive")
        print("  quit     - Quitter le chat")
        print("\n💡 Le chat utilise automatiquement:")
        print("  - Recherche dans les conversations passées")
        print("  - Recherche dans les mémoires")
        print("  - Résumé automatique à la fin")
        print("  - Sauvegarde des conversations")
    
    def _show_memories(self):
        """Afficher les mémoires"""
        try:
            result = list_memories()
            data = json.loads(result)
            
            if data.get("status") == "success":
                memories = data.get("memories", [])
                print(f"\n💾 MÉMOIRES ({len(memories)} trouvées):")
                for i, mem in enumerate(memories[:10], 1):  # Limiter à 10
                    print(f"\n{i}. {mem.get('content', 'N/A')[:100]}...")
                    print(f"   Catégorie: {mem.get('category', 'N/A')}")
                    print(f"   Date: {mem.get('timestamp', 'N/A')}")
            else:
                print(f"⚠️ Erreur: {data.get('message')}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    def _interactive_search(self):
        """Recherche interactive"""
        query = input("🔍 Terme de recherche: ").strip()
        if not query:
            return
        
        print(f"\n🔍 Recherche de: '{query}'")
        
        # Rechercher dans les conversations
        conversations = self._search_relevant_conversations(query)
        if conversations:
            print(f"\n📚 CONVERSATIONS TROUVÉES ({len(conversations)}):")
            for i, conv in enumerate(conversations, 1):
                print(f"\n{i}. Score: {conv.get('score', 0):.3f}")
                print(f"   Résumé: {conv.get('summary', 'N/A')[:200]}...")
                print(f"   Date: {conv.get('timestamp', 'N/A')}")
        
        # Rechercher dans les mémoires
        memories = self._search_memories(query)
        if memories:
            print(f"\n💾 MÉMOIRES TROUVÉES ({len(memories)}):")
            for i, mem in enumerate(memories, 1):
                print(f"\n{i}. Score: {mem.get('similarity_score', 0):.3f}")
                print(f"   Contenu: {mem.get('content', 'N/A')[:200]}...")
                print(f"   Catégorie: {mem.get('category', 'N/A')}")

def main():
    """Fonction principale"""
    print("🧠 Chat Simple avec Mistral - Version Complète")
    print("=" * 50)
    
    # Vérifier la configuration
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        print("⚠️ ATTENTION: Mistral n'est pas configuré!")
        print("   Configurez MISTRAL_API_KEY dans votre fichier .env")
        print("   Le chat fonctionnera en mode limité")
        print()
    
    # Créer et démarrer le chat
    chat = SimpleChat()
    chat.chat_loop()

if __name__ == "__main__":
    main()
