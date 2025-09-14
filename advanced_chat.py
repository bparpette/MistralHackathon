#!/usr/bin/env python3
"""
Chat Avancé avec Mistral - Résumation automatique à chaque message
Version optimisée avec résumation continue et recherche intelligente
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

class AdvancedChat:
    """Chat avancé avec résumation automatique et recherche intelligente"""
    
    def __init__(self):
        self.conversation_id = None
        self.user_info = None
        self.storage = None
        self.mistral = None
        self.conversation_history = []
        self.summary_threshold = 3  # Résumer tous les 3 messages
        
        # Initialiser les services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialiser tous les services nécessaires"""
        print("🔧 Initialisation des services avancés...")
        
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
        self.conversation_history = []
        
        print(f"\n🎯 Nouvelle conversation avancée démarrée")
        print(f"📝 ID: {self.conversation_id}")
        print(f"👤 Utilisateur: {user_name}")
        print(f"🧠 Stockage: {'✅' if self.storage else '❌'}")
        print(f"🤖 Mistral: {'✅' if self.mistral else '❌'}")
        print(f"📊 Résumation: Tous les {self.summary_threshold} messages")
        print("\n" + "="*60)
        print("💬 Tapez votre message (ou 'quit' pour quitter, 'help' pour l'aide)")
        print("="*60)
    
    def _auto_summarize(self) -> str:
        """Résumer automatiquement la conversation actuelle"""
        if len(self.conversation_history) < 2:
            return ""
        
        if not self.mistral:
            return ""
        
        try:
            from main import generate_continuous_summary
            summary = generate_continuous_summary(
                self.conversation_history,
                self.conversation_id,
                self.user_info["team_id"]
            )
            return summary
        except Exception as e:
            print(f"⚠️ Erreur résumation automatique: {e}")
            return ""
    
    def _search_relevant_conversations(self, query: str) -> List[Dict]:
        """Rechercher des conversations pertinentes avec scoring intelligent"""
        if not self.storage:
            return []
        
        try:
            # Rechercher dans les conversations passées
            result = search_past_conversations(query, limit=5)
            data = json.loads(result)
            
            if data.get("status") == "success":
                conversations = data.get("results", [])
                # Filtrer les conversations très pertinentes (score > 0.5)
                relevant = [conv for conv in conversations if conv.get('score', 0) > 0.5]
                return relevant
            else:
                print(f"⚠️ Erreur recherche conversations: {data.get('message')}")
                return []
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {e}")
            return []
    
    def _search_memories(self, query: str) -> List[Dict]:
        """Rechercher dans les mémoires avec scoring intelligent"""
        if not self.storage:
            return []
        
        try:
            result = search_memories(query, limit=5)
            data = json.loads(result)
            
            if data.get("status") == "success":
                memories = data.get("results", [])
                # Filtrer les mémoires très pertinentes (score > 0.3)
                relevant = [mem for mem in memories if mem.get('similarity_score', 0) > 0.3]
                return relevant
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
    
    def _generate_intelligent_response(self, user_message: str) -> str:
        """Générer une réponse intelligente avec contexte complet"""
        if not self.mistral:
            return "❌ Mistral n'est pas configuré. Veuillez configurer MISTRAL_API_KEY."
        
        print("🔍 Recherche de contexte pertinent...")
        
        # 1. Rechercher des conversations pertinentes
        relevant_conversations = self._search_relevant_conversations(user_message)
        
        # 2. Rechercher des mémoires pertinentes
        relevant_memories = self._search_memories(user_message)
        
        # 3. Construire le contexte intelligent
        context_parts = []
        
        if relevant_conversations:
            context_parts.append("📚 CONVERSATIONS PERTINENTES:")
            for i, conv in enumerate(relevant_conversations, 1):
                context_parts.append(f"\n--- Conversation {i} (Score: {conv.get('score', 0):.3f}) ---")
                context_parts.append(f"Résumé: {conv.get('summary', 'N/A')}")
                context_parts.append(f"Date: {conv.get('timestamp', 'N/A')}")
        
        if relevant_memories:
            context_parts.append("\n💾 MÉMOIRES PERTINENTES:")
            for i, mem in enumerate(relevant_memories, 1):
                context_parts.append(f"\n--- Mémoire {i} (Score: {mem.get('similarity_score', 0):.3f}) ---")
                context_parts.append(f"Contenu: {mem.get('content', 'N/A')}")
                context_parts.append(f"Catégorie: {mem.get('category', 'N/A')}")
        
        # 4. Récupérer les détails de la conversation la plus pertinente
        detailed_context = ""
        if relevant_conversations:
            best_conv = max(relevant_conversations, key=lambda x: x.get('score', 0))
            if best_conv.get('score', 0) > 0.7:
                print(f"📖 Récupération des détails de la conversation {best_conv.get('chat_id')}...")
                full_transcript = self._get_full_conversation(best_conv.get('chat_id'))
                if full_transcript:
                    detailed_context = f"\n📖 DÉTAILS DE LA CONVERSATION LA PLUS PERTINENTE:\n{full_transcript}\n"
        
        # 5. Construire le prompt final avec contexte
        context = "\n".join(context_parts) if context_parts else "Aucun contexte pertinent trouvé."
        
        system_prompt = f"""Tu es un assistant IA expert avec accès à une mémoire collective et aux conversations passées.

CONTEXTE DISPONIBLE:
{context}
{detailed_context}

HISTORIQUE DE LA CONVERSATION ACTUELLE:
{self._get_conversation_summary()}

INSTRUCTIONS:
- Utilise TOUT le contexte fourni pour répondre de manière pertinente et précise
- Si tu trouves des informations utiles dans les conversations/mémoires, cite-les clairement
- Si l'utilisateur pose une question spécifique, cherche dans le contexte et réponds avec des détails
- Si tu ajoutes de nouvelles informations importantes, mentionne-le
- Sois naturel, utile et précis en utilisant toutes les informations disponibles
- Réponds en français de manière conversationnelle

Réponds de manière naturelle et utile."""

        try:
            # Appel à Mistral avec le contexte complet
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
    
    def _get_conversation_summary(self) -> str:
        """Obtenir un résumé de la conversation actuelle"""
        if len(self.conversation_history) <= 1:
            return "Conversation récemment démarrée."
        
        # Prendre les 3 derniers échanges
        recent_messages = self.conversation_history[-6:]  # 3 échanges = 6 messages
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
    
    def _finalize_conversation(self) -> str:
        """Finaliser et sauvegarder la conversation"""
        if not self.conversation_id or not self.conversation_history:
            return "Aucune conversation à finaliser"
        
        try:
            # Utiliser la fonction existante pour finaliser
            result = end_chat_and_summarize(self.conversation_id)
            data = json.loads(result)
            
            if data.get("status") == "success":
                summary = data.get("summary", "Résumé non disponible")
                print(f"\n📝 RÉSUMÉ FINAL DE LA CONVERSATION:")
                print(f"{summary}")
                print(f"\n💾 Conversation sauvegardée avec l'ID: {self.conversation_id}")
                return summary
            else:
                print(f"⚠️ Erreur lors de la finalisation: {data.get('message')}")
                return "Erreur lors de la finalisation"
        except Exception as e:
            print(f"❌ Erreur lors de la finalisation: {e}")
            return "Erreur lors de la finalisation"
    
    def chat_loop(self):
        """Boucle principale du chat avancé"""
        if not self.mistral:
            print("❌ Impossible de démarrer le chat: Mistral non configuré")
            return
        
        print("🚀 Démarrage du chat avancé...")
        self.start_conversation()
        
        while True:
            try:
                # Lire l'entrée utilisateur
                user_input = input("\n👤 Vous: ").strip()
                
                # Commandes spéciales
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Finalisation de la conversation...")
                    self._finalize_conversation()
                    break
                
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                elif user_input.lower() == 'summary':
                    auto_summary = self._auto_summarize()
                    if auto_summary:
                        print(f"\n📝 RÉSUMÉ AUTOMATIQUE:\n{auto_summary}")
                    else:
                        print("⚠️ Impossible de générer un résumé automatique")
                    continue
                
                elif user_input.lower() == 'memories':
                    self._show_memories()
                    continue
                
                elif user_input.lower() == 'search':
                    self._interactive_search()
                    continue
                
                elif not user_input:
                    continue
                
                # Ajouter le message utilisateur à l'historique
                self.conversation_history.append({"role": "user", "content": user_input})
                
                # Générer la réponse intelligente
                print("\n🤖 Assistant: ", end="", flush=True)
                response = self._generate_intelligent_response(user_input)
                print(response)
                
                # Ajouter la réponse à l'historique
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Résumation automatique si nécessaire
                if len(self.conversation_history) % (self.summary_threshold * 2) == 0:  # *2 car user + assistant
                    print("\n🔄 Résumation automatique en cours...")
                    auto_summary = self._auto_summarize()
                    if auto_summary:
                        print(f"📝 Résumé: {auto_summary}")
                
                # Ajouter automatiquement des informations importantes à la mémoire
                if any(keyword in user_input.lower() for keyword in ['important', 'souviens-toi', 'note', 'décision', 'solution', 'bug', 'problème']):
                    print("💾 Ajout automatique à la mémoire...")
                    self._add_memory(user_input, category="important")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interruption détectée...")
                self._finalize_conversation()
                break
            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                continue
    
    def _show_help(self):
        """Afficher l'aide"""
        print("\n📚 COMMANDES DISPONIBLES:")
        print("  help     - Afficher cette aide")
        print("  summary  - Résumé automatique de la conversation actuelle")
        print("  memories - Afficher les mémoires récentes")
        print("  search   - Recherche interactive")
        print("  quit     - Quitter le chat")
        print("\n🤖 FONCTIONNALITÉS AUTOMATIQUES:")
        print("  - Résumation automatique tous les 3 échanges")
        print("  - Recherche intelligente dans les conversations passées")
        print("  - Recherche dans les mémoires avec scoring")
        print("  - Récupération des détails des conversations pertinentes")
        print("  - Ajout automatique des informations importantes")
        print("  - Sauvegarde complète à la fin")
    
    def _show_memories(self):
        """Afficher les mémoires"""
        try:
            result = list_memories()
            data = json.loads(result)
            
            if data.get("status") == "success":
                memories = data.get("memories", [])
                print(f"\n💾 MÉMOIRES ({len(memories)} trouvées):")
                for i, mem in enumerate(memories[:10], 1):
                    print(f"\n{i}. {mem.get('content', 'N/A')[:100]}...")
                    print(f"   Catégorie: {mem.get('category', 'N/A')}")
                    print(f"   Date: {mem.get('timestamp', 'N/A')}")
            else:
                print(f"⚠️ Erreur: {data.get('message')}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    def _interactive_search(self):
        """Recherche interactive avancée"""
        query = input("🔍 Terme de recherche: ").strip()
        if not query:
            return
        
        print(f"\n🔍 Recherche intelligente de: '{query}'")
        
        # Rechercher dans les conversations
        conversations = self._search_relevant_conversations(query)
        if conversations:
            print(f"\n📚 CONVERSATIONS PERTINENTES ({len(conversations)}):")
            for i, conv in enumerate(conversations, 1):
                print(f"\n{i}. Score: {conv.get('score', 0):.3f}")
                print(f"   Résumé: {conv.get('summary', 'N/A')[:200]}...")
                print(f"   Date: {conv.get('timestamp', 'N/A')}")
                
                # Proposer de voir les détails
                if conv.get('score', 0) > 0.7:
                    choice = input(f"   Voir les détails de la conversation {i}? (y/n): ").lower()
                    if choice == 'y':
                        full_transcript = self._get_full_conversation(conv.get('chat_id'))
                        if full_transcript:
                            print(f"\n📖 DÉTAILS COMPLETS:\n{full_transcript[:500]}...")
        
        # Rechercher dans les mémoires
        memories = self._search_memories(query)
        if memories:
            print(f"\n💾 MÉMOIRES PERTINENTES ({len(memories)}):")
            for i, mem in enumerate(memories, 1):
                print(f"\n{i}. Score: {mem.get('similarity_score', 0):.3f}")
                print(f"   Contenu: {mem.get('content', 'N/A')[:200]}...")
                print(f"   Catégorie: {mem.get('category', 'N/A')}")

def main():
    """Fonction principale"""
    print("🧠 Chat Avancé avec Mistral - Version Complète")
    print("=" * 60)
    
    # Vérifier la configuration
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        print("⚠️ ATTENTION: Mistral n'est pas configuré!")
        print("   Configurez MISTRAL_API_KEY dans votre fichier .env")
        print("   Le chat fonctionnera en mode limité")
        print()
    
    # Créer et démarrer le chat
    chat = AdvancedChat()
    chat.chat_loop()

if __name__ == "__main__":
    main()
