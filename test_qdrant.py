#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion à Qdrant
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def test_qdrant_connection():
    """Tester la connexion à Qdrant"""
    
    print("🧪 Test de connexion à Qdrant")
    print("=" * 40)
    
    # Configuration
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name = "test_collection"
    
    try:
        # Connexion
        print(f"🔗 Connexion à {qdrant_url}...")
        client = QdrantClient(url=qdrant_url)
        
        # Test de ping
        print("📡 Test de ping...")
        info = client.get_collections()
        print(f"✅ Connexion réussie! Collections existantes: {len(info.collections)}")
        
        # Créer une collection de test
        print(f"📦 Création de la collection '{collection_name}'...")
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )
            print("✅ Collection créée avec succès")
        except Exception as e:
            if "already exists" in str(e):
                print("ℹ️ Collection existe déjà")
            else:
                raise e
        
        # Test d'insertion
        print("📝 Test d'insertion de données...")
        test_point = PointStruct(
            id=1,
            vector=[0.1] * 384,  # Vecteur de test
            payload={
                "content": "Test de connexion Qdrant",
                "user_id": "test_user",
                "workspace_id": "test_workspace",
                "category": "test",
                "timestamp": "2024-01-01T00:00:00"
            }
        )
        
        client.upsert(
            collection_name=collection_name,
            points=[test_point]
        )
        print("✅ Données insérées avec succès")
        
        # Test de recherche
        print("🔍 Test de recherche...")
        results = client.search(
            collection_name=collection_name,
            query_vector=[0.1] * 384,
            limit=1
        )
        
        if results:
            print(f"✅ Recherche réussie! Résultat: {results[0].payload['content']}")
        else:
            print("⚠️ Aucun résultat trouvé")
        
        # Nettoyage
        print("🧹 Nettoyage...")
        client.delete_collection(collection_name=collection_name)
        print("✅ Collection de test supprimée")
        
        print("\n🎉 Tous les tests sont passés!")
        print("✅ Qdrant est prêt à être utilisé avec votre serveur MCP")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n🔧 Solutions possibles:")
        print("   1. Vérifiez que Qdrant est démarré: ./start_qdrant.sh")
        print("   2. Vérifiez l'URL: export QDRANT_URL=http://localhost:6333")
        print("   3. Vérifiez que Docker est en cours d'exécution")
        return False

if __name__ == "__main__":
    success = test_qdrant_connection()
    sys.exit(0 if success else 1)
