#!/usr/bin/env python3
"""
Lanceur pour l'interface Streamlit
"""

import subprocess
import sys
import os

def check_streamlit():
    """Vérifier si Streamlit est installé"""
    try:
        import streamlit
        print("✅ Streamlit disponible")
        return True
    except ImportError:
        print("❌ Streamlit non installé")
        return False

def install_requirements():
    """Installer les dépendances"""
    print("🔧 Installation des dépendances...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_streamlit.txt"])
        print("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur installation: {e}")
        return False

def launch_streamlit():
    """Lancer l'interface Streamlit"""
    print("🚀 Lancement de l'interface Streamlit...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_chat.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'interface Streamlit")
    except Exception as e:
        print(f"❌ Erreur lancement: {e}")

def main():
    """Fonction principale"""
    print("🧠 Lanceur Interface Streamlit - Chat Mistral")
    print("=" * 50)
    
    # Vérifier Streamlit
    if not check_streamlit():
        print("📦 Installation de Streamlit...")
        if not install_requirements():
            print("❌ Impossible d'installer les dépendances")
            return
    
    # Lancer l'interface
    launch_streamlit()

if __name__ == "__main__":
    main()
