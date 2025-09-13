#!/usr/bin/env python3
"""
Script de test pour mesurer les temps de connexion Qdrant
Permet d'identifier si le problème vient de la connexion réseau
"""

import time
import os
import sys
from datetime import datetime

def test_qdrant_connection():
    """Test complet de la connexion Qdrant avec mesure de temps"""
    
    print("🔍 Test de connexion Qdrant - Mesure des temps")
    print("=" * 50)
    
    # Configuration
    QDRANT_URL = "https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333"
    QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.dTojrUAcLmujBlbrJyQ_oILGXQcWVhF7B8sOTWiIyLw"
    
    print(f"📍 URL: {QDRANT_URL}")
    print(f"🔑 API Key: {'***' + QDRANT_API_KEY[-10:] if QDRANT_API_KEY else 'None'}")
    print()
    
    # Test 1: Import des modules
    print("📦 Test 1: Import des modules Qdrant")
    start_time = time.time()
    
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        import_time = time.time() - start_time
        print(f"✅ Import réussi en {import_time:.3f}s")
    except ImportError as e:
        print(f"❌ Erreur import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False
    
    # Test 2: Création du client
    print("\n🔌 Test 2: Création du client Qdrant")
    start_time = time.time()
    
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30  # Timeout généreux pour le test
        )
        client_time = time.time() - start_time
        print(f"✅ Client créé en {client_time:.3f}s")
    except Exception as e:
        print(f"❌ Erreur création client: {e}")
        return False
    
    # Test 3: Test de connexion (ping)
    print("\n🌐 Test 3: Test de connexion réseau")
    start_time = time.time()
    
    try:
        # Test simple de connexion
        collections = client.get_collections()
        ping_time = time.time() - start_time
        print(f"✅ Connexion réussie en {ping_time:.3f}s")
        print(f"   Collections trouvées: {len(collections.collections)}")
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return False
    
    # Test 4: Création/accès à la collection
    print("\n🗂️ Test 4: Gestion de la collection")
    start_time = time.time()
    
    collection_name = "test_collection"
    try:
        # Vérifier si la collection existe
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if collection_name not in collection_names:
            print(f"   Création de la collection '{collection_name}'...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"✅ Collection créée")
        else:
            print(f"✅ Collection '{collection_name}' existe déjà")
        
        collection_time = time.time() - start_time
        print(f"   Temps total: {collection_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Erreur collection: {e}")
        return False
    
    # Test 5: Insertion d'un point de test
    print("\n📝 Test 5: Insertion d'un point de test")
    start_time = time.time()
    
    try:
        # Créer un point de test
        test_point = PointStruct(
            id="test_point_1",
            vector=[0.1] * 384,  # Vecteur simple
            payload={"content": "Test de connexion", "timestamp": datetime.now().isoformat()}
        )
        
        client.upsert(
            collection_name=collection_name,
            points=[test_point]
        )
        
        insert_time = time.time() - start_time
        print(f"✅ Point inséré en {insert_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Erreur insertion: {e}")
        return False
    
    # Test 6: Recherche
    print("\n🔍 Test 6: Recherche")
    start_time = time.time()
    
    try:
        results = client.search(
            collection_name=collection_name,
            query_vector=[0.1] * 384,
            limit=1
        )
        
        search_time = time.time() - start_time
        print(f"✅ Recherche réussie en {search_time:.3f}s")
        print(f"   Résultats trouvés: {len(results)}")
        
    except Exception as e:
        print(f"❌ Erreur recherche: {e}")
        return False
    
    # Test 7: Nettoyage
    print("\n🧹 Test 7: Nettoyage")
    start_time = time.time()
    
    try:
        client.delete_collection(collection_name)
        cleanup_time = time.time() - start_time
        print(f"✅ Collection supprimée en {cleanup_time:.3f}s")
        
    except Exception as e:
        print(f"⚠️ Erreur nettoyage: {e}")
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TEMPS")
    print("=" * 50)
    print(f"Import modules:     {import_time:.3f}s")
    print(f"Création client:    {client_time:.3f}s")
    print(f"Connexion réseau:   {ping_time:.3f}s")
    print(f"Gestion collection: {collection_time:.3f}s")
    print(f"Insertion point:    {insert_time:.3f}s")
    print(f"Recherche:          {search_time:.3f}s")
    print(f"Nettoyage:          {cleanup_time:.3f}s")
    
    total_time = import_time + client_time + ping_time + collection_time + insert_time + search_time + cleanup_time
    print(f"\n⏱️ TEMPS TOTAL: {total_time:.3f}s")
    
    # Analyse
    print("\n🔍 ANALYSE")
    print("=" * 50)
    if total_time > 10:
        print("❌ PROBLÈME: Temps total > 10s - Risque de timeout Lambda")
    elif ping_time > 5:
        print("⚠️ ATTENTION: Connexion réseau lente (>5s)")
    elif import_time > 2:
        print("⚠️ ATTENTION: Import des modules lent (>2s)")
    else:
        print("✅ OK: Temps de connexion acceptables")
    
    if ping_time > 3:
        print("💡 SUGGESTION: Réduire le timeout Qdrant à 5s maximum")
    
    return True

def test_network_only():
    """Test rapide de connectivité réseau"""
    print("\n🌐 Test de connectivité réseau rapide")
    print("-" * 30)
    
    import socket
    import urllib.parse
    
    url = "https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333"
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 443
    
    print(f"Test de connexion à {host}:{port}")
    
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        connect_time = time.time() - start_time
        
        if result == 0:
            print(f"✅ Connexion TCP réussie en {connect_time:.3f}s")
        else:
            print(f"❌ Connexion TCP échouée (code: {result})")
            
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du test Qdrant")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test de connectivité réseau
    test_network_only()
    
    # Test complet Qdrant
    success = test_qdrant_connection()
    
    if success:
        print("\n🎉 Test terminé avec succès!")
    else:
        print("\n💥 Test échoué!")
        sys.exit(1)
