#!/usr/bin/env python3
"""
Script de démarrage simple du MCP Collective Brain
"""

import sys
import os

def main():
    print("🧠 MCP Collective Brain - Démarrage")
    print("=" * 40)
    
    # Vérifier les dépendances
    try:
        import mcp
        print("✅ MCP disponible")
    except ImportError:
        print("❌ MCP non installé")
        print("Installez avec: pip install mcp")
        return False
    
    # Démarrer le serveur
    print("🚀 Démarrage du serveur...")
    try:
        from main import initialize_mcp
        mcp = initialize_mcp()
        
        if mcp:
            print("✅ Serveur MCP initialisé")
            print("🎯 Prêt à recevoir des requêtes")
            print("💡 Utilisez les outils MCP pour interagir")
            print("\n📋 Outils disponibles:")
            print("  - store_memory")
            print("  - search_memories") 
            print("  - get_team_insights")
            print("  - record_conversation_message")
            print("  - get_conversation_summary")
            print("  - list_team_conversations")
            print("  - generate_conversation_insights")
            
            # Démarrer le serveur
            mcp.run(transport="streamable-http")
        else:
            print("❌ Impossible d'initialiser MCP")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt du serveur")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
