#!/usr/bin/env python3
"""
Interface Streamlit pour le Chat Mistral
Interface visuelle avec sélection de conversations et fonctionnalités avancées
"""

import streamlit as st
import os
import sys
import json
import hashlib
import random
import string
from datetime import datetime
from typing import Dict, List, Optional
import time
import io
import contextlib

# Ajouter le répertoire parent pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importer toutes les fonctions du main.py
from main import (
    verify_user_token, extract_token_from_headers,
    ensure_mistral_import, generate_embedding, get_storage,
    chat_with_mistral, end_chat_and_summarize,
    search_past_conversations, get_full_transcript,
    add_memory, search_memories, list_memories,
    MISTRAL_ENABLED, MISTRAL_API_KEY, IS_LAMBDA,
    set_ai_logs_callback
)

# Configuration de la page
st.set_page_config(
    page_title="🧠 Chat Mistral - Interface Visuelle",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

class StreamlitChatInterface:
    """Interface Streamlit pour le chat Mistral"""
    
    def __init__(self):
        self.initialize_session_state()
        self.initialize_services()
    
    def initialize_session_state(self):
        """Initialiser l'état de la session Streamlit"""
        if 'conversations' not in st.session_state:
            st.session_state.conversations = {}
        
        if 'current_conversation_id' not in st.session_state:
            st.session_state.current_conversation_id = None
        
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
        
        # Mapping des utilisateurs
        if 'user_mapping' not in st.session_state:
            st.session_state.user_mapping = {
                "baptiste": {
                    "user_id": "user_baptiste_test",
                    "team_id": "team-shared-global",
                    "user_name": "Baptiste",
                    "display_name": "👨‍💻 Baptiste"
                },
                "henri": {
                    "user_id": "user_henri_test", 
                    "team_id": "team-shared-global",
                    "user_name": "Henri",
                    "display_name": "👨‍🎓 Henri"
                }
            }
        
        if 'current_user' not in st.session_state:
            st.session_state.current_user = "henri"  # Utilisateur par défaut
        
        if 'user_info' not in st.session_state:
            self.update_user_info()
        
        if 'mistral' not in st.session_state:
            st.session_state.mistral = None
        
        if 'storage' not in st.session_state:
            st.session_state.storage = None
        
        # Système de logs en temps réel
        if 'ai_logs' not in st.session_state:
            st.session_state.ai_logs = []
        
        if 'show_ai_logs' not in st.session_state:
            st.session_state.show_ai_logs = True
    
    def update_user_info(self):
        """Mettre à jour les informations utilisateur selon l'utilisateur sélectionné"""
        current_user_key = st.session_state.current_user
        user_data = st.session_state.user_mapping[current_user_key]
        
        st.session_state.user_info = {
            "user_id": user_data["user_id"],
            "team_id": user_data["team_id"], 
            "user_name": user_data["user_name"]
        }
        
        # Réinitialiser l'historique de conversation lors du changement d'utilisateur
        st.session_state.conversation_history = []
        st.session_state.current_conversation_id = None
    
    def initialize_services(self):
        """Initialiser les services"""
        # Configurer le callback pour les logs IA
        set_ai_logs_callback(self.add_ai_log)
        
        # Initialiser Mistral
        ensure_mistral_import()
        if MISTRAL_ENABLED and MISTRAL_API_KEY:
            try:
                from mistralai import Mistral
                st.session_state.mistral = Mistral(api_key=MISTRAL_API_KEY)
            except Exception as e:
                st.error(f"Erreur initialisation Mistral: {e}")
        
        # Initialiser le stockage
        st.session_state.storage = get_storage()
    
    def add_ai_log(self, log_type: str, message: str, details: str = ""):
        """Ajouter un log de l'IA"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "type": log_type,
            "message": message,
            "details": details
        }
        st.session_state.ai_logs.append(log_entry)
        
        # Garder seulement les 50 derniers logs
        if len(st.session_state.ai_logs) > 50:
            st.session_state.ai_logs = st.session_state.ai_logs[-50:]
    
    def display_ai_logs(self):
        """Afficher les logs de l'IA dans un panneau latéral"""
        if not st.session_state.show_ai_logs:
            return
        
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🤖 Logs IA en temps réel")
            
            # Bouton pour masquer/afficher
            if st.button("👁️ Masquer les logs"):
                st.session_state.show_ai_logs = False
                st.rerun()
            
            # Bouton pour vider les logs
            if st.button("🗑️ Vider les logs"):
                st.session_state.ai_logs = []
                st.rerun()
            
            # Afficher les logs
            if st.session_state.ai_logs:
                # Créer un conteneur scrollable
                log_container = st.container()
                with log_container:
                    for log in reversed(st.session_state.ai_logs[-20:]):  # Afficher les 20 derniers
                        # Couleur selon le type de log
                        if log["type"] == "thinking":
                            st.markdown(f"🧠 **{log['timestamp']}** - {log['message']}")
                        elif log["type"] == "tool_call":
                            st.markdown(f"🛠️ **{log['timestamp']}** - {log['message']}")
                        elif log["type"] == "portfolio":
                            st.markdown(f"📋 **{log['timestamp']}** - {log['message']}")
                        elif log["type"] == "reminder":
                            st.markdown(f"🔔 **{log['timestamp']}** - {log['message']}")
                        elif log["type"] == "error":
                            st.markdown(f"❌ **{log['timestamp']}** - {log['message']}")
                        elif log["type"] == "success":
                            st.markdown(f"✅ **{log['timestamp']}** - {log['message']}")
                        else:
                            st.markdown(f"ℹ️ **{log['timestamp']}** - {log['message']}")
                        
                        # Afficher les détails si disponibles
                        if log["details"]:
                            with st.expander("Détails", expanded=False):
                                st.code(log["details"], language="json")
            else:
                st.info("Aucun log disponible")
    
    def generate_conversation_id(self) -> str:
        """Générer un ID de conversation aléatoire"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"conv_{timestamp}_{random_suffix}"
    
    def create_sidebar(self):
        """Créer la barre latérale"""
        with st.sidebar:
            st.title("🧠 Chat Mistral")
            st.markdown("---")
            
            # Sélecteur d'utilisateur
            st.subheader("👤 Utilisateur")
            user_options = {
                key: data["display_name"] 
                for key, data in st.session_state.user_mapping.items()
            }
            
            selected_user = st.selectbox(
                "Choisir un utilisateur:",
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x],
                index=list(user_options.keys()).index(st.session_state.current_user),
                key="user_selector"
            )
            
            # Mettre à jour l'utilisateur si changé
            if selected_user != st.session_state.current_user:
                st.session_state.current_user = selected_user
                self.update_user_info()
                st.rerun()
            
            # Afficher les informations de l'utilisateur actuel
            current_user_data = st.session_state.user_mapping[st.session_state.current_user]
            st.info(f"**Connecté en tant que:** {current_user_data['display_name']}")
            st.caption(f"ID: {current_user_data['user_id']}")
            
            st.markdown("---")
            
            # Informations système
            st.subheader("📊 État du système")
            mistral_status = "✅" if st.session_state.mistral else "❌"
            storage_status = "✅" if st.session_state.storage else "❌"
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Mistral", mistral_status)
            with col2:
                st.metric("Stockage", storage_status)
            
            st.markdown("---")
            
            # Gestion des conversations
            st.subheader("💬 Conversations")
            
            # Nouvelle conversation
            if st.button("🆕 Nouvelle conversation", use_container_width=True):
                new_id = self.generate_conversation_id()
                st.session_state.current_conversation_id = new_id
                st.session_state.conversation_history = []
                st.session_state.conversations[new_id] = {
                    "id": new_id,
                    "title": f"Conversation {new_id[-6:]}",
                    "created_at": datetime.now().isoformat(),
                    "messages": []
                }
                st.rerun()
            
            # Liste des conversations existantes
            if st.session_state.conversations:
                st.markdown("**Conversations existantes:**")
                for conv_id, conv_data in st.session_state.conversations.items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(f"💬 {conv_data['title']}", key=f"conv_{conv_id}"):
                            st.session_state.current_conversation_id = conv_id
                            st.session_state.conversation_history = conv_data.get('messages', [])
                            st.rerun()
                    with col2:
                        if st.button("🗑️", key=f"del_{conv_id}", help="Supprimer"):
                            del st.session_state.conversations[conv_id]
                            if st.session_state.current_conversation_id == conv_id:
                                st.session_state.current_conversation_id = None
                                st.session_state.conversation_history = []
                            st.rerun()
            
            st.markdown("---")
            
            # Outils
            st.subheader("🛠️ Outils")
            
            if st.button("💾 Mémoires", use_container_width=True):
                st.session_state.show_memories = True
            
            if st.button("📊 Statistiques", use_container_width=True):
                st.session_state.show_stats = True
    
    def search_relevant_conversations(self, query: str) -> List[Dict]:
        """Rechercher des conversations pertinentes"""
        if not st.session_state.storage:
            return []
        
        try:
            result = search_past_conversations(query, limit=5)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("results", [])
            return []
        except Exception as e:
            st.error(f"Erreur recherche conversations: {e}")
            return []
    
    def search_memories(self, query: str) -> List[Dict]:
        """Rechercher dans les mémoires"""
        if not st.session_state.storage:
            return []
        
        try:
            result = search_memories(query, limit=5)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("results", [])
            return []
        except Exception as e:
            st.error(f"Erreur recherche mémoires: {e}")
            return []
    
    def get_full_conversation(self, chat_id: str) -> Optional[str]:
        """Récupérer une conversation complète"""
        try:
            result = get_full_transcript(chat_id)
            data = json.loads(result)
            
            if data.get("status") == "success":
                return data.get("transcript")
            return None
        except Exception as e:
            st.error(f"Erreur récupération conversation: {e}")
            return None
    
    def add_memory(self, content: str, tags: str = "", category: str = "general"):
        """Ajouter une mémoire"""
        try:
            result = add_memory(content, tags, category)
            data = json.loads(result)
            
            if data.get("status") == "success":
                st.success(f"Mémoire ajoutée: {data.get('message')}")
            else:
                st.error(f"Erreur ajout mémoire: {data.get('message')}")
        except Exception as e:
            st.error(f"Erreur lors de l'ajout de mémoire: {e}")
    
    def generate_response(self, user_message: str) -> str:
        """Générer une réponse avec contexte en utilisant le cerveau principal"""
        if not st.session_state.mistral:
            self.add_ai_log("error", "Mistral non configuré")
            return "❌ Mistral n'est pas configuré. Veuillez configurer MISTRAL_API_KEY."
        
        try:
            # Log du début du processus
            self.add_ai_log("thinking", f"Traitement du message: {user_message[:50]}...")
            
            with st.spinner("🧠 Le modèle réfléchit et utilise ses outils..."):
                # Déléguer toute la logique de recherche et de réponse au cerveau principal
                # Passer les informations utilisateur pour le mode multi-utilisateur
                result = chat_with_mistral(
                    st.session_state.current_conversation_id, 
                    user_message,
                    user_id=st.session_state.user_info["user_id"],
                    team_id=st.session_state.user_info["team_id"]
                )
                data = json.loads(result)

                if data.get("status") == "success":
                    response = data.get("response", "Aucune réponse générée.")
                    self.add_ai_log("success", f"Réponse générée: {response[:50]}...")
                    return response
                else:
                    error_msg = f"❌ Erreur du modèle: {data.get('message', 'Erreur inconnue')}"
                    self.add_ai_log("error", f"Erreur API: {data.get('message', 'Erreur inconnue')}")
                    return error_msg
        
        except Exception as e:
            error_msg = f"❌ Erreur critique: {e}"
            self.add_ai_log("error", f"Exception: {str(e)}")
            st.error(f"Erreur lors de la génération de la réponse: {e}")
            return error_msg
    
    def generate_continuous_summary(self) -> str:
        """Générer un résumé continu de la conversation actuelle"""
        if not st.session_state.mistral or not st.session_state.current_conversation_id:
            return ""
        
        try:
            from main import generate_continuous_summary
            summary = generate_continuous_summary(
                st.session_state.conversation_history,
                st.session_state.current_conversation_id,
                st.session_state.user_info["team_id"]
            )
            return summary
        except Exception as e:
            st.error(f"Erreur génération résumé continu: {e}")
            return ""
    
    def get_conversation_summary(self) -> str:
        """Obtenir un résumé de la conversation actuelle"""
        if st.session_state.current_conversation_id in st.session_state.conversations:
            conv_data = st.session_state.conversations[st.session_state.current_conversation_id]
            if len(conv_data.get('messages', [])) <= 1:
                return "Conversation récemment démarrée."
            
            # Prendre les 3 derniers échanges
            recent_messages = conv_data.get('messages', [])[-6:]
            return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        return ""
    
    def display_chat_interface(self):
        """Afficher l'interface de chat principale"""
        st.title("💬 Chat Mistral - Interface Visuelle")
        
        # Afficher l'ID de conversation actuelle et le résumé
        if st.session_state.current_conversation_id:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📝 Conversation active: `{st.session_state.current_conversation_id}`")
            with col2:
                if st.button("📝 Voir le résumé", help="Afficher le résumé de la conversation"):
                    st.session_state.show_current_summary = True
            
            # Afficher le résumé actuel si demandé
            if st.session_state.get('show_current_summary', False):
                with st.expander("📝 Résumé actuel de la conversation", expanded=True):
                    if st.session_state.current_conversation_id in st.session_state.conversations:
                        summary = st.session_state.conversations[st.session_state.current_conversation_id].get('summary', '')
                        if summary:
                            st.write(summary)
                        else:
                            st.info("Aucun résumé disponible. Le résumé se génère automatiquement à chaque nouveau message.")
                    else:
                        st.info("Aucun résumé disponible.")
                
                if st.button("Fermer le résumé"):
                    st.session_state.show_current_summary = False
                    st.rerun()
        else:
            st.warning("⚠️ Aucune conversation active. Créez une nouvelle conversation dans la barre latérale.")
            return
        
        # Zone de chat
        chat_container = st.container()
        
        with chat_container:
            # Afficher l'historique de la conversation
            for message in st.session_state.conversation_history:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
        
        # Zone de saisie
        if prompt := st.chat_input("Tapez votre message..."):
            st.session_state.conversation_history.append({"role": "user", "content": prompt})
            
            # Générer la réponse en utilisant le cerveau principal
            assistant_response = self.generate_response(prompt)
            st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Mettre à jour la conversation dans l'état
            if st.session_state.current_conversation_id in st.session_state.conversations:
                st.session_state.conversations[st.session_state.current_conversation_id]['messages'] = st.session_state.conversation_history
            
            # Résumation continue à chaque nouveau message
            with st.spinner("📝 Génération du résumé continu..."):
                summary = self.generate_continuous_summary()
                if summary:
                    # Mettre à jour le résumé dans l'état de la conversation
                    if st.session_state.current_conversation_id in st.session_state.conversations:
                        st.session_state.conversations[st.session_state.current_conversation_id]['summary'] = summary
                    
                    # Détecter les références temporelles dans le message
                    from main import detect_time_references
                    time_refs = detect_time_references(prompt)
                    
                    # Afficher le résumé mis à jour
                    with st.expander("📝 Résumé de la conversation (mis à jour)", expanded=False):
                        st.write(summary)
                        
                        # Afficher les références temporelles si trouvées
                        if time_refs:
                            st.write("⏰ **Références temporelles détectées:**")
                            for ref in time_refs:
                                st.write(f"- {ref['description']}")
            
            # Ajouter automatiquement des informations importantes à la mémoire
            if any(keyword in prompt.lower() for keyword in ['important', 'souviens-toi', 'note', 'décision', 'solution', 'bug', 'problème']):
                with st.spinner("💾 Ajout à la mémoire..."):
                    self.add_memory(prompt, category="important")

            st.rerun()

    def display_search_interface(self):
        """Afficher l'interface de recherche"""
        st.title("🔍 Recherche Intelligente")
        
        query = st.text_input("Terme de recherche:", placeholder="Tapez votre recherche...")
        
        if st.button("Rechercher", type="primary"):
            if query:
                with st.spinner("Recherche en cours..."):
                    # Rechercher dans les conversations
                    conversations = self.search_relevant_conversations(query)
                    
                    # Rechercher dans les mémoires
                    memories = self.search_memories(query)
                
                # Afficher les résultats
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"📚 Conversations ({len(conversations)})")
                    if conversations:
                        for i, conv in enumerate(conversations, 1):
                            with st.expander(f"Conversation {i} (Score: {conv.get('score', 0):.3f})"):
                                st.write(f"**Résumé:** {conv.get('summary', 'N/A')}")
                                st.write(f"**Date:** {conv.get('timestamp', 'N/A')}")
                                
                                if st.button(f"Voir les détails", key=f"conv_details_{i}"):
                                    full_transcript = self.get_full_conversation(conv.get('chat_id'))
                                    if full_transcript:
                                        st.text_area("Transcription complète:", full_transcript, height=300)
                    else:
                        st.info("Aucune conversation trouvée")
                
                with col2:
                    st.subheader(f"💾 Mémoires ({len(memories)})")
                    if memories:
                        for i, mem in enumerate(memories, 1):
                            with st.expander(f"Mémoire {i} (Score: {mem.get('similarity_score', 0):.3f})"):
                                st.write(f"**Contenu:** {mem.get('content', 'N/A')}")
                                st.write(f"**Catégorie:** {mem.get('category', 'N/A')}")
                                st.write(f"**Date:** {mem.get('timestamp', 'N/A')}")
                    else:
                        st.info("Aucune mémoire trouvée")
    
    def display_memories_interface(self):
        """Afficher l'interface des mémoires"""
        st.title("💾 Mémoires Collectives")
        
        try:
            # Utiliser les informations utilisateur actuelles
            user_info = st.session_state.user_info
            result = list_memories(
                user_id=user_info["user_id"],
                team_id=user_info["team_id"]
            )
            data = json.loads(result)
            
            if data.get("status") == "success":
                memories = data.get("memories", [])
                st.metric("Total des mémoires", len(memories))
                
                # Filtres
                col1, col2 = st.columns(2)
                with col1:
                    categories = list(set([mem.get('category', 'general') for mem in memories]))
                    selected_category = st.selectbox("Filtrer par catégorie:", ["Toutes"] + categories)
                
                with col2:
                    search_term = st.text_input("Rechercher dans les mémoires:", placeholder="Terme de recherche...")
                
                # Filtrer les mémoires
                filtered_memories = memories
                if selected_category != "Toutes":
                    filtered_memories = [mem for mem in filtered_memories if mem.get('category') == selected_category]
                
                if search_term:
                    filtered_memories = [mem for mem in filtered_memories if search_term.lower() in mem.get('content', '').lower()]
                
                # Afficher les mémoires
                for i, mem in enumerate(filtered_memories, 1):
                    with st.expander(f"Mémoire {i} - {mem.get('category', 'general').title()}"):
                        st.write(f"**Contenu:** {mem.get('content', 'N/A')}")
                        st.write(f"**Tags:** {', '.join(mem.get('tags', []))}")
                        st.write(f"**Confiance:** {mem.get('confidence', 0):.2f}")
                        st.write(f"**Date:** {mem.get('timestamp', 'N/A')}")
            else:
                st.error(f"Erreur: {data.get('message')}")
        except Exception as e:
            st.error(f"Erreur lors du chargement des mémoires: {e}")
    
    def display_stats_interface(self):
        """Afficher l'interface des statistiques"""
        st.title("📊 Statistiques")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Conversations actives", len(st.session_state.conversations))
        
        with col2:
            st.metric("Messages dans la conversation actuelle", len(st.session_state.conversation_history))
        
        with col3:
            st.metric("Mistral configuré", "✅" if st.session_state.mistral else "❌")
        
        # Graphiques
        if st.session_state.conversations:
            st.subheader("📈 Activité des conversations")
            
            # Données pour le graphique
            conv_data = []
            for conv_id, conv_data_item in st.session_state.conversations.items():
                conv_data.append({
                    "ID": conv_id[-6:],
                    "Messages": len(conv_data_item.get('messages', [])),
                    "Créée": conv_data_item.get('created_at', '')[:10]
                })
            
            if conv_data:
                import pandas as pd
                df = pd.DataFrame(conv_data)
                st.bar_chart(df.set_index("ID")["Messages"])
    
    def run(self):
        """Exécuter l'interface"""
        # Créer la barre latérale
        self.create_sidebar()
        
        # Afficher les logs IA
        self.display_ai_logs()
        
        # Afficher l'interface principale
        if st.session_state.get('show_search', False):
            self.display_search_interface()
            if st.button("Retour au chat"):
                st.session_state.show_search = False
                st.rerun()
        elif st.session_state.get('show_memories', False):
            self.display_memories_interface()
            if st.button("Retour au chat"):
                st.session_state.show_memories = False
                st.rerun()
        elif st.session_state.get('show_stats', False):
            self.display_stats_interface()
            if st.button("Retour au chat"):
                st.session_state.show_stats = False
                st.rerun()
        else:
            self.display_chat_interface()

def main():
    """Fonction principale"""
    # Vérifier la configuration
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        st.warning("⚠️ Mistral n'est pas configuré! Configurez MISTRAL_API_KEY dans votre fichier .env")
    
    # Créer et exécuter l'interface
    interface = StreamlitChatInterface()
    interface.run()

if __name__ == "__main__":
    main()
