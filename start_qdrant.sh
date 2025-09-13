#!/bin/bash

# Script pour lancer Qdrant en local pour le développement

echo "🚀 Démarrage de Qdrant en local pour le développement"
echo "=================================================="

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Installez Docker d'abord:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Vérifier si Docker est en cours d'exécution
if ! docker info &> /dev/null; then
    echo "❌ Docker n'est pas en cours d'exécution. Démarrez Docker d'abord."
    exit 1
fi

echo "📦 Téléchargement de l'image Qdrant..."
docker pull qdrant/qdrant

echo "🔧 Lancement du conteneur Qdrant..."
echo "   - Port: 6333 (HTTP)"
echo "   - Port: 6334 (gRPC)"
echo "   - Interface web: http://localhost:6333/dashboard"

# Lancer Qdrant avec persistance des données
docker run -d \
  --name qdrant-local \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant

echo ""
echo "✅ Qdrant démarré avec succès!"
echo ""
echo "🔗 URLs utiles:"
echo "   - API HTTP: http://localhost:6333"
echo "   - Interface web: http://localhost:6333/dashboard"
echo "   - API gRPC: localhost:6334"
echo ""
echo "📝 Configuration pour votre serveur MCP:"
echo "   export QDRANT_URL=http://localhost:6333"
echo ""
echo "🛑 Pour arrêter Qdrant:"
echo "   docker stop qdrant-local"
echo "   docker rm qdrant-local"
echo ""
echo "🧹 Pour nettoyer les données:"
echo "   rm -rf qdrant_storage"
