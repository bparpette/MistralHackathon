#!/usr/bin/env python3
"""
Lanceur pour l'interface Streamlit avec logs IA en temps réel
"""

import subprocess
import sys
import os
import time

def check_dependencies():
    """Vérifier les dépendances"""
    try:
        import streamlit
        print("✅ Streamlit disponible")
        return True
    except ImportError:
        print("❌ Streamlit non installé")
        return False

def launch_streamlit_with_logs():
    """Lancer Streamlit avec les logs IA"""
    print("🚀 Lancement de l'interface Streamlit avec logs IA")
    print("=" * 60)
    
    if not check_dependencies():
        print("📦 Installation des dépendances...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_streamlit.txt"])
    
    print("🌐 Interface accessible à: http://localhost:8501")
    print("🤖 Logs IA en temps réel dans la barre latérale")
    print("=" * 60)
    
    try:
        # Lancer Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_chat.py",
            "--server.port", "8501",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'interface")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    launch_streamlit_with_logs()
