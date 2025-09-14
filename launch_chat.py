#!/usr/bin/env python3
"""
Lanceur de Chat Mistral - Interface simple pour choisir le type de chat
"""

import os
import sys
from datetime import datetime

def check_environment():
    """Vérifier l'environnement et la configuration"""
    print("🔧 Vérification de l'environnement...")
    
    # Vérifier les fichiers de configuration
    config_files = ['.env', 'config.env', 'config.local.env', 'config.lambda-optimized.env']
    config_found = False
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Configuration trouvée: {config_file}")
            config_found = True
            break
    
    if not config_found:
        print("⚠️ Aucun fichier de configuration trouvé")
        print("   Créez un fichier .env avec vos clés API")
    
    # Vérifier les dépendances
    try:
        import mistralai
        print("✅ Mistral AI disponible")
    except ImportError:
        print("❌ Mistral AI non installé")
        print("   Installez avec: pip install mistralai")
    
    try:
        from qdrant_client import QdrantClient
        print("✅ Qdrant disponible")
    except ImportError:
        print("❌ Qdrant non installé")
        print("   Installez avec: pip install qdrant-client")
    
    try:
        import requests
        print("✅ Requests disponible")
    except ImportError:
        print("❌ Requests non installé")
        print("   Installez avec: pip install requests")
    
    print()

def show_menu():
    """Afficher le menu principal"""
    print("🧠 CHAT MISTRAL - MENU PRINCIPAL")
    print("=" * 50)
    print("1. Chat Simple - Fonctionnalités de base")
    print("2. Chat Avancé - Résumation automatique + recherche intelligente")
    print("3. Vérifier la configuration")
    print("4. Tester les services")
    print("5. Quitter")
    print("=" * 50)

def test_services():
    """Tester les services disponibles"""
    print("\n🧪 Test des services...")
    
    try:
        # Tester l'import de main
        from main import MISTRAL_ENABLED, MISTRAL_API_KEY, get_storage
        print(f"✅ Import main.py réussi")
        print(f"   Mistral activé: {MISTRAL_ENABLED}")
        print(f"   Clé Mistral: {'✅' if MISTRAL_API_KEY else '❌'}")
        
        # Tester le stockage
        storage = get_storage()
        if storage:
            print("✅ Stockage vectoriel disponible")
        else:
            print("⚠️ Stockage vectoriel non disponible")
        
        # Tester Mistral
        if MISTRAL_ENABLED and MISTRAL_API_KEY:
            try:
                from mistralai import Mistral
                mistral = Mistral(api_key=MISTRAL_API_KEY)
                print("✅ Connexion Mistral réussie")
            except Exception as e:
                print(f"❌ Erreur connexion Mistral: {e}")
        else:
            print("⚠️ Mistral non configuré")
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
    
    input("\nAppuyez sur Entrée pour continuer...")

def launch_simple_chat():
    """Lancer le chat simple"""
    try:
        print("\n🚀 Lancement du Chat Simple...")
        from simple_chat import SimpleChat
        
        chat = SimpleChat()
        chat.chat_loop()
    except Exception as e:
        print(f"❌ Erreur lors du lancement du chat simple: {e}")
        input("Appuyez sur Entrée pour continuer...")

def launch_advanced_chat():
    """Lancer le chat avancé"""
    try:
        print("\n🚀 Lancement du Chat Avancé...")
        from advanced_chat import AdvancedChat
        
        chat = AdvancedChat()
        chat.chat_loop()
    except Exception as e:
        print(f"❌ Erreur lors du lancement du chat avancé: {e}")
        input("Appuyez sur Entrée pour continuer...")

def main():
    """Fonction principale"""
    print("🎯 Lanceur de Chat Mistral")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Vérifier l'environnement au démarrage
    check_environment()
    
    while True:
        try:
            show_menu()
            choice = input("\nVotre choix (1-5): ").strip()
            
            if choice == '1':
                launch_simple_chat()
            elif choice == '2':
                launch_advanced_chat()
            elif choice == '3':
                check_environment()
            elif choice == '4':
                test_services()
            elif choice == '5':
                print("\n👋 Au revoir !")
                break
            else:
                print("❌ Choix invalide. Veuillez choisir entre 1 et 5.")
                input("Appuyez sur Entrée pour continuer...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interruption détectée. Au revoir !")
            break
        except Exception as e:
            print(f"\n❌ Erreur inattendue: {e}")
            input("Appuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()
