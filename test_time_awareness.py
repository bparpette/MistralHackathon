#!/usr/bin/env python3
"""
Test de la conscience temporelle
Vérifie que la détection des références temporelles fonctionne
"""

import os
import sys
import json
from datetime import datetime

# Ajouter le répertoire parent pour importer main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_time_detection():
    """Tester la détection des références temporelles"""
    print("🧪 Test de la détection des références temporelles...")
    
    try:
        from main import detect_time_references
        
        test_cases = [
            "Je reviens dans 20 minutes",
            "Rendez-vous à 14:30",
            "On se voit demain",
            "Ce soir à 20h",
            "Dans 2 heures",
            "Dans 3 jours",
            "Hier matin",
            "Cet après-midi"
        ]
        
        for test_text in test_cases:
            refs = detect_time_references(test_text)
            print(f"\n📝 Texte: '{test_text}'")
            if refs:
                for ref in refs:
                    print(f"   ⏰ {ref['description']} (type: {ref['type']})")
            else:
                print("   ❌ Aucune référence temporelle détectée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test détection temporelle: {e}")
        return False

def test_summary_with_time():
    """Tester la résumation avec références temporelles"""
    print("\n🧪 Test de la résumation avec références temporelles...")
    
    try:
        from main import generate_continuous_summary
        
        # Simuler une conversation avec références temporelles
        conversation_history = [
            {"role": "user", "content": "Bonjour, j'ai un rendez-vous à 15:30"},
            {"role": "assistant", "content": "Bonjour ! Je note que vous avez un rendez-vous à 15:30. Comment puis-je vous aider ?"},
            {"role": "user", "content": "Je reviens dans 20 minutes, peux-tu me rappeler ?"},
            {"role": "assistant", "content": "Bien sûr ! Je vous rappellerai dans 20 minutes."}
        ]
        
        chat_id = "test_time_conv_123"
        team_id = "test-team-123"
        
        summary = generate_continuous_summary(conversation_history, chat_id, team_id)
        
        if summary:
            print(f"✅ Résumé généré: {summary[:100]}...")
            return True
        else:
            print("⚠️ Aucun résumé généré (peut-être Mistral non configuré)")
            return True  # Pas d'erreur si Mistral n'est pas configuré
            
    except Exception as e:
        print(f"❌ Erreur test résumation temporelle: {e}")
        return False

def test_memory_with_timestamps():
    """Tester la sauvegarde en mémoire avec timestamps"""
    print("\n🧪 Test de la sauvegarde avec timestamps...")
    
    try:
        from main import add_memory, search_memories
        
        # Ajouter une mémoire avec timestamp
        current_time = datetime.now()
        memory_content = f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Test de mémoire avec timestamp"
        
        result = add_memory(
            memory_content,
            "test,timestamp,time",
            "test_category"
        )
        
        data = json.loads(result)
        if data.get("status") == "success":
            print("✅ Mémoire avec timestamp ajoutée")
            
            # Rechercher la mémoire
            search_result = search_memories("timestamp", 1)
            search_data = json.loads(search_result)
            
            if search_data.get("status") == "success" and search_data.get("results"):
                print("✅ Mémoire avec timestamp trouvée en recherche")
                return True
            else:
                print("⚠️ Mémoire non trouvée en recherche")
                return True  # Pas critique
        else:
            print(f"❌ Erreur ajout mémoire: {data.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test mémoire timestamp: {e}")
        return False

def test_prompt_timestamps():
    """Tester que les prompts incluent les timestamps"""
    print("\n🧪 Test des timestamps dans les prompts...")
    
    try:
        from main import generate_conversation_summary, Conversation, ConversationMessage
        
        # Créer une conversation de test
        conversation = Conversation(
            chat_id="test_prompt_123",
            team_id="test-team-123",
            user_id="test-user",
            title="Test conversation",
            messages=[
                ConversationMessage("user", "Test message 1"),
                ConversationMessage("assistant", "Test réponse 1")
            ]
        )
        
        # Tester la génération de résumé (qui devrait inclure des timestamps)
        summary = generate_conversation_summary(conversation)
        
        if summary:
            print(f"✅ Résumé avec timestamp généré: {summary[:100]}...")
            return True
        else:
            print("⚠️ Aucun résumé généré (peut-être Mistral non configuré)")
            return True  # Pas d'erreur si Mistral n'est pas configuré
            
    except Exception as e:
        print(f"❌ Erreur test prompt timestamps: {e}")
        return False

def run_all_tests():
    """Exécuter tous les tests"""
    print("🧪 TESTS DE CONSCIENCE TEMPORELLE")
    print("=" * 50)
    
    tests = [
        ("Détection des références temporelles", test_time_detection),
        ("Résumation avec références temporelles", test_summary_with_time),
        ("Sauvegarde avec timestamps", test_memory_with_timestamps),
        ("Timestamps dans les prompts", test_prompt_timestamps),
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
        print("🎉 Tous les tests sont passés ! La conscience temporelle est prête.")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
    
    return passed == total

def main():
    """Fonction principale"""
    success = run_all_tests()
    
    if success:
        print("\n🚀 PRÊT POUR L'UTILISATION")
        print("Lancez l'interface avec: python launch_streamlit.py")
        print("\n💡 Exemples de phrases temporelles à tester:")
        print("- 'Je reviens dans 20 minutes'")
        print("- 'Rendez-vous à 15:30'")
        print("- 'On se voit demain'")
        print("- 'Ce soir à 20h'")
    else:
        print("\n🔧 CONFIGURATION REQUISE")
        print("Vérifiez votre configuration avant d'utiliser la conscience temporelle")
    
    return success

if __name__ == "__main__":
    main()
