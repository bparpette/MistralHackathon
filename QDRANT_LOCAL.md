# 🚀 Guide Qdrant Local pour le Développement

## Démarrage rapide

### 1. Lancer Qdrant en local
```bash
./start_qdrant.sh
```

### 2. Tester la connexion
```bash
export QDRANT_URL=http://localhost:6333
uv run python test_qdrant.py
```

### 3. Lancer votre serveur MCP avec Qdrant
```bash
export QDRANT_URL=http://localhost:6333
uv run main.py
```

## URLs utiles

- **API HTTP** : http://localhost:6333
- **Interface web** : http://localhost:6333/dashboard
- **API gRPC** : localhost:6334

## Commandes utiles

### Arrêter Qdrant
```bash
docker stop qdrant-local
docker rm qdrant-local
```

### Voir les logs
```bash
docker logs qdrant-local
```

### Nettoyer les données
```bash
rm -rf qdrant_storage
```

## Avantages du développement local

✅ **Rapide** - Pas de latence réseau  
✅ **Gratuit** - Pas de coûts cloud  
✅ **Offline** - Fonctionne sans internet  
✅ **Debug** - Logs et monitoring locaux  
✅ **Test** - Données de test isolées  

## Configuration automatique

Le serveur MCP détecte automatiquement si Qdrant est disponible :

- Si `QDRANT_URL` est défini → Utilise Qdrant
- Sinon → Utilise le stockage en mémoire (fallback)

## Persistance des données

Les données sont stockées dans le dossier `qdrant_storage/` et persistent entre les redémarrages.

## Interface web

Accédez à http://localhost:6333/dashboard pour :
- Voir les collections
- Explorer les données
- Tester les requêtes
- Monitorer les performances
