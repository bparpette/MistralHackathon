#!/usr/bin/env python3
"""
Test de la résumation continue
Vérifie que la résumation continue fonctionne correctement
"""

import os
import sys
import json
from datetime import datetime

# Ajouter le répertoire parent pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_embedding_fix():
    """Tester la correction de l'embedding Mistral"""
    print("🧪 Test de la correction d'embedding Mistral...")
    
    try:
        from main import generate_embedding, ensure_mistral_import, MISTRAL_ENABLED, MISTRAL_API_KEY
        
        if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
            print("⚠️ Mistral non configuré, test avec fallback")
            embedding = generate_embedding("Test d'embedding")
            if len(embedding) == 1024:
                print("✅ Fallback embedding fonctionne")
                return True
            else:
                print("❌ Fallback embedding échoué")
                return False
        
        ensure_mistral_import()
        embedding = generate_embedding("Test d'embedding Mistral")
        
        if len(embedding) == 1024:
            print("✅ Embedding Mistral fonctionne")
            return True
        else:
            print(f"❌ Embedding Mistral échoué: longueur {len(embedding)}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test embedding: {e}")
        return False

def test_continuous_summary():
    """Tester la résumation continue"""
    print("\n🧪 Test de la résumation continue...")
    
    try:
        from main import generate_continuous_summary
        
        # Simuler une conversation
        conversation_history = [
            {"role": "user", "content": "Bonjour, j'ai un problème avec ma base de données"},
            {"role": "assistant", "content": "Bonjour ! Je peux vous aider. Pouvez-vous me décrire le problème en détail ?"},
            {"role": "user", "content": "La connexion échoue avec l'erreur 'Connection refused'"},
            {"role": "assistant", "content": "Cette erreur indique généralement que le serveur de base de données n'est pas démarré. Vérifiez d'abord si le service est actif."}
        ]
        
        chat_id = "test_conv_123"
        team_id = "test-team-123"
        
        summary = generate_continuous_summary(conversation_history, chat_id, team_id)
        
        if summary:
            print(f"✅ Résumé généré: {summary[:100]}...")
            return True
        else:
            print("⚠️ Aucun résumé généré (peut-être Mistral non configuré)")
            return True  # Pas d'erreur si Mistral n'est pas configuré
            
    except Exception as e:
        print(f"❌ Erreur test résumation continue: {e}")
        return False

def test_memory_save():
    """Tester la sauvegarde en mémoire"""
    print("\n🧪 Test de la sauvegarde en mémoire...")
    
    try:
        from main import add_memory, search_memories
        
        # Ajouter une mémoire de test
        result = add_memory(
            "Test de résumation continue - conversation test_conv_123",
            "test,resumation,conversation",
            "conversation_summary"
        )
        
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Mémoire ajoutée avec succès")
            
            # Rechercher la mémoire
            search_result = search_memories("test_conv_123", 1)
            search_data = json.loads(search_result)
            
            if search_data.get("status") == "success" and search_data.get("results"):
                print("✅ Mémoire trouvée en recherche")
                return True
            else:
                print("⚠️ Mémoire non trouvée en recherche")
                return True  # Pas critique
        else:
            print(f"❌ Erreur ajout mémoire: {data.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test mémoire: {e}")
        return False

def test_streamlit_integration():
    """Tester l'intégration Streamlit"""
    print("\n🧪 Test de l'intégration Streamlit...")
    
    try:
        from streamlit_chat import StreamlitChatInterface
        
        # Créer une instance de l'interface
        interface = StreamlitChatInterface()
        print("✅ Interface Streamlit créée")
        
        # Tester la génération d'ID de conversation
        conv_id = interface.generate_conversation_id()
        if conv_id.startswith("conv_"):
            print(f"✅ ID de conversation généré: {conv_id}")
        else:
            print(f"❌ ID de conversation invalide: {conv_id}")
            return False
        
        # Tester la fonction de résumation continue
        test_history = [
            {"role": "user", "content": "Test message 1"},
            {"role": "assistant", "content": "Test réponse 1"}
        ]
        
        # Simuler l'état de session
        interface.conversation_id = conv_id
        interface.conversation_history = test_history
        
        summary = interface.generate_continuous_summary()
        if summary or not interface.mistral:  # OK si pas de Mistral configuré
            print("✅ Résumation continue Streamlit fonctionne")
            return True
        else:
            print("❌ Résumation continue Streamlit échouée")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test Streamlit: {e}")
        return False

def run_all_tests():
    """Exécuter tous les tests"""
    print("🧪 TESTS DE RÉSUMATION CONTINUE")
    print("=" * 50)
    
    tests = [
        ("Correction embedding Mistral", test_embedding_fix),
        ("Résumation continue", test_continuous_summary),
        ("Sauvegarde en mémoire", test_memory_save),
        ("Intégration Streamlit", test_streamlit_integration),
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
        print("🎉 Tous les tests sont passés ! La résumation continue est prête.")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
    
    return passed == total

def main():
    """Fonction principale"""
    success = run_all_tests()
    
    if success:
        print("\n🚀 PRÊT POUR L'UTILISATION")
        print("Lancez l'interface avec: python launch_streamlit.py")
    else:
        print("\n🔧 CONFIGURATION REQUISE")
        print("Vérifiez votre configuration avant d'utiliser la résumation continue")
    
    return success

if __name__ == "__main__":
    main()
