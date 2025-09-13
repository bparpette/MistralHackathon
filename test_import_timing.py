#!/usr/bin/env python3
"""
Script de test pour mesurer les temps d'import des modules
Identifie les modules lents à charger
"""

import time
import sys
from datetime import datetime

def test_import_time(module_name, import_statement):
    """Test le temps d'import d'un module"""
    start_time = time.time()
    try:
        exec(import_statement)
        import_time = time.time() - start_time
        print(f"✅ {module_name}: {import_time:.3f}s")
        return import_time
    except ImportError as e:
        import_time = time.time() - start_time
        print(f"❌ {module_name}: {import_time:.3f}s (ImportError: {e})")
        return None
    except Exception as e:
        import_time = time.time() - start_time
        print(f"❌ {module_name}: {import_time:.3f}s (Erreur: {e})")
        return None

def test_all_imports():
    """Test tous les imports du main.py"""
    print("📦 Test des temps d'import des modules")
    print("=" * 50)
    
    imports = [
        ("os", "import os"),
        ("hashlib", "import hashlib"),
        ("json", "import json"),
        ("datetime", "from datetime import datetime"),
        ("typing", "from typing import List, Dict, Optional"),
        ("pydantic", "from pydantic import Field, BaseModel"),
        ("mcp.server.fastmcp", "from mcp.server.fastmcp import FastMCP"),
        ("qdrant_client", "from qdrant_client import QdrantClient"),
        ("qdrant_client.models", "from qdrant_client.models import Distance, VectorParams, PointStruct"),
    ]
    
    total_time = 0
    successful_imports = 0
    
    for module_name, import_statement in imports:
        import_time = test_import_time(module_name, import_statement)
        if import_time is not None:
            total_time += import_time
            successful_imports += 1
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES IMPORTS")
    print("=" * 50)
    print(f"Modules importés avec succès: {successful_imports}/{len(imports)}")
    print(f"Temps total d'import: {total_time:.3f}s")
    
    if total_time > 5:
        print("❌ PROBLÈME: Temps d'import total > 5s")
    elif total_time > 2:
        print("⚠️ ATTENTION: Temps d'import total > 2s")
    else:
        print("✅ OK: Temps d'import acceptable")
    
    return total_time

def test_fastmcp_creation():
    """Test la création de FastMCP"""
    print("\n🚀 Test de création FastMCP")
    print("-" * 30)
    
    try:
        # Test d'import d'abord
        start_time = time.time()
        from mcp.server.fastmcp import FastMCP
        import_time = time.time() - start_time
        print(f"Import FastMCP: {import_time:.3f}s")
        
        # Test de création
        start_time = time.time()
        mcp = FastMCP("Test Server", port=3000, stateless_http=True, debug=False)
        creation_time = time.time() - start_time
        print(f"Création FastMCP: {creation_time:.3f}s")
        
        total_time = import_time + creation_time
        print(f"Total FastMCP: {total_time:.3f}s")
        
        if total_time > 3:
            print("❌ PROBLÈME: FastMCP prend trop de temps")
        elif total_time > 1:
            print("⚠️ ATTENTION: FastMCP prend du temps")
        else:
            print("✅ OK: FastMCP rapide")
        
        return total_time
        
    except ImportError as e:
        print(f"❌ FastMCP non disponible: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur FastMCP: {e}")
        return None

def test_qdrant_import():
    """Test l'import de Qdrant"""
    print("\n🔗 Test d'import Qdrant")
    print("-" * 30)
    
    try:
        start_time = time.time()
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        import_time = time.time() - start_time
        print(f"Import Qdrant: {import_time:.3f}s")
        
        if import_time > 2:
            print("❌ PROBLÈME: Import Qdrant très lent")
        elif import_time > 1:
            print("⚠️ ATTENTION: Import Qdrant lent")
        else:
            print("✅ OK: Import Qdrant rapide")
        
        return import_time
        
    except ImportError as e:
        print(f"❌ Qdrant non disponible: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur Qdrant: {e}")
        return None

def analyze_startup_time():
    """Analyse le temps de démarrage total"""
    print("\n" + "=" * 50)
    print("🔍 ANALYSE DU TEMPS DE DÉMARRAGE")
    print("=" * 50)
    
    # Test des imports
    import_time = test_all_imports()
    
    # Test FastMCP
    fastmcp_time = test_fastmcp_creation()
    
    # Test Qdrant
    qdrant_time = test_qdrant_import()
    
    # Calcul du temps total estimé
    total_estimated = 0
    if import_time:
        total_estimated += import_time
    if fastmcp_time:
        total_estimated += fastmcp_time
    if qdrant_time:
        total_estimated += qdrant_time
    
    print(f"\n⏱️ TEMPS TOTAL ESTIMÉ: {total_estimated:.3f}s")
    
    # Analyse
    if total_estimated > 10:
        print("❌ PROBLÈME MAJEUR: Temps de démarrage > 10s")
        print("   Risque élevé de timeout Lambda")
    elif total_estimated > 5:
        print("⚠️ PROBLÈME: Temps de démarrage > 5s")
        print("   Risque de timeout Lambda")
    elif total_estimated > 2:
        print("⚠️ ATTENTION: Temps de démarrage > 2s")
        print("   Optimisation recommandée")
    else:
        print("✅ OK: Temps de démarrage acceptable")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS:")
    print("-" * 30)
    
    if qdrant_time and qdrant_time > 1:
        print("• Utiliser l'import paresseux pour Qdrant")
    
    if fastmcp_time and fastmcp_time > 1:
        print("• Optimiser la création de FastMCP")
        print("• Considérer un mode de démarrage minimal")
    
    if total_estimated > 5:
        print("• Implémenter un démarrage en deux phases")
        print("• Initialiser les composants lourds à la première utilisation")
        print("• Utiliser des timeouts courts pour les connexions externes")

if __name__ == "__main__":
    print("🚀 Test des temps d'import et de démarrage")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version}")
    print("=" * 50)
    
    analyze_startup_time()
    
    print("\n🎯 CONCLUSION:")
    print("=" * 50)
    print("Ce test identifie les modules lents à importer.")
    print("Si les temps sont élevés, c'est probablement la cause")
    print("du timeout de démarrage Lambda.")
