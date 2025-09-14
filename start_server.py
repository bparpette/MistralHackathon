python run.py#!/usr/bin/env python3
"""
Script de démarrage du MCP Collective Brain
Configure l'environnement et démarre le serveur
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Configurer l'environnement de développement"""
    print("🔧 Configuration de l'environnement...")
    
    # Vérifier si .env existe
    if not os.path.exists('.env'):
        if os.path.exists('config.local.env'):
            print("📋 Copie de la configuration locale...")
            subprocess.run(['cp', 'config.local.env', '.env'])
            print("✅ Fichier .env créé")
        elif os.path.exists('config.lambda-optimized.env'):
            print("📋 Copie de la configuration de base...")
            subprocess.run(['cp', 'config.lambda-optimized.env', '.env'])
            print("✅ Fichier .env créé")
        else:
            print("⚠️ Aucun fichier de configuration trouvé")
            print("📝 Créez un fichier .env avec vos clés API")
    
    # Vérifier les variables d'environnement critiques
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Variables manquantes: {', '.join(missing_vars)}")
        print("📝 Ajoutez-les dans le fichier .env")
        return False
    
    print("✅ Configuration validée")
    return True

def install_dependencies():
    """Installer les dépendances"""
    print("📦 Installation des dépendances...")
    
    try:
        # Essayer uv d'abord
        result = subprocess.run(['uv', 'sync'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dépendances installées avec uv")
            return True
    except FileNotFoundError:
        print("⚠️ uv non trouvé, tentative avec pip...")
    
    try:
        # Fallback vers pip
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dépendances installées avec pip")
            return True
        else:
            print(f"❌ Erreur pip: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Erreur installation: {e}")
        return False

def start_mcp_server():
    """Démarrer le serveur MCP"""
    print("🚀 Démarrage du serveur MCP Collective Brain...")
    
    try:
        # Démarrer le serveur
        subprocess.run([sys.executable, 'main.py'])
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt du serveur demandé")
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")

def main():
    """Fonction principale"""
    print("🧠 MCP Collective Brain - Démarrage")
    print("=" * 40)
    
    # 1. Configurer l'environnement
    if not setup_environment():
        print("\n❌ Configuration échouée")
        print("📖 Consultez TESTING_GUIDE.md pour la configuration")
        return False
    
    # 2. Installer les dépendances
    if not install_dependencies():
        print("\n❌ Installation des dépendances échouée")
        return False
    
    # 3. Démarrer le serveur
    print("\n🎯 Serveur prêt à démarrer")
    print("💡 Appuyez sur Ctrl+C pour arrêter")
    print("=" * 40)
    
    start_mcp_server()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
