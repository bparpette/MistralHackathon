#!/usr/bin/env python3
"""
Test de démarrage ultra-rapide pour Lambda
Simule le démarrage du serveur MCP avec initialisation paresseuse complète
"""

import os
import time
import sys

# Simuler l'environnement Lambda
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-function"
os.environ["QDRANT_ENABLED"] = "true"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-key"

def test_ultra_fast_startup():
    """Test du temps de démarrage ultra-rapide"""
    start_time = time.time()
    
    try:
        # Importer le module principal
        import main
        
        # Vérifier que les variables sont bien configurées
        print(f"✅ Qdrant configuré: {main.USE_QDRANT}")
        print(f"✅ Supabase configuré: {bool(main.SUPABASE_SERVICE_KEY)}")
        print(f"✅ Mode Lambda: {main.IS_LAMBDA}")
        
        # Test de l'initialisation paresseuse
        print("🔄 Test initialisation paresseuse Supabase...")
        supabase_available = main.init_supabase_lazy()
        print(f"✅ Supabase disponible: {supabase_available}")
        
        # Test de création du serveur MCP minimal
        print("🔄 Test création serveur MCP minimal...")
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("Collective Brain Server", port=3000, stateless_http=True, debug=False)
        print("✅ Serveur MCP minimal créé")
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        print(f"⏱️ Temps de démarrage: {startup_time:.3f}s")
        
        if startup_time < 1:
            print("🎯 EXCELLENT: Démarrage < 1s")
        elif startup_time < 2:
            print("✅ TRÈS BON: Démarrage < 2s")
        elif startup_time < 5:
            print("✅ BON: Démarrage < 5s")
        else:
            print("⚠️ LENT: Démarrage > 5s")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Test de démarrage Lambda ultra-rapide...")
    success = test_ultra_fast_startup()
    sys.exit(0 if success else 1)
