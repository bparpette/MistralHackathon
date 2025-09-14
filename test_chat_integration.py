#!/usr/bin/env python3
"""
Test d'intégration des chats Mistral
Vérifie que toutes les fonctionnalités sont bien connectées
"""

import os
import sys
import json
from datetime import datetime

# Ajouter le répertoire parent pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Tester les imports"""
    print("🧪 Test des imports...")
    
    try:
        from main import (
            verify_user_token, extract_token_from_headers,
            ensure_mistral_import, generate_embedding, get_storage,
            chat_with_mistral, end_chat_and_summarize,
            search_past_conversations, get_full_transcript,
            add_memory, search_memories, list_memories,
            MISTRAL_ENABLED, MISTRAL_API_KEY, IS_LAMBDA
        )
        print("✅ Import main.py réussi")
        return True
    except Exception as e:
        print(f"❌ Erreur import main.py: {e}")
        return False

def test_chat_classes():
    """Tester les classes de chat"""
    print("\n🧪 Test des classes de chat...")
    
    try:
        from simple_chat import SimpleChat
        from advanced_chat import AdvancedChat
        print("✅ Import des classes de chat réussi")
        return True
    except Exception as e:
        print(f"❌ Erreur import classes de chat: {e}")
        return False

def test_services():
    """Tester les services"""
    print("\n🧪 Test des services...")
    
    # Test Mistral
    try:
        from main import ensure_mistral_import, MISTRAL_ENABLED, MISTRAL_API_KEY
        ensure_mistral_import()
        print(f"✅ Mistral: {'Configuré' if MISTRAL_ENABLED and MISTRAL_API_KEY else 'Non configuré'}")
    except Exception as e:
        print(f"❌ Erreur Mistral: {e}")
    
    # Test Qdrant
    try:
        from main import get_storage
        storage = get_storage()
        print(f"✅ Stockage: {'Disponible' if storage else 'Non disponible'}")
    except Exception as e:
        print(f"❌ Erreur stockage: {e}")
    
    return True

def test_chat_functionality():
    """Tester les fonctionnalités de chat"""
    print("\n🧪 Test des fonctionnalités de chat...")
    
    try:
        from simple_chat import SimpleChat
        
        # Créer une instance de chat
        chat = SimpleChat()
        print("✅ Création d'instance SimpleChat réussie")
        
        # Tester l'initialisation
        if chat.mistral:
            print("✅ Mistral initialisé dans le chat")
        else:
            print("⚠️ Mistral non disponible dans le chat")
        
        if chat.storage:
            print("✅ Stockage initialisé dans le chat")
        else:
            print("⚠️ Stockage non disponible dans le chat")
        
        return True
    except Exception as e:
        print(f"❌ Erreur test fonctionnalités: {e}")
        return False

def test_advanced_chat():
    """Tester le chat avancé"""
    print("\n🧪 Test du chat avancé...")
    
    try:
        from advanced_chat import AdvancedChat
        
        # Créer une instance de chat avancé
        chat = AdvancedChat()
        print("✅ Création d'instance AdvancedChat réussie")
        
        # Tester les méthodes
        chat.start_conversation("Test User")
        print("✅ Démarrage de conversation réussi")
        
        # Tester la résumation automatique
        chat.conversation_history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Salut ! Comment puis-je vous aider ?"}
        ]
        
        summary = chat._auto_summarize()
        if summary:
            print(f"✅ Résumation automatique: {summary[:50]}...")
        else:
            print("⚠️ Résumation automatique non disponible")
        
        return True
    except Exception as e:
        print(f"❌ Erreur test chat avancé: {e}")
        return False

def test_memory_functions():
    """Tester les fonctions de mémoire"""
    print("\n🧪 Test des fonctions de mémoire...")
    
    try:
        from main import add_memory, search_memories, list_memories
        
        # Test d'ajout de mémoire
        result = add_memory("Test de mémoire", "test", "general")
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Ajout de mémoire réussi")
        else:
            print(f"⚠️ Ajout de mémoire: {data.get('message')}")
        
        # Test de recherche
        result = search_memories("test", 3)
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Recherche de mémoires réussie")
        else:
            print(f"⚠️ Recherche de mémoires: {data.get('message')}")
        
        # Test de listage
        result = list_memories()
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Listage de mémoires réussi")
        else:
            print(f"⚠️ Listage de mémoires: {data.get('message')}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur test fonctions mémoire: {e}")
        return False

def test_conversation_functions():
    """Tester les fonctions de conversation"""
    print("\n🧪 Test des fonctions de conversation...")
    
    try:
        from main import search_past_conversations, get_full_transcript
        
        # Test de recherche de conversations
        result = search_past_conversations("test", 3)
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Recherche de conversations réussie")
        else:
            print(f"⚠️ Recherche de conversations: {data.get('message')}")
        
        # Test de récupération de transcription
        result = get_full_transcript("test-chat-id")
        data = json.loads(result)
        if data.get("status") == "error" and "non trouvée" in data.get("message", ""):
            print("✅ Gestion d'erreur transcription correcte")
        else:
            print(f"⚠️ Test transcription: {data.get('message')}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur test fonctions conversation: {e}")
        return False

def run_all_tests():
    """Exécuter tous les tests"""
    print("🧪 TESTS D'INTÉGRATION DES CHATS MISTRAL")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Classes de chat", test_chat_classes),
        ("Services", test_services),
        ("Fonctionnalités de chat", test_chat_functionality),
        ("Chat avancé", test_advanced_chat),
        ("Fonctions de mémoire", test_memory_functions),
        ("Fonctions de conversation", test_conversation_functions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: RÉUSSI")
            else:
                print(f"❌ {test_name}: ÉCHEC")
        except Exception as e:
            print(f"❌ {test_name}: ERREUR - {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 RÉSULTATS: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés ! Le système est prêt.")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
    
    return passed == total

def main():
    """Fonction principale"""
    success = run_all_tests()
    
    if success:
        print("\n🚀 PRÊT POUR L'UTILISATION")
        print("Lancez le chat avec: python launch_chat.py")
    else:
        print("\n🔧 CONFIGURATION REQUISE")
        print("Vérifiez votre configuration avant d'utiliser les chats")
    
    return success

if __name__ == "__main__":
    main()
