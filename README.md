# 🧠 Collective Brain MCP Server

Système de mémoire collective pour équipes - Un cerveau partagé qui permet aux équipes de stocker, rechercher et partager leurs connaissances de manière intelligente.

## 🎯 Concept

Transformez votre équipe en un cerveau collectif où chaque membre peut :
- **Stocker** des informations importantes (décisions, solutions, bugs, etc.)
- **Rechercher** dans la mémoire collective de l'équipe
- **Partager** le contexte instantanément
- **Vérifier** et valider les informations

## 🚀 Fonctionnalités

### Outils MCP disponibles :

1. **`store_memory`** - Stocker une mémoire collective
   - Contenu, catégorie, tags, visibilité
   - Détection automatique de l'importance
   - Liens avec des mémoires similaires

2. **`search_memories`** - Recherche sémantique
   - Recherche par similarité de contenu
   - Filtres par catégorie et visibilité
   - Respect des permissions (private/team/public)

3. **`get_team_insights`** - Analytics d'équipe
   - Top catégories et tags
   - Contributeurs les plus actifs
   - Mémoires les plus consultées

4. **`verify_memory`** - Validation collaborative
   - Permettre aux membres de confirmer des infos
   - Augmenter le score de confiance

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Le Chat A     │    │   Le Chat B      │    │   Le Chat C     │
│   (CEO Alice)   │    │   (CTO Bob)      │    │   (CS Charlie)  │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   Collective Brain MCP    │
                    │   - Store Memories        │
                    │   - Search & Retrieve     │
                    │   - Team Insights         │
                    │   - Verify & Validate     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      Qdrant Vector DB     │
                    │   - Semantic Search       │
                    │   - Embeddings Storage    │
                    │   - Workspace Isolation   │
                    └───────────────────────────┘
```

## 🛠️ Installation

1. **Installer les dépendances :**
```bash
uv sync
```

2. **Déploiement automatique :**
Le serveur se déploie automatiquement à chaque commit sur la branche `main`.

3. **Configuration des clés API :**
Configurez vos clés API directement sur la plateforme de déploiement :
- `QDRANT_URL` - URL de votre cluster Qdrant
- `QDRANT_API_KEY` - Clé API Qdrant  
- `MISTRAL_API_KEY` - Clé API Mistral
- `DEFAULT_WORKSPACE` - Workspace par défaut

## 🎬 Démonstration

Lancez le scénario de démo :
```bash
python demo_scenario.py
```

**Scénario :** Une startup AI résout un bug critique en 45 minutes au lieu de 2h grâce au partage d'information instantané.

## 📊 Cas d'usage

### 1. **Résolution de problèmes**
- CS reçoit une plainte client → stocke dans la mémoire collective
- CTO cherche le contexte → trouve immédiatement l'impact business
- CEO voit la priorité → tout le monde est aligné

### 2. **Prise de décisions**
- Décisions documentées et traçables
- Contexte historique accessible
- Validation collaborative

### 3. **Onboarding**
- Nouveaux membres accèdent à l'historique
- Connaissances préservées
- Meilleures pratiques partagées

## 🔧 Configuration

### Variables d'environnement :
- `QDRANT_URL` - URL de votre cluster Qdrant
- `QDRANT_API_KEY` - Clé API Qdrant
- `MISTRAL_API_KEY` - Clé API Mistral (pour embeddings)
- `DEFAULT_WORKSPACE` - Workspace par défaut

### Permissions :
- **`private`** - Seul le créateur peut voir
- **`team`** - Tous les membres du workspace
- **`public`** - Accessible à tous

## 🎯 Roadmap

### Phase 1 (MVP) ✅
- [x] Stockage de mémoires
- [x] Recherche sémantique
- [x] Système de permissions
- [x] Analytics d'équipe

### Phase 2 (Améliorations)
- [ ] Intégration Qdrant réelle
- [ ] Embeddings Mistral
- [ ] Knowledge graph
- [ ] Dashboard web

### Phase 3 (Avancé)
- [ ] Multi-langue
- [ ] Voice notes
- [ ] Predictive insights
- [ ] API REST

## 🏆 Avantages concurrentiels

1. **Multi-tenant** - Isolation par workspace
2. **Permissions granulaires** - Contrôle fin de l'accès
3. **Recherche sémantique** - Trouve même avec des mots différents
4. **Validation collaborative** - Crowdsourcing de la vérité
5. **Analytics temps réel** - Insights sur l'activité équipe

## 🤝 Contribution

Ce projet a été développé lors du **Mistral AI MCP Hackathon 2025**.

## 📄 Licence

MIT License - Voir le fichier LICENSE pour plus de détails.