#!/usr/bin/env python3
"""
Test de démarrage ultra-rapide pour le mode cloud
"""

import os
import time
import sys

# Simuler l'environnement cloud
os.environ["QDRANT_ENABLED"] = "true"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-key"

def test_cloud_startup():
    """Test du temps de démarrage cloud"""
    start_time = time.time()
    
    try:
        # Importer le module principal
        import main
        
        # Vérifier que les variables sont bien configurées
        print(f"✅ Qdrant configuré: {main.USE_QDRANT}")
        print(f"✅ Supabase configuré: {bool(main.SUPABASE_SERVICE_KEY)}")
        
        # Test de l'initialisation paresseuse
        print("🔄 Test initialisation paresseuse Supabase...")
        supabase_available = main.init_supabase_lazy()
        print(f"✅ Supabase disponible: {supabase_available}")
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        print(f"⏱️ Temps de démarrage: {startup_time:.3f}s")
        
        if startup_time < 0.5:
            print("🎯 EXCELLENT: Démarrage < 0.5s")
        elif startup_time < 1:
            print("✅ TRÈS BON: Démarrage < 1s")
        elif startup_time < 2:
            print("✅ BON: Démarrage < 2s")
        else:
            print("⚠️ LENT: Démarrage > 2s")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Test de démarrage Cloud ultra-rapide...")
    success = test_cloud_startup()
    sys.exit(0 if success else 1)
