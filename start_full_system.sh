#!/bin/bash

# Script pour démarrer le système complet : Qdrant + Serveur MCP
echo "🚀 Démarrage du système complet : Qdrant + Serveur MCP"
echo "====================================================="

# Fonction pour vérifier si un port est utilisé
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port utilisé
    else
        return 1  # Port libre
    fi
}

# Fonction pour attendre qu'un service soit prêt
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Attente que le service soit prêt..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo "✅ Service prêt !"
            return 0
        fi
        echo "   Tentative $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    echo "❌ Service non disponible après $max_attempts tentatives"
    return 1
}

# Vérifier si Qdrant est déjà en cours d'exécution
if check_port 6333; then
    echo "✅ Qdrant est déjà en cours d'exécution sur le port 6333"
else
    echo "📦 Démarrage de Qdrant..."
    ./start_qdrant.sh
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors du démarrage de Qdrant"
        exit 1
    fi
    
    # Attendre que Qdrant soit prêt
    wait_for_service "http://localhost:6333/health"
    if [ $? -ne 0 ]; then
        echo "❌ Qdrant n'est pas prêt"
        exit 1
    fi
fi

# Vérifier si le serveur MCP est déjà en cours d'exécution
if check_port 3000; then
    echo "✅ Le serveur MCP est déjà en cours d'exécution sur le port 3000"
else
    echo "🔧 Démarrage du serveur MCP..."
    
    # Activer l'environnement virtuel si disponible
    if [ -f "venv/bin/activate" ]; then
        echo "🐍 Activation de l'environnement virtuel..."
        source venv/bin/activate
    elif [ -f ".venv/bin/activate" ]; then
        echo "🐍 Activation de l'environnement virtuel..."
        source .venv/bin/activate
    fi
    
    # Démarrer le serveur MCP en arrière-plan
    echo "🚀 Lancement du serveur MCP..."
    python main.py &
    MCP_PID=$!
    
    # Attendre que le serveur MCP soit prêt
    wait_for_service "http://localhost:3000/health"
    if [ $? -ne 0 ]; then
        echo "❌ Le serveur MCP n'est pas prêt"
        kill $MCP_PID 2>/dev/null
        exit 1
    fi
    
    echo "✅ Serveur MCP démarré avec PID: $MCP_PID"
fi

echo ""
echo "🎉 Système complet démarré avec succès !"
echo ""
echo "🔗 URLs utiles:"
echo "   - Qdrant Dashboard: http://localhost:6333/dashboard"
echo "   - Serveur MCP: http://localhost:3000"
echo "   - Health Check: http://localhost:3000/health"
echo ""
echo "🧪 Pour tester le système:"
echo "   python test_chat_system.py"
echo ""
echo "🛑 Pour arrêter le système:"
echo "   - Qdrant: docker stop qdrant-local"
echo "   - Serveur MCP: kill $MCP_PID (ou Ctrl+C si en premier plan)"
echo ""

# Garder le script en vie pour pouvoir arrêter les services
echo "Appuyez sur Ctrl+C pour arrêter tous les services..."
trap 'echo "🛑 Arrêt des services..."; docker stop qdrant-local 2>/dev/null; kill $MCP_PID 2>/dev/null; exit 0' INT

# Attendre indéfiniment
while true; do
    sleep 1
done
