# 🧪 Guide de Test MCP Inspector avec Qdrant Cloud

## 🚀 **Étape 1: Démarrer le serveur MCP avec Qdrant**

```bash
# Dans votre terminal
export QDRANT_URL="https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333"
export QDRANT_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.dTojrUAcLmujBlbrJyQ_oILGXQcWVhF7B8sOTWiIyLw"
uv run main.py
```

**Résultat attendu :**
```
🔗 Connexion à Qdrant: https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333
✅ Collection 'shared_memories' créée
INFO:     Started server process [XXXXX]
INFO:     Uvicorn running on http://127.0.0.1:3000
```

---

## 🔧 **Étape 2: Configuration MCP Inspector**

### **Paramètres de connexion :**
- **Transport Type:** `Streamable HTTP`
- **URL:** `http://127.0.0.1:3000/mcp`
- **Server Entry:** (vide)
- **Authentication:** None

---

## 🧪 **Étape 3: Tests à effectuer dans MCP Inspector**

### **Test 1: Vérifier les outils disponibles**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```
**Résultat attendu :** 4 outils disponibles
- `add_memory`
- `search_memories`
- `delete_memory`
- `list_memories`

---

### **Test 2: Ajouter une mémoire (Test Qdrant)**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "add_memory",
    "arguments": {
      "content": "Test MCP Inspector avec Qdrant Cloud - mémoire de test pour vérifier la connexion vectorielle",
      "tags": "test,mcp,inspector,qdrant,cloud,vector"
    }
  }
}
```
**Résultat attendu :**
```json
{
  "status": "success",
  "memory_id": "XXXXXXXXXXXXXX",
  "message": "Mémoire ajoutée au bucket partagé (Qdrant)"
}
```
**⚠️ Important :** Le message doit contenir "(Qdrant)" pour confirmer l'utilisation de Qdrant Cloud.

---

### **Test 3: Rechercher la mémoire stockée**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_memories",
    "arguments": {
      "query": "MCP Inspector Qdrant",
      "limit": 5
    }
  }
}
```
**Résultat attendu :**
```json
{
  "status": "success",
  "query": "MCP Inspector Qdrant",
  "results": [
    {
      "memory_id": "XXXXXXXXXXXXXX",
      "content": "Test MCP Inspector avec Qdrant Cloud...",
      "tags": ["test", "mcp", "inspector", "qdrant", "cloud", "vector"],
      "timestamp": "2025-09-13T15:XX:XX.XXXXXX",
      "similarity_score": 0.XXX
    }
  ],
  "total_found": 1
}
```

---

### **Test 4: Lister toutes les mémoires**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "list_memories",
    "arguments": {}
  }
}
```
**Résultat attendu :**
```json
{
  "status": "success",
  "total": 1,
  "memories": [
    {
      "memory_id": "XXXXXXXXXXXXXX",
      "content": "Test MCP Inspector avec Qdrant Cloud...",
      "tags": ["test", "mcp", "inspector", "qdrant", "cloud", "vector"],
      "timestamp": "2025-09-13T15:XX:XX.XXXXXX"
    }
  ]
}
```

---

### **Test 5: Supprimer une mémoire**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "delete_memory",
    "arguments": {
      "memory_id": "MEMORY_ID_FROM_TEST_2"
    }
  }
}
```
**Résultat attendu :**
```json
{
  "status": "success",
  "message": "Mémoire XXXXXXXXXXXXXX supprimée du bucket (Qdrant)"
}
```

---

## ✅ **Critères de succès**

### **Tests réussis si :**
1. ✅ **Connexion Qdrant** - Message "🔗 Connexion à Qdrant" au démarrage
2. ✅ **Collection créée** - Message "✅ Collection 'shared_memories' créée"
3. ✅ **Stockage Qdrant** - Message "Mémoire ajoutée au bucket partagé (Qdrant)"
4. ✅ **Recherche vectorielle** - Résultats avec similarity_score > 0
5. ✅ **Suppression Qdrant** - Message "supprimée du bucket (Qdrant)"

### **Tests échoués si :**
1. ❌ **Pas de connexion Qdrant** - Message "Utilisation du stockage en mémoire"
2. ❌ **Erreur de collection** - Message d'erreur Qdrant
3. ❌ **Stockage mémoire** - Message "Mémoire ajoutée au bucket partagé (mémoire)"
4. ❌ **Pas de résultats** - total_found: 0
5. ❌ **Erreur suppression** - Message d'erreur

---

## 🔍 **Vérifications supplémentaires**

### **Vérifier directement Qdrant Cloud :**
```bash
# Lister les collections
curl -X GET 'https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333/collections' \
  --header 'api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.dTojrUAcLmujBlbrJyQ_oILGXQcWVhF7B8sOTWiIyLw'

# Compter les points dans la collection
curl -X POST 'https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333/collections/shared_memories/points/count' \
  --header 'api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.dTojrUAcLmujBlbrJyQ_oILGXQcWVhF7B8sOTWiIyLw' \
  --header 'Content-Type: application/json' \
  --data '{}'
```

---

## 🚨 **Dépannage**

### **Si MCP Inspector ne se connecte pas :**
- Vérifier que le serveur MCP tourne sur le port 3000
- Utiliser l'URL complète : `http://127.0.0.1:3000/mcp`
- S'assurer que le transport est `Streamable HTTP`

### **Si les tests échouent :**
- Vérifier les variables d'environnement QDRANT_URL et QDRANT_API_KEY
- Vérifier les logs du serveur MCP
- Tester la connexion Qdrant directement avec curl

### **Si la recherche ne trouve rien :**
- Vérifier que la mémoire a bien été stockée
- Attendre quelques secondes après le stockage
- Vérifier les embeddings dans Qdrant

---

## 🎯 **Objectif du test**

Ce test confirme que votre MCP :
1. **Se connecte** à Qdrant Cloud
2. **Stocke** les mémoires dans la base vectorielle
3. **Recherche** avec la similarité vectorielle
4. **Gère** les opérations CRUD complètes
5. **Fonctionne** avec MCP Inspector

Une fois ces tests réussis, votre MCP est prêt pour la production ! 🚀
