"""
MCP Collective Brain Server - Version multi-tenant optimisée pour Lambda
Système de mémoire collective avec isolation par équipe
"""

import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

# Import paresseux pour optimiser le démarrage Lambda
try:
    import requests
    print("✅ Module requests importé au démarrage")
except ImportError:
    requests = None
    print("❌ Module requests non disponible au démarrage")

# Fallback vers urllib si requests n'est pas disponible
try:
    import urllib.request
    import urllib.parse
    import urllib.error
    import json as json_module
    print("✅ Module urllib disponible comme fallback")
except ImportError:
    print("❌ Module urllib non disponible")

QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None
Mistral = None

# Charger les variables d'environnement depuis .env si disponible
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Charger depuis config.env si .env n'existe pas
elif os.path.exists('config.env'):
    with open('config.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Charger depuis config.lambda-optimized.env si config.env n'existe pas
elif os.path.exists('config.lambda-optimized.env'):
    with open('config.lambda-optimized.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Charger aussi depuis config.env.example si disponible
elif os.path.exists('config.env.example'):
    with open('config.env.example', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://hzoggayzniyxlbwxchcx.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configuration Qdrant - optimisée pour démarrage rapide
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "false").lower() == "true"

# Configuration Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_ENABLED = os.getenv("MISTRAL_ENABLED", "false").lower() == "true"

# Détection environnement Lambda
IS_LAMBDA = (
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None or
    os.getenv("AWS_EXECUTION_ENV") is not None or
    os.getenv("LAMBDA_TASK_ROOT") is not None
)

# Fonction pour déterminer si Qdrant doit être utilisé
def should_use_qdrant():
    """Détermine si Qdrant doit être utilisé"""
    if IS_LAMBDA:
        return False
    
    # Vérifier les variables d'environnement actuelles
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_enabled = os.getenv("QDRANT_ENABLED", "false").lower()
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_enabled == "true":
        if qdrant_url and qdrant_api_key:
            return True  # Qdrant cloud
        elif qdrant_url:
            return True  # Qdrant local avec URL
        else:
            # Qdrant local par défaut
            os.environ["QDRANT_URL"] = "http://localhost:6333"
            os.environ["QDRANT_API_KEY"] = ""
            return True
    else:
        # Essayer Qdrant local par défaut
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["QDRANT_ENABLED"] = "true"
        os.environ["QDRANT_API_KEY"] = ""
        return True

# En Lambda, mode paresseux pour éviter les timeouts
if IS_LAMBDA:
    # En Lambda, on active Qdrant si les credentials sont disponibles
    USE_QDRANT = bool(QDRANT_URL and QDRANT_API_KEY)
    if USE_QDRANT:
        print("🚀 Mode Lambda - Qdrant activé (paresseux)")
    else:
        print("🚀 Mode Lambda - Qdrant désactivé (pas de credentials)")
else:
    # En local, utiliser la logique de should_use_qdrant()
    USE_QDRANT = should_use_qdrant()
    print(f"🔧 Qdrant configuré: URL={QDRANT_URL}, ENABLED={QDRANT_ENABLED}, API_KEY={'***' if QDRANT_API_KEY else 'None'}")

# Debug minimal - seulement en local
if not IS_LAMBDA:
    print(f"🔧 Qdrant: {'Activé' if USE_QDRANT else 'Désactivé'}")
    print(f"🔧 Supabase: {'Activé' if SUPABASE_SERVICE_KEY else 'Désactivé'}")
    print(f"🔧 Mistral: {'Activé' if MISTRAL_ENABLED else 'Désactivé'}")

# Variable globale pour stocker les headers de la requête courante
current_request_headers = {}

# Système de logs en temps réel
ai_logs_callback = None

def set_ai_logs_callback(callback_func):
    """Définir la fonction de callback pour les logs IA"""
    global ai_logs_callback
    ai_logs_callback = callback_func

def add_ai_log(log_type: str, message: str, details: str = ""):
    """Ajouter un log de l'IA"""
    global ai_logs_callback
    if ai_logs_callback:
        ai_logs_callback(log_type, message, details)

def set_request_headers(headers: dict):
    """Définir les headers de la requête courante"""
    global current_request_headers
    current_request_headers = headers

def get_request_headers() -> dict:
    """Récupérer les headers de la requête courante"""
    return current_request_headers

def extract_token_from_headers():
    """Extraire le token Bearer depuis les headers HTTP"""
    try:
        # 1. Essayer de récupérer depuis les headers de la requête courante
        request_headers = get_request_headers()
        print(f"🔍 Headers de la requête: {request_headers}")
        
        if "authorization" in request_headers:
            auth_header = request_headers["authorization"]
            if auth_header.startswith("Bearer "):
                print(f"✅ Token trouvé dans les headers de requête: {auth_header[7:]}")
                return auth_header[7:]  # Enlever "Bearer "
        
        # 2. Debug: afficher tous les headers disponibles dans l'environnement
        print("=== DEBUG HEADERS ENV ===")
        for key, value in os.environ.items():
            if "AUTH" in key.upper() or "HEADER" in key.upper() or "HTTP" in key.upper():
                print(f"{key}: {value}")
        print("========================")
        
        # 3. En Lambda, les headers sont disponibles via les variables d'environnement
        auth_header = os.getenv("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            print(f"✅ Token trouvé dans HTTP_AUTHORIZATION: {auth_header[7:]}")
            return auth_header[7:]  # Enlever "Bearer "
        
        # 4. Fallback: chercher dans d'autres variables d'environnement
        for key, value in os.environ.items():
            if "AUTHORIZATION" in key.upper() and value.startswith("Bearer "):
                print(f"✅ Token trouvé dans {key}: {value[7:]}")
                return value[7:]
        
        print("❌ Aucun token Bearer trouvé")
        return ""
    except Exception as e:
        print(f"❌ Erreur extraction token: {e}")
        return ""

# Configuration globale pour forcer le partage
FORCE_SHARED_TEAM = True
SHARED_TEAM_ID = "team-shared-global"

def get_unified_team_context(user_token=None, user_id=None, team_id=None):
    """
    Fonction centralisée pour obtenir le contexte utilisateur/équipe
    avec une logique cohérente de partage des données
    """
    
    # Mode 1: Paramètres explicites fournis (priorité absolue)
    if user_id and team_id:
        # Forcer l'utilisation de l'équipe partagée si configuré
        if FORCE_SHARED_TEAM:
            team_id = SHARED_TEAM_ID
        return {
            "user_id": user_id,
            "team_id": team_id,
            "user_name": user_id.replace("user_", "").replace("_", " ").title(),
            "mode": "explicit_params"
        }
    
    # Mode 2: Token fourni - vérifier en base
    if user_token and user_token != "test-token":
        user_info = verify_user_token(user_token)
        if user_info:
            return {
                "user_id": user_info["user_id"],
                "team_id": user_info["team_id"],
                "user_name": user_info["user_name"],
                "mode": "database_auth"
            }
    
    # Mode 3: Mode test/développement - MÊME ÉQUIPE POUR TOUS
    # ⚠️ POINT CLÉ: Tous les utilisateurs de test partagent la même équipe
    return {
        "user_id": user_id or "user_test_shared",
        "team_id": "team-shared-global",  # ← ÉQUIPE UNIQUE PARTAGÉE
        "user_name": "Test User",
        "mode": "test_shared"
    }

def enforce_shared_team_if_needed(team_id: str) -> str:
    """
    Force l'utilisation d'une équipe partagée si configuré
    """
    if FORCE_SHARED_TEAM:
        return SHARED_TEAM_ID
    return team_id

# Import paresseux de FastMCP
def get_mcp():
    """Import paresseux de FastMCP - optimisé pour Lambda"""
    try:
        from mcp.server.fastmcp import FastMCP
        # Configuration optimisée pour Lambda
        return FastMCP(
            "Collective Brain Server", 
            port=3000, 
            stateless_http=True, 
            debug=False
        )
    except ImportError:
        if not IS_LAMBDA:
            print("❌ FastMCP non disponible")
        return None

# Modèle de données enrichi pour le cerveau collectif
class Memory:
    def __init__(self, content: str, user_id: str = "", team_id: str = "", 
                 timestamp: str = "", tags: List[str] = [], category: str = "general",
                 visibility: str = "team", confidence: float = 0.5):
        self.content = content
        self.user_id = user_id
        self.team_id = team_id
        self.timestamp = timestamp
        self.tags = tags
        self.category = category
        self.visibility = visibility
        self.confidence = confidence

# Modèle de données pour les conversations
class ConversationMessage:
    def __init__(self, role: str, content: str, timestamp: str = "", user_id: str = ""):
        self.role = role  # "user" ou "assistant"
        self.content = content
        self.timestamp = timestamp
        self.user_id = user_id

class Conversation:
    def __init__(self, chat_id: str, team_id: str = "", user_id: str = "", 
                 title: str = "", created_at: str = "", updated_at: str = "",
                 messages: List[ConversationMessage] = None, summary: str = ""):
        self.chat_id = chat_id
        self.team_id = team_id
        self.user_id = user_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.messages = messages or []
        self.summary = summary

# Stockage en mémoire simple (fallback)
memories: Dict[str, Memory] = {}
conversations: Dict[str, Conversation] = {}

# Import paresseux de Qdrant
QDRANT_AVAILABLE = False
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None

def ensure_qdrant_import():
    """Import paresseux de Qdrant - optimisé pour Lambda"""
    global QDRANT_AVAILABLE, QdrantClient, Distance, VectorParams, PointStruct
    
    if not QDRANT_AVAILABLE and USE_QDRANT:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            QDRANT_AVAILABLE = True
            # Pas de print en Lambda pour éviter les logs
            if not IS_LAMBDA:
                print("✅ Qdrant importé avec succès")
        except ImportError:
            QDRANT_AVAILABLE = False
            if not IS_LAMBDA:
                print("❌ Qdrant non disponible")

def ensure_mistral_import():
    """Import paresseux de Mistral - optimisé pour Lambda"""
    global Mistral
    
    if Mistral is None and MISTRAL_ENABLED and MISTRAL_API_KEY:
        try:
            from mistralai import Mistral
            Mistral = Mistral(api_key=MISTRAL_API_KEY)
            if not IS_LAMBDA:
                print("✅ Mistral importé avec succès")
        except ImportError:
            Mistral = None
            if not IS_LAMBDA:
                print("❌ Mistral non disponible")

def calculate_similarity(text1: str, text2: str) -> float:
    """Calcule la similarité entre deux textes"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return intersection / union if union > 0 else 0.0

def generate_embedding(text: str) -> List[float]:
    """Génère un embedding en utilisant l'API de Mistral."""
    
    # S'assurer que Mistral est disponible
    ensure_mistral_import()
    if not Mistral:
        print("⚠️ Mistral non disponible, fallback vers l'embedding par hash.")
        # Fallback vers l'ancienne méthode si Mistral n'est pas là
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        vector = []
        # La dimension du modèle d'embedding de Mistral est de 1024
        for i in range(1024):
            vector.append((hash_bytes[i % 16] - 128) / 128.0)
        return vector

    try:
        response = Mistral.embeddings.create(
            model="mistral-embed",
            inputs=[text]  # L'API attend une liste de textes
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Erreur lors de la génération de l'embedding Mistral: {e}")
        # Fallback en cas d'erreur de l'API
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        vector = []
        for i in range(1024): # Dimension de mistral-embed
            vector.append((hash_bytes[i % 16] - 128) / 128.0)
        return vector


def generate_conversation_summary(conversation: Conversation) -> str:
    """Génère un résumé de conversation avec Mistral"""
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        # Fallback simple si Mistral n'est pas disponible
        return f"Conversation de {len(conversation.messages)} messages sur {conversation.title or 'sujet non spécifié'}"
    
    try:
        ensure_mistral_import()
        if not Mistral:
            return f"Conversation de {len(conversation.messages)} messages sur {conversation.title or 'sujet non spécifié'}"
        
        # Préparer le contexte de la conversation
        conversation_text = ""
        for msg in conversation.messages:
            role = "Utilisateur" if msg.role == "user" else "Assistant"
            conversation_text += f"{role}: {msg.content}\n"
        
        # Prompt pour le résumé avec timestamp
        current_time = datetime.now()
        prompt = f"""Résumez cette conversation de manière concise et structurée. 
        Identifiez les points clés, décisions importantes, et actions à retenir.
        
        Date et heure actuelle: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
        
        Conversation:
        {conversation_text}
        
        Résumé (max 200 mots):"""
        
        # Appel à l'API Mistral
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Erreur génération résumé Mistral: {e}")
        return f"Conversation de {len(conversation.messages)} messages sur {conversation.title or 'sujet non spécifié'}"

def detect_time_references(text: str) -> List[Dict]:
    """Détecter les références temporelles dans un texte"""
    import re
    from datetime import datetime, timedelta
    
    time_references = []
    current_time = datetime.now()
    
    # Patterns pour détecter les références temporelles
    patterns = [
        (r'dans (\d+) minutes?', 'minutes'),
        (r'dans (\d+) heures?', 'hours'),
        (r'dans (\d+) jours?', 'days'),
        (r'(\d+):(\d+)', 'time'),
        (r'demain', 'tomorrow'),
        (r'hier', 'yesterday'),
        (r'ce soir', 'tonight'),
        (r'cet après-midi', 'afternoon'),
        (r'ce matin', 'morning'),
    ]
    
    for pattern, ref_type in patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            if ref_type == 'minutes':
                minutes = int(match.group(1))
                target_time = current_time + timedelta(minutes=minutes)
                time_references.append({
                    'text': match.group(0),
                    'type': 'relative',
                    'target_time': target_time.isoformat(),
                    'description': f"dans {minutes} minutes ({target_time.strftime('%H:%M')})"
                })
            elif ref_type == 'hours':
                hours = int(match.group(1))
                target_time = current_time + timedelta(hours=hours)
                time_references.append({
                    'text': match.group(0),
                    'type': 'relative',
                    'target_time': target_time.isoformat(),
                    'description': f"dans {hours} heures ({target_time.strftime('%H:%M')})"
                })
            elif ref_type == 'days':
                days = int(match.group(1))
                target_time = current_time + timedelta(days=days)
                time_references.append({
                    'text': match.group(0),
                    'type': 'relative',
                    'target_time': target_time.isoformat(),
                    'description': f"dans {days} jours ({target_time.strftime('%Y-%m-%d')})"
                })
            elif ref_type == 'time':
                hour, minute = int(match.group(1)), int(match.group(2))
                target_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= current_time:
                    target_time += timedelta(days=1)
                time_references.append({
                    'text': match.group(0),
                    'type': 'absolute',
                    'target_time': target_time.isoformat(),
                    'description': f"à {hour:02d}:{minute:02d}"
                })
            else:
                time_references.append({
                    'text': match.group(0),
                    'type': 'relative',
                    'target_time': current_time.isoformat(),
                    'description': match.group(0)
                })
    
    return time_references

def generate_continuous_summary(conversation_history: List[Dict], chat_id: str, team_id: str) -> str:
    """Génère un résumé continu de la conversation et le sauvegarde"""
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        return ""
    
    if len(conversation_history) < 2:
        return ""
    
    try:
        ensure_mistral_import()
        if not Mistral:
            return ""
        
        # Préparer le texte de la conversation avec timestamps
        conversation_text = ""
        current_time = datetime.now()
        
        for i, msg in enumerate(conversation_history):
            role = "Utilisateur" if msg.get('role') == "user" else "Assistant"
            # Simuler un timestamp (dans un vrai système, on aurait des vrais timestamps)
            msg_time = current_time.strftime("%H:%M:%S")
            conversation_text += f"[{msg_time}] {role}: {msg.get('content', '')}\n"
        
        # Prompt pour le résumé continu avec contexte temporel
        prompt = f"""Résumez UNIQUEMENT cette conversation de manière concise et structurée.
        Identifiez les points clés, décisions importantes, et actions à retenir.
        Le résumé doit être factuel et utile pour retrouver les informations plus tard.
        N'incluez QUE le contenu de cette conversation, pas d'autres informations.
        
        Date et heure actuelle: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
        
        Conversation:
        {conversation_text}
        
        Résumé de la conversation uniquement (max 150 mots):"""
        
        # Appel à l'API Mistral
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Détecter les références temporelles dans la conversation
        time_refs = []
        for msg in conversation_history:
            if msg.get('role') == 'user':
                refs = detect_time_references(msg.get('content', ''))
                time_refs.extend(refs)
        
        # Sauvegarder le résumé en mémoire avec timestamp
        if summary:
            try:
                # Ajouter le résumé comme mémoire avec timestamp
                memory_content = f"[{current_time.strftime("%Y-%m-%d %H:%M:%S")}] Résumé de conversation {chat_id}: {summary}"
                
                # Ajouter les références temporelles si trouvées
                if time_refs:
                    time_info = " | Références temporelles: " + ", ".join([ref['description'] for ref in time_refs])
                    memory_content += time_info
                
                add_memory(
                    content=memory_content,
                    tags=f"conversation,resume,{chat_id},{current_time.strftime('%Y%m%d')}",
                    category="conversation_summary"
                )
                print(f"💾 Résumé de conversation sauvegardé: {summary[:50]}...")
                
                # Sauvegarder les références temporelles séparément
                for ref in time_refs:
                    reminder_content = f"[{current_time.strftime("%Y-%m-%d %H:%M:%S")}] Rappel: {ref['description']} - Conversation {chat_id}"
                    add_memory(
                        content=reminder_content,
                        tags=f"rappel,time,{chat_id},{current_time.strftime('%Y%m%d')}",
                        category="reminder"
                    )
                    print(f"⏰ Rappel créé: {ref['description']}")
                    
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde résumé: {e}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Erreur génération résumé continu: {e}")
        return ""

def verify_user_token(user_token: str) -> Optional[Dict]:
    """Vérifier un token utilisateur via Supabase (obligatoire)"""
    print(f"🔍 Début vérification token: {user_token[:10]}...")
    
    # Mode développement : accepter des tokens de test
    if user_token in ["test-token-valid-123", "user_d8a7996df3c777e9ac2914ef16d5b501"]:
        print(f"✅ Token de test accepté (mode développement): {user_token}")
        return {
            "user_id": "user_d8a7996df3c777e9ac2914ef16d5b501",
            "team_id": "test-team-123",
            "user_name": "Test User"
        }
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ Supabase non configuré - authentification obligatoire")
        return None
    
    try:
        # Si c'est un token Bearer, enlever le préfixe
        if user_token.startswith("Bearer "):
            user_token = user_token[7:]
            print(f"🔍 Token nettoyé: {user_token[:10]}...")
        
        print(f"🔍 Appel Supabase: {SUPABASE_URL}/rest/v1/rpc/verify_user_token")
        
        # Utiliser requests si disponible, sinon urllib
        if requests is not None:
            print("🔍 Utilisation de requests")
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/verify_user_token",
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "apikey": SUPABASE_SERVICE_KEY
                },
                json={"token": user_token},
                timeout=3
            )
            status_code = response.status_code
            response_text = response.text
        else:
            print("🔍 Utilisation de urllib (fallback)")
            # Utiliser urllib comme fallback
            data = json.dumps({"token": user_token}).encode('utf-8')
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/rpc/verify_user_token",
                data=data,
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "apikey": SUPABASE_SERVICE_KEY
                }
            )
            response = urllib.request.urlopen(req, timeout=3)
            status_code = response.getcode()
            response_text = response.read().decode('utf-8')
        
        print(f"🔍 Réponse Supabase: {status_code}")
        print(f"🔍 Contenu de la réponse: {response_text}")
        
        if status_code == 200:
            data = json.loads(response_text)
            print(f"🔍 Données reçues: {data}")
            if data and len(data) > 0:
                print(f"✅ Token valide pour utilisateur: {data[0]}")
                return data[0]
        
        print(f"❌ Token invalide: {user_token[:10]}... (status: {status_code})")
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification token: {e}")
        return None

class QdrantStorage:
    """Gestionnaire de stockage Qdrant multi-tenant"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
        self._init_attempted = False
    
    def _ensure_connected(self):
        """Connexion paresseuse avec timeout court"""
        if not self._initialized and not self._init_attempted:
            self._init_attempted = True
            
            # En Lambda, on active Qdrant seulement quand nécessaire
            if IS_LAMBDA and not QDRANT_ENABLED:
                # Vérifier si Qdrant est configuré
                if QDRANT_URL and QDRANT_API_KEY:
                    # Activer Qdrant dynamiquement
                    global USE_QDRANT
                    USE_QDRANT = True
            
            # Import paresseux
            ensure_qdrant_import()
            
            if not QDRANT_AVAILABLE:
                raise Exception("Qdrant non disponible")
            
            try:
                if not IS_LAMBDA:
                    print("🔄 Connexion Qdrant...")
                
                # Connexion Qdrant avec ou sans API key
                if QDRANT_API_KEY:
                    self.client = QdrantClient(
                        url=QDRANT_URL,
                        api_key=QDRANT_API_KEY,
                        timeout=2
                    )
                else:
                    # Qdrant local sans API key
                    self.client = QdrantClient(
                        url=QDRANT_URL,
                        timeout=2
                    )
                self._initialized = True
                if not IS_LAMBDA:
                    print("✅ Qdrant connecté")
            except Exception as e:
                if not IS_LAMBDA:
                    print(f"❌ Erreur Qdrant: {e}")
                self.client = None
                self._initialized = False
                raise Exception(f"Connexion Qdrant échouée: {e}")
        
        if not self._initialized:
            raise Exception("Qdrant non disponible")
    
    def _get_collection_name(self, team_id: str) -> str:
        """Générer le nom de collection pour une équipe"""
        # Nettoyer l'ID d'équipe pour créer un nom de collection valide
        clean_team_id = team_id.replace("-", "_").replace(" ", "_")
        return f"team_memories_{clean_team_id}"
    
    def _get_conversation_collection_name(self, team_id: str) -> str:
        """Générer le nom de la collection de conversations pour une équipe."""
        clean_team_id = team_id.replace("-", "_").replace(" ", "_")
        return f"team_conversations_{clean_team_id}"

    def _ensure_collection_exists(self, team_id: str, collection_type: str = "memories"):
        """S'assurer que la collection de l'équipe existe (paresseux)"""
        if collection_type == "memories":
            collection_name = self._get_collection_name(team_id)
            vector_size = 1024 # Taille Mistral pour toutes les collections
        else: # conversations
            collection_name = self._get_conversation_collection_name(team_id)
            vector_size = 1024 # Nouvelle taille pour les embeddings Mistral
        
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                print(f"✅ Collection '{collection_name}' créée pour l'équipe {team_id}")
            else:
                print(f"✅ Collection '{collection_name}' existe pour l'équipe {team_id}")
                
        except Exception as e:
            print(f"❌ Erreur collection: {e}")
            raise
    
    def store_memory(self, memory: Memory, memory_id: str, team_id: str) -> str:
        """Stocker une mémoire avec isolation par équipe"""
        try:
            self._ensure_connected()
            self._ensure_collection_exists(team_id)
            
            collection_name = self._get_collection_name(team_id)
            embedding = generate_embedding(memory.content)
            
            # Convertir l'ID string en entier pour Qdrant
            point_id = int(memory_id[:8], 16) if len(memory_id) >= 8 else hash(memory_id) % (2**63)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "memory_id": memory_id,  # Garder l'ID original dans le payload
                    "content": memory.content,
                    "timestamp": memory.timestamp,
                    "tags": memory.tags,
                    "user_id": memory.user_id,
                    "team_id": memory.team_id,
                    "category": memory.category,
                    "confidence": memory.confidence
                }
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            return memory_id
            
        except Exception as e:
            print(f"❌ Erreur stockage: {e}")
            raise

    def store_conversation_summary(self, chat_id: str, summary: str, team_id: str, transcript_path: str, message_count: int = 0, auto_tags: str = "") -> bool:
        """Stocker un résumé de conversation dans Qdrant."""
        try:
            self._ensure_connected()
            self._ensure_collection_exists(team_id, collection_type="conversations")

            collection_name = self._get_conversation_collection_name(team_id)
            # L'embedding est fait sur le résumé ET les tags pour une meilleure recherche
            embedding_text = summary + "\n" + auto_tags.replace(",", " ")
            embedding = generate_embedding(embedding_text)

            point_id = hashlib.md5(chat_id.encode()).hexdigest()

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "chat_id": chat_id,
                    "summary": summary,
                    "team_id": team_id,
                    "transcript_path": transcript_path,
                    "timestamp": datetime.now().isoformat(),
                    "message_count": message_count,
                    "duration_minutes": 0,  # Peut être calculé si on stocke les timestamps
                    "conversation_type": "chat_with_mistral",
                    "auto_tags": auto_tags
                }
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            print(f"✅ Résumé pour chat '{chat_id}' stocké dans Qdrant.")
            return True

        except Exception as e:
            print(f"❌ Erreur lors du stockage du résumé de conversation: {e}")
            raise
    
    def search_memories(self, query: str, team_id: str, limit: int = 5) -> List[Dict]:
        """Recherche avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            # Vérifier que la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                print(f"⚠️ Collection {collection_name} n'existe pas encore")
                return []
            
            query_embedding = generate_embedding(query)
            
            search_results = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=limit
            ).points
            
            results = []
            for result in search_results:
                results.append({
                    "memory_id": result.id,
                    "content": result.payload["content"],
                    "tags": result.payload["tags"],
                    "timestamp": result.payload["timestamp"],
                    "user_id": result.payload.get("user_id", "unknown"),
                    "category": result.payload.get("category", "general"),
                    "confidence": result.payload.get("confidence", 0.5),
                    "similarity_score": round(result.score, 3)
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche: {e}")
            return []

    def search_conversation_summaries(self, query: str, team_id: str, limit: int = 3) -> List[Dict]:
        """Recherche sémantique dans les résumés de conversations."""
        try:
            self._ensure_connected()
            collection_name = self._get_conversation_collection_name(team_id)

            # S'assurer que la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            if collection_name not in collection_names:
                print(f"⚠️ La collection de conversations pour l'équipe {team_id} n'existe pas.")
                return []

            query_embedding = generate_embedding(query)

            search_results = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=limit,
                with_payload=True
            ).points

            results = []
            for hit in search_results:
                payload = hit.payload
                results.append({
                    "chat_id": payload.get("chat_id"),
                    "summary": payload.get("summary"),
                    "transcript_path": payload.get("transcript_path"),
                    "timestamp": payload.get("timestamp"),
                    "score": hit.score
                })
            
            return results

        except Exception as e:
            print(f"❌ Erreur lors de la recherche de conversations: {e}")
            return []
    
    def delete_memory(self, memory_id: str, team_id: str) -> bool:
        """Suppression avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=[memory_id]
            )
            return True
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
            return False
    
    def list_memories(self, team_id: str) -> List[Dict]:
        """Listage avec isolation par équipe"""
        try:
            self._ensure_connected()
            collection_name = self._get_collection_name(team_id)
            
            # Vérifier que la collection existe
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                return []
            
            points = self.client.scroll(
                collection_name=collection_name,
                limit=1000
            )[0]
            
            results = []
            for point in points:
                results.append({
                    "memory_id": point.id,
                    "content": point.payload["content"],
                    "tags": point.payload["tags"],
                    "timestamp": point.payload["timestamp"],
                    "user_id": point.payload.get("user_id", "unknown"),
                    "category": point.payload.get("category", "general"),
                    "confidence": point.payload.get("confidence", 0.5)
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur listage: {e}")
            return []

# Initialisation paresseuse du stockage
storage = None

def get_storage():
    """Obtenir l'instance de stockage avec initialisation paresseuse"""
    global storage
    if storage is None:
        # En Lambda, activer Qdrant à la demande si les credentials sont disponibles
        if IS_LAMBDA and QDRANT_URL and QDRANT_API_KEY:
            try:
                print("🔧 Activation de Qdrant en Lambda...")
                storage = QdrantStorage()
                print("✅ Qdrant activé en Lambda")
            except Exception as e:
                print(f"⚠️ Erreur activation Qdrant en Lambda: {e}")
                storage = None
        elif USE_QDRANT:
            try:
                storage = QdrantStorage()
                # Tester la connexion
                storage._ensure_connected()
                if not IS_LAMBDA:
                    print("✅ Stockage Qdrant initialisé")
            except Exception as e:
                if not IS_LAMBDA:
                    print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
                storage = None
        else:
            storage = None
    return storage

# Initialisation paresseuse de MCP
mcp = None

def get_mcp_instance():
    """Obtenir l'instance MCP avec initialisation paresseuse"""
    global mcp
    if mcp is None:
        mcp = get_mcp()
    return mcp

def health_check() -> str:
    """Endpoint de santé pour vérifier l'état du système"""
    try:
        # Vérifier les services
        mistral_status = "✅" if MISTRAL_ENABLED and MISTRAL_API_KEY else "❌"
        qdrant_status = "✅" if USE_QDRANT else "❌"
        supabase_status = "✅" if SUPABASE_SERVICE_KEY else "❌"
        
        # Tester la connexion Qdrant si activé
        qdrant_connected = False
        if USE_QDRANT:
            try:
                storage = get_storage()
                if storage:
                    storage._ensure_connected()
                    qdrant_connected = True
            except:
                qdrant_connected = False
        
        return json.dumps({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "mistral": {
                    "enabled": MISTRAL_ENABLED,
                    "configured": bool(MISTRAL_API_KEY),
                    "status": mistral_status
                },
                "qdrant": {
                    "enabled": USE_QDRANT,
                    "connected": qdrant_connected,
                    "status": "✅" if qdrant_connected else "❌"
                },
                "supabase": {
                    "enabled": bool(SUPABASE_SERVICE_KEY),
                    "status": supabase_status
                }
            },
            "environment": {
                "is_lambda": IS_LAMBDA,
                "active_chats": len(active_chats),
                "memories_count": len(memories),
                "conversations_count": len(conversations)
            }
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        })

# Outils MCP avec authentification
def add_memory(
    content: str,
    tags: str = "",
    category: str = "general",
    visibility: str = "team",
    user_id: str = None,
    team_id: str = None
) -> str:
    """
    Ajouter une mémoire avec logique de team_id unifiée
    """
    
    # Si paramètres non fournis, utiliser la logique unifiée
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"📝 Ajout mémoire - User: {user_id}, Team: {team_id}")
    
    # Générer un ID unique
    memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}{user_id}".encode()).hexdigest()
    
    # Parser les tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Détection automatique de l'importance
    confidence = 0.5
    if any(word in content.lower() for word in ["décision", "important", "critique", "urgent", "bug", "erreur"]):
        confidence = 0.8
    elif any(word in content.lower() for word in ["solution", "résolu", "fix", "correction"]):
        confidence = 0.7
    
    # Détection automatique de catégorie
    if category == "general":
        if any(word in content.lower() for word in ["bug", "erreur", "problème", "issue"]):
            category = "bug"
        elif any(word in content.lower() for word in ["décision", "choix", "stratégie"]):
            category = "decision"
        elif any(word in content.lower() for word in ["feature", "fonctionnalité", "nouveau"]):
            category = "feature"
        elif any(word in content.lower() for word in ["réunion", "meeting", "call"]):
            category = "meeting"
    
    # Créer la mémoire enrichie
    memory = Memory(
        content=content,
        user_id=user_id,
        team_id=team_id,
        timestamp=datetime.now().isoformat(),
        tags=tag_list,
        category=category,
        visibility=visibility,
        confidence=confidence
    )
    
    # Stocker via le système de stockage
    storage = get_storage()
    if storage:
        try:
            storage.store_memory(memory, memory_id, team_id)
            message = f"Mémoire ajoutée au cerveau collectif de l'équipe (Qdrant)"
        except Exception as e:
            if not IS_LAMBDA:
                print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            memories[memory_id] = memory
            message = f"Mémoire ajoutée au cerveau collectif (mémoire - fallback)"
    else:
        memories[memory_id] = memory
        message = f"Mémoire ajoutée au cerveau collectif (mémoire)"
    
    return json.dumps({
        "status": "success",
        "memory_id": memory_id,
        "message": message,
        "user": user_name,
        "team": team_id
    })

def search_memories(
    query: str,
    limit: int = 5,
    user_id: str = None,
    team_id: str = None
) -> str:
    """
    Rechercher dans le cerveau collectif avec logique unifiée
    """
    
    # Si paramètres non fournis, utiliser la logique unifiée
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"🔍 Recherche mémoires - User: {user_id}, Team: {team_id}")
    
    storage = get_storage()
    if storage:
        try:
            results = storage.search_memories(query, team_id, limit)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            results = []
    else:
        results = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not results:
        scored_memories = []
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:  # Isolation par équipe
                similarity = calculate_similarity(query, memory.content)
                scored_memories.append((similarity, memory_id, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        for similarity, memory_id, memory in scored_memories[:limit]:
            if similarity > 0:
                results.append({
                    "memory_id": memory_id,
                    "content": memory.content,
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "user_id": memory.user_id,
                    "category": memory.category,
                    "confidence": memory.confidence,
                    "similarity_score": round(similarity, 3)
                })
    
    return json.dumps({
        "status": "success",
        "query": query,
        "results": results,
        "total_found": len(results),
        "user": user_name,
        "team": team_id
    })

def delete_memory(memory_id: str, user_id: str = None, team_id: str = None) -> str:
    """Supprimer une mémoire du cerveau collectif avec authentification"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    storage = get_storage()
    if storage:
        try:
            success = storage.delete_memory(memory_id, team_id)
            if success:
                return json.dumps({
                    "status": "success",
                    "message": f"Mémoire {memory_id} supprimée du cerveau collectif (Qdrant)"
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Erreur lors de la suppression"
                })
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
    
    # Utiliser le stockage en mémoire (fallback ou par défaut)
    if memory_id not in memories:
        return json.dumps({
            "status": "error",
            "message": "Mémoire non trouvée"
        })
    
    # Vérifier que la mémoire appartient à l'équipe de l'utilisateur
    memory = memories[memory_id]
    if memory.team_id != team_id:
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette mémoire"
        })
    
    del memories[memory_id]
    
    return json.dumps({
        "status": "success",
        "message": f"Mémoire {memory_id} supprimée du cerveau collectif (mémoire)"
    })

def list_memories(user_id: str = None, team_id: str = None) -> str:
    """Lister toutes les mémoires du cerveau collectif avec logique unifiée"""
    
    # Utiliser la logique unifiée pour obtenir le contexte
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"📋 Liste mémoires - User: {user_id}, Team: {team_id}")
    
    storage = get_storage()
    if storage:
        try:
            all_memories = storage.list_memories(team_id)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
            all_memories = []
    else:
        all_memories = []
    
    # Si pas de résultats de Qdrant, utiliser le stockage en mémoire
    if not all_memories:
        if not memories:
            return json.dumps({
                "status": "success",
                "message": "Aucune mémoire dans le cerveau collectif",
                "total": 0,
                "memories": [],
                "user": user_name,
                "team": team_id
            })
        
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:  # Isolation par équipe
                all_memories.append({
                    "memory_id": memory_id,
                    "content": memory.content,
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "user_id": memory.user_id,
                    "category": memory.category,
                    "confidence": memory.confidence
                })
    
    return json.dumps({
        "status": "success",
        "total": len(all_memories),
        "memories": all_memories,
        "user": user_name,
        "team": team_id
    })

def get_team_insights() -> str:
    """Obtenir des insights sur l'activité de l'équipe avec authentification"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Récupérer toutes les mémoires de l'équipe
    all_memories = []
    storage = get_storage()
    
    if storage:
        try:
            all_memories = storage.list_memories(team_id)
        except Exception as e:
            print(f"⚠️ Erreur Qdrant, fallback vers mémoire: {e}")
    
    # Fallback vers mémoire locale
    if not all_memories:
        for memory_id, memory in memories.items():
            if memory.team_id == team_id:
                all_memories.append({
                    "memory_id": memory_id,
                    "content": memory.content,
                    "category": getattr(memory, 'category', 'general'),
                    "tags": memory.tags,
                    "timestamp": memory.timestamp,
                    "user_id": getattr(memory, 'user_id', 'unknown'),
                    "confidence": getattr(memory, 'confidence', 0.5)
                })
    
    # Analyser les patterns
    categories = {}
    contributors = {}
    tags_count = {}
    high_confidence = 0
    
    for memory in all_memories:
        # Compter les catégories
        category = memory.get('category', 'general')
        categories[category] = categories.get(category, 0) + 1
        
        # Compter les contributeurs
        user = memory.get('user_id', 'unknown')
        contributors[user] = contributors.get(user, 0) + 1
        
        # Compter les tags
        for tag in memory.get('tags', []):
            tags_count[tag] = tags_count.get(tag, 0) + 1
        
        # Compter les mémoires importantes
        if memory.get('confidence', 0) > 0.7:
            high_confidence += 1
    
    # Top 5 de chaque catégorie
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
    top_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:5]
    top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    insights = {
        "team_id": team_id,
        "total_memories": len(all_memories),
        "high_confidence_memories": high_confidence,
        "top_categories": [{"category": cat, "count": count} for cat, count in top_categories],
        "top_contributors": [{"user": user, "contributions": count} for user, count in top_contributors],
        "trending_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
        "knowledge_health": {
            "coverage": len(categories),
            "activity_level": "high" if len(all_memories) > 20 else "medium" if len(all_memories) > 5 else "low",
            "collaboration_score": len(contributors) / max(len(all_memories), 1)
        }
    }
    
    return json.dumps({
        "status": "success",
        "insights": insights,
        "user": user_name,
        "team": team_id
    })

def record_conversation_message(
    chat_id: str,
    role: str,
    content: str,
    title: str = ""
) -> str:
    """Enregistrer un message dans une conversation avec authentification"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    user_id = user_info["user_id"]
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Vérifier que le rôle est valide
    if role not in ["user", "assistant"]:
        return json.dumps({
            "status": "error",
            "message": "Le rôle doit être 'user' ou 'assistant'"
        })
    
    # Créer ou récupérer la conversation
    if chat_id not in conversations:
        conversations[chat_id] = Conversation(
            chat_id=chat_id,
            team_id=team_id,
            user_id=user_id,
            title=title or f"Conversation {chat_id[:8]}",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    conversation = conversations[chat_id]
    
    # Vérifier que l'utilisateur appartient à la même équipe
    if conversation.team_id != team_id:
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette conversation"
        })
    
    # Créer le message
    message = ConversationMessage(
        role=role,
        content=content,
        timestamp=datetime.now().isoformat(),
        user_id=user_id
    )
    
    # Ajouter le message à la conversation
    conversation.messages.append(message)
    conversation.updated_at = datetime.now().isoformat()
    
    # Générer un résumé si c'est le 5ème message ou plus
    if len(conversation.messages) >= 5 and not conversation.summary:
        conversation.summary = generate_conversation_summary(conversation)
    
    return json.dumps({
        "status": "success",
        "message": "Message enregistré avec succès",
        "chat_id": chat_id,
        "message_count": len(conversation.messages),
        "has_summary": bool(conversation.summary),
        "user": user_name,
        "team": team_id
    })

def get_conversation_summary(chat_id: str) -> str:
    """Obtenir le résumé d'une conversation avec authentification"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Vérifier que la conversation existe
    if chat_id not in conversations:
        return json.dumps({
            "status": "error",
            "message": "Conversation non trouvée"
        })
    
    conversation = conversations[chat_id]
    
    # Vérifier que l'utilisateur appartient à la même équipe
    if conversation.team_id != team_id:
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette conversation"
        })
    
    # Générer un résumé si nécessaire
    if not conversation.summary and len(conversation.messages) > 0:
        conversation.summary = generate_conversation_summary(conversation)
    
    return json.dumps({
        "status": "success",
        "chat_id": chat_id,
        "title": conversation.title,
        "message_count": len(conversation.messages),
        "summary": conversation.summary or "Aucun résumé disponible",
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "user": user_name,
        "team": team_id
    })

def list_team_conversations(limit: int = 10) -> str:
    """Lister les conversations de l'équipe avec authentification"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Filtrer les conversations de l'équipe
    team_conversations = []
    for conv in conversations.values():
        if conv.team_id == team_id:
            team_conversations.append({
                "chat_id": conv.chat_id,
                "title": conv.title,
                "message_count": len(conv.messages),
                "has_summary": bool(conv.summary),
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "last_message": conv.messages[-1].content[:100] + "..." if conv.messages else ""
            })
    
    # Trier par date de mise à jour (plus récent en premier)
    team_conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return json.dumps({
        "status": "success",
        "conversations": team_conversations[:limit],
        "total": len(team_conversations),
        "user": user_name,
        "team": team_id
    })

def generate_conversation_insights(chat_id: str) -> str:
    """Générer des insights détaillés sur une conversation avec Mistral"""
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    
    # MODE TEST: Si aucun token trouvé, utiliser le token de test
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    if not user_token:
        return json.dumps({
            "status": "error",
            "message": "Token utilisateur requis. Veuillez configurer l'authentification Bearer dans Le Chat."
        })
    
    # Vérifier le token utilisateur
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({
            "status": "error",
            "message": f"Token utilisateur invalide: {user_token[:10]}..."
        })
    
    team_id = user_info["team_id"]
    user_name = user_info["user_name"]
    
    # Vérifier que la conversation existe
    if chat_id not in conversations:
        return json.dumps({
            "status": "error",
            "message": "Conversation non trouvée"
        })
    
    conversation = conversations[chat_id]
    
    # Vérifier que l'utilisateur appartient à la même équipe
    if conversation.team_id != team_id:
        return json.dumps({
            "status": "error",
            "message": "Accès non autorisé à cette conversation"
        })
    
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        return json.dumps({
            "status": "error",
            "message": "Mistral non configuré pour les insights"
        })
    
    try:
        ensure_mistral_import()
        if not Mistral:
            return json.dumps({
                "status": "error",
                "message": "Mistral non disponible"
            })
        
        # Préparer le contexte de la conversation
        conversation_text = ""
        for msg in conversation.messages:
            role = "Utilisateur" if msg.role == "user" else "Assistant"
            conversation_text += f"{role}: {msg.content}\n"
        
        # Prompt pour les insights avec timestamp
        current_time = datetime.now()
        prompt = f"""Analysez cette conversation et fournissez des insights structurés en JSON.
        
        Date et heure actuelle: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
        
        Conversation:
        {conversation_text}
        
        Retournez un JSON avec:
        - "key_topics": liste des sujets principaux
        - "decisions": liste des décisions prises
        - "action_items": liste des actions à faire
        - "sentiment": sentiment général (positif/neutre/négatif)
        - "complexity": niveau de complexité (faible/moyen/élevé)
        - "recommendations": recommandations pour la suite
        - "timeline": références temporelles mentionnées dans la conversation
        
        Format JSON uniquement:"""
        
        # Appel à l'API Mistral
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Essayer de parser le JSON
        try:
            insights = json.loads(insights_text)
        except:
            insights = {"raw_insights": insights_text}
        
        return json.dumps({
            "status": "success",
            "chat_id": chat_id,
            "insights": insights,
            "message_count": len(conversation.messages),
            "user": user_name,
            "team": team_id
        })
        
    except Exception as e:
        print(f"❌ Erreur génération insights: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Erreur lors de la génération des insights: {e}"
        })

# --- Nouvelles fonctionnalités de Chat Interactif ---

# Dictionnaire pour stocker les conversations en cours
active_chats: Dict[str, List[Dict[str, str]]] = {}

def save_conversation_to_file(chat_id: str, conversation_history: List) -> str:
    """Sauvegarder une conversation en continu dans un fichier .txt (uniquement messages visibles par l'utilisateur)"""
    try:
        # Créer le répertoire transcripts s'il n'existe pas
        transcript_dir = "transcripts"
        os.makedirs(transcript_dir, exist_ok=True)
        
        # Chemin du fichier de transcription
        transcript_path = os.path.join(transcript_dir, f"{chat_id}.txt")
        
        # Convertir la conversation en format texte (uniquement messages visibles)
        conversation_text = ""
        for msg in conversation_history:
            # Gérer les différents types de messages (dict ou objet Mistral)
            if isinstance(msg, dict):
                role = msg.get('role', '')
                content = msg.get('content', '')
            else:
                # Objet Mistral (AssistantMessage, etc.)
                role = getattr(msg, 'role', '')
                content = getattr(msg, 'content', '')
            
            # Filtrer uniquement les messages utilisateur et assistant (pas system, tool, etc.)
            if role in ['user', 'assistant']:
                # Pour les messages assistant, vérifier qu'ils ne contiennent pas d'instructions système
                if role == 'assistant':
                    # Ignorer les messages qui contiennent des instructions système ou des mémoires
                    if any(keyword in content.lower() for keyword in [
                        'tu es un assistant', 'instructions importantes', 'outils disponibles',
                        'règles spéciales', 'date et heure actuelle', 'portfolio utilisateur',
                        'mémoire collective', 'conversations passées', 'attendez confirmation',
                        '⚠️ attention', 'catégorie:', 'date:', 'score:', '--- mémoire',
                        '📚 mémoires pertinentes', '💬 conversations pertinentes', '🔍 recherche',
                        '🛠️ appels d\'outils', '🔄 itération', '✅ réponse finale'
                    ]):
                        continue
                
                # Pour les messages utilisateur, vérifier qu'ils ne contiennent pas d'enrichissement
                if role == 'user':
                    # Ignorer les messages qui contiennent des mémoires ou conversations enrichies
                    if any(keyword in content for keyword in [
                        '📚 MÉMOIRES PERTINENTES', '💬 CONVERSATIONS PERTINENTES',
                        '--- Mémoire', '--- Conversation', 'Score:', 'Catégorie:',
                        '⚠️ ATTENTION:', 'Utilise ces mémoires', 'Utilise ces conversations'
                    ]):
                        continue
                
                role_display = "Utilisateur" if role == 'user' else "Assistant"
                conversation_text += f"{role_display}: {content}\n"
        
        # Écraser le fichier avec la conversation complète
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(conversation_text)
        
        print(f"💾 Conversation sauvegardée en continu: {transcript_path}")
        return transcript_path
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde en continu: {e}")
        return ""

def get_conversation_transcript(chat_id: str) -> str:
    """Récupérer le contenu d'un fichier de transcription de conversation"""
    try:
        transcript_path = os.path.join("transcripts", f"{chat_id}.txt")
        
        if not os.path.exists(transcript_path):
            return f"❌ Transcription non trouvée pour le chat_id: {chat_id}"
        
        with open(transcript_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"❌ Erreur lors de la lecture de la transcription: {e}"

def list_available_transcripts() -> str:
    """Lister tous les fichiers de transcription disponibles"""
    try:
        transcript_dir = "transcripts"
        if not os.path.exists(transcript_dir):
            return "❌ Aucun dossier transcripts trouvé"
        
        files = [f for f in os.listdir(transcript_dir) if f.endswith('.txt')]
        
        if not files:
            return "❌ Aucun fichier de transcription trouvé"
        
        result = f"📁 {len(files)} fichiers de transcription disponibles:\n\n"
        for i, file in enumerate(sorted(files), 1):
            chat_id = file.replace('.txt', '')
            file_path = os.path.join(transcript_dir, file)
            file_size = os.path.getsize(file_path)
            result += f"{i}. {chat_id} ({file_size} bytes)\n"
        
        return result
        
    except Exception as e:
        return f"❌ Erreur lors de la liste des transcriptions: {e}"

# Système de limitation des rappels par conversation
reminder_notifications = {}  # {chat_id: {"last_reminder_time": timestamp, "reminder_count": int}}

def chat_with_mistral(
    chat_id: str,
    user_message: str,
    user_id: str = None,
    team_id: str = None
) -> str:
    """
    Gérer une conversation interactive avec Mistral Large,
    avec logique de team_id unifiée
    """
    
    # Récupérer le token depuis les headers
    user_token = extract_token_from_headers()
    if not user_token:
        user_token = "test-token"  # Fallback pour les tests
    
    # ✅ UTILISER LA LOGIQUE UNIFIÉE
    context = get_unified_team_context(
        user_token=user_token,
        user_id=user_id,
        team_id=team_id
    )
    
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_name = context["user_name"]
    
    print(f"🔄 Context unifié: {context}")

    # Générer un chat_id unique si non fourni
    if not chat_id:
        chat_id = hashlib.md5(f"{user_id}-{datetime.now().isoformat()}".encode()).hexdigest()
        print(f"🆕 Nouvelle conversation initiée avec chat_id: {chat_id}")

    # Mode test : simuler Mistral si non configuré
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        # Mode simulation pour les tests
        assistant_response = f"Mode test : J'ai reçu votre message '{user_message}'. Dans un environnement de production avec Mistral configuré, je pourrais utiliser tous les outils de mémoire collective pour vous aider."
        
        # Ajouter la réponse simulée à l'historique
        if chat_id not in active_chats:
            active_chats[chat_id] = []
        active_chats[chat_id].append({"role": "assistant", "content": assistant_response})
        
        return json.dumps({
            "status": "success", 
            "response": assistant_response,
            "mode": "test_simulation"
        })
    
    ensure_mistral_import()
    if not Mistral:
        return json.dumps({"status": "error", "message": "Mistral non disponible."})

    # Vérifier la disponibilité du stockage
    storage = get_storage()
    storage_available = storage is not None
    
    # Processus de réflexion préalable avec portfolio
    print("🧠 Début du processus de réflexion...")
    add_ai_log("thinking", "Début du processus de réflexion...")
    thinking_result = reflective_thinking_process(user_message, user_id, team_id)
    print(f"🧠 Processus de réflexion: {thinking_result}")
    add_ai_log("thinking", f"Processus de réflexion terminé: {thinking_result.get('patterns_detected', [])}")
    
    # Si une règle du portfolio est déclenchée, répondre immédiatement
    if thinking_result.get("rule_triggered") and thinking_result.get("response"):
        print(f"⚡ Règle portfolio déclenchée: {thinking_result['response']}")
        add_ai_log("portfolio", f"Règle portfolio déclenchée: {thinking_result['response']}")
        return json.dumps({
            "status": "success",
            "response": thinking_result["response"],
            "chat_id": chat_id,
            "mode": "portfolio_rule_triggered",
            "source": thinking_result.get("source", "portfolio")
        })
    
    # Analyser la conversation pour détecter des rappels potentiels
    if thinking_result.get("time_references") or thinking_result.get("patterns_detected"):
        print("🔔 Analyse de la conversation pour détecter des rappels...")
        conversation_text = f"Utilisateur: {user_message}"
        detected_reminders = analyze_conversation_for_reminders(conversation_text, user_id, team_id)
        
        if detected_reminders:
            print(f"🔔 {len(detected_reminders)} rappels détectés automatiquement")
            # Ajouter les rappels détectés
            for reminder in detected_reminders:
                add_reminder(
                    title=reminder.get("title", "Rappel détecté"),
                    description=reminder.get("description", ""),
                    due_date=reminder.get("due_date", ""),
                    priority=reminder.get("priority", "medium"),
                    reminder_type=reminder.get("type", "general")
                )
    
    # Mise à jour automatique du portfolio basée sur le message
    print("📋 Mise à jour automatique du portfolio...")
    add_ai_log("portfolio", "Mise à jour automatique du portfolio...")
    auto_update_portfolio(user_message, user_id, team_id)
    
    # Vérification automatique des rappels à venir
    print("🔔 Vérification des rappels à venir...")
    add_ai_log("reminder", "Vérification des rappels à venir...")
    upcoming_reminders = check_upcoming_reminders(team_id, hours_ahead=24)
    reminders_context = ""
    
    # Détecter et supprimer les rappels en double
    if upcoming_reminders:
        original_count = len(upcoming_reminders)
        upcoming_reminders = detect_duplicate_reminders(upcoming_reminders)
        if len(upcoming_reminders) < original_count:
            print(f"🔄 {original_count - len(upcoming_reminders)} rappels en double supprimés")
    
    # Utiliser la logique intelligente pour décider d'afficher les rappels
    if upcoming_reminders and should_show_reminders(chat_id, upcoming_reminders):
        print(f"🔔 {len(upcoming_reminders)} rappels à venir détectés (affichage autorisé)")
        add_ai_log("reminder", f"{len(upcoming_reminders)} rappels à venir détectés")
        
        # Préparer le contexte des rappels à venir
        reminders_context = "\n\n🔔 RAPPELS À VENIR :\n"
        for reminder in upcoming_reminders[:3]:  # Limiter à 3 rappels
            minutes_until = reminder.get("minutes_until", 0)
            hours_until = reminder.get("hours_until", 0)
            
            # Formatage du temps plus précis
            if minutes_until < 60:
                time_str = f"dans {int(minutes_until)} minutes"
            elif hours_until < 24:
                time_str = f"dans {hours_until:.1f} heures"
            else:
                days = hours_until / 24
                time_str = f"dans {days:.1f} jours"
            
            reminders_context += f"• {reminder.get('title', 'Rappel')} - {time_str}\n"
    elif upcoming_reminders:
        print(f"🔔 {len(upcoming_reminders)} rappels à venir détectés (affichage limité)")
        add_ai_log("reminder", f"{len(upcoming_reminders)} rappels à venir détectés (non affichés)")
    
    # Historique de la conversation
    if chat_id not in active_chats:
        current_time = datetime.now()
        system_message = f"""Tu es un assistant IA expert avec accès à une mémoire collective, aux conversations passées, et au PORTFOLIO UTILISATEUR DYNAMIQUE.

DATE ET HEURE ACTUELLE: {current_time.strftime("%Y-%m-%d %H:%M:%S")} (Fuseau horaire: {current_time.strftime("%Z")})

INSTRUCTIONS IMPORTANTES :
- Réponds de manière naturelle et conversationnelle
- N'affiche JAMAIS les étapes de réflexion internes dans tes réponses
- Utilise les outils disponibles pour accéder aux informations
- Vérifie automatiquement le portfolio utilisateur et les rappels à venir
- Mets à jour le portfolio avec les nouvelles informations importantes
- Sois concis et utile
- ⚠️ IMPORTANT: Pour les rappels, calcule TOUJOURS l'heure exacte en ajoutant les minutes à l'heure actuelle. Ne devine jamais l'heure !
- ⚠️ CRITIQUE: Si des mémoires ou conversations sont fournies automatiquement, tu DOIS les utiliser dans ta réponse. Ne dis jamais "je ne sais pas" si des informations pertinentes sont disponibles !

OUTILS DISPONIBLES :
- search_memories : Rechercher dans la mémoire collective
- search_past_conversations : Rechercher dans les conversations archivées
- get_user_portfolio_summary : Consulter le portfolio utilisateur
- update_user_portfolio : Mettre à jour le portfolio
- check_upcoming_reminders : Vérifier les rappels à venir
- add_reminder : Ajouter un rappel

RÈGLES SPÉCIALES :
- Vérifie toujours les rappels à venir et informe l'utilisateur
- Enrichis automatiquement le portfolio avec les informations importantes
- Sois proactif dans la gestion des rappels et événements

INSTRUCTIONS DE RECHERCHE OBLIGATOIRES :
- ⚠️ TU DOIS TOUJOURS rechercher dans les mémoires et conversations avant de répondre
- Si tu n'as pas d'informations sur un sujet, utilise search_memories et search_past_conversations
- Recherche toujours dans les mémoires avant de dire "je ne sais pas"
- Utilise des termes de recherche pertinents pour trouver des informations
- ⚠️ CRITIQUE: Si des mémoires sont fournies automatiquement, tu DOIS les utiliser en priorité !
- 🚫 NE FAIS PAS de recherches supplémentaires si des mémoires pertinentes sont déjà fournies !
- Ne réponds JAMAIS "je ne sais pas" si des mémoires pertinentes sont disponibles !

Réponds de manière naturelle et utile !{reminders_context}"""
        
        if not storage_available:
            system_message += "\n\nNote: Le service de stockage vectoriel n'est pas disponible pour le moment, mais tu peux toujours répondre aux questions générales."
        
        active_chats[chat_id] = [{"role": "system", "content": system_message}]
    
    # Intégrer les mémoires trouvées automatiquement dans le message utilisateur
    enhanced_user_message = user_message
    
    if storage_available:
        try:
            # Recherche dans les mémoires avec des termes plus spécifiques
            search_terms = [user_message]
            
            # Extraire des mots-clés spécifiques pour améliorer la recherche
            if "baptiste" in user_message.lower():
                search_terms.extend(["baptiste code", "baptiste flutter", "baptiste react", "baptiste typescript"])
            if "code" in user_message.lower():
                search_terms.extend(["code", "programming", "développement"])
            if "travaille" in user_message.lower() or "travail" in user_message.lower():
                search_terms.extend(["travail", "projet", "work"])
            
            # Recherche avec le terme original
            memory_results = storage.search_memories(user_message, team_id, limit=5)
            
            # Recherche avec des termes spécifiques pour Baptiste
            if "baptiste" in user_message.lower():
                for term in ["baptiste code", "baptiste flutter", "baptiste react"]:
                    additional_results = storage.search_memories(term, team_id, limit=3)
                    # Fusionner les résultats en évitant les doublons
                    for result in additional_results:
                        if not any(r.get('memory_id') == result.get('memory_id') for r in memory_results):
                            memory_results.append(result)
                
                # Trier par priorité : mémoires de travail d'abord, puis par score
                def priority_score(result):
                    category = result.get('category', '')
                    base_score = result.get('similarity_score', 0)
                    content = result.get('content', '').lower()
                    
                    # Prioriser les mémoires de travail
                    if category in ['work', 'project', 'code']:
                        return base_score + 0.2  # Bonus pour les mémoires de travail
                    # Prioriser les conversations qui mentionnent des technologies spécifiques
                    elif category == 'conversation_summary' and any(tech in content for tech in ['flutter', 'react', 'typescript', 'javascript', 'python', 'java']):
                        return base_score + 0.3  # Bonus important pour les conversations techniques
                    elif category == 'conversation_summary':
                        return base_score - 0.1  # Malus pour les conversations générales
                    else:
                        return base_score
                
                memory_results.sort(key=priority_score, reverse=True)
                memory_results = memory_results[:5]  # Garder seulement les 5 meilleurs
            if memory_results:
                print(f"✅ {len(memory_results)} mémoires trouvées automatiquement")
                add_ai_log("search", f"{len(memory_results)} mémoires trouvées automatiquement")
                
                # Intégrer les mémoires dans le message utilisateur
                enhanced_user_message += "\\n\\n📚 MÉMOIRES PERTINENTES TROUVÉES:\\n"
                for i, mem in enumerate(memory_results, 1):
                    enhanced_user_message += f"\\n--- Mémoire {i} (Score: {mem.get('similarity_score', 0):.3f}) ---\\n"
                    enhanced_user_message += f"Contenu: {mem.get('content', 'N/A')}\\n"
                    enhanced_user_message += f"Catégorie: {mem.get('category', 'N/A')}\\n"
                    enhanced_user_message += f"Date: {mem.get('timestamp', 'N/A')}\\n"
                
                enhanced_user_message += "\\n⚠️ ATTENTION: Utilise ces mémoires dans ta réponse !\\n"
            
            # Recherche dans les conversations archivées
            conversation_results = storage.search_conversation_summaries(user_message, team_id, limit=2)
            if conversation_results:
                print(f"✅ {len(conversation_results)} conversations trouvées automatiquement")
                add_ai_log("search", f"{len(conversation_results)} conversations trouvées automatiquement")
                
                # Intégrer les conversations dans le message utilisateur
                enhanced_user_message += "\\n\\n💬 CONVERSATIONS PERTINENTES TROUVÉES:\\n"
                for i, conv in enumerate(conversation_results, 1):
                    enhanced_user_message += f"\\n--- Conversation {i} (Score: {conv.get('score', 0):.3f}) ---\\n"
                    enhanced_user_message += f"Résumé: {conv.get('summary', 'N/A')}\\n"
                    enhanced_user_message += f"Date: {conv.get('timestamp', 'N/A')}\\n"
                
                enhanced_user_message += "\\n⚠️ ATTENTION: Utilise ces conversations dans ta réponse !\\n"
                
        except Exception as e:
            print(f"⚠️ Erreur lors de la recherche automatique: {e}")
            add_ai_log("search", f"Erreur recherche automatique: {e}")
    
    # Ajouter le message utilisateur enrichi à la conversation active (pour l'IA)
    active_chats[chat_id].append({"role": "user", "content": enhanced_user_message})

    # Détecter les IDs de conversation dans le message de l'utilisateur
    detected_ids = detect_conversation_ids(user_message)
    if detected_ids:
        print(f"🔍 IDs de conversation détectés: {detected_ids}")
        # Ajouter une instruction spéciale pour forcer l'utilisation de ces IDs
        special_instruction = f"\\n\\nATTENTION: L'utilisateur a mentionné les IDs de conversation suivants: {', '.join(detected_ids)}. Tu DOIS utiliser `get_full_transcript` avec ces IDs EXACTS en priorité absolue. C'est la première chose à faire."
        active_chats[chat_id].append({"role": "system", "content": special_instruction})

    try:
        # Générer dynamiquement le schéma des outils à partir de available_tools
        tools_for_mistral = []
        
        # Schémas spécifiques pour les outils les plus importants
        tool_schemas = {
            "search_past_conversations": {
                "type": "function",
                "function": {
                    "name": "search_past_conversations",
                    "description": "Rechercher dans les résumés des conversations archivées",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Terme de recherche pour trouver des conversations pertinentes"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Nombre maximum de résultats à retourner",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "search_memories": {
                "type": "function",
                "function": {
                    "name": "search_memories",
                    "description": "Rechercher dans la mémoire collective de l'équipe",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Terme de recherche dans les mémoires"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Nombre maximum de résultats à retourner",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "add_memory": {
                "type": "function",
                "function": {
                    "name": "add_memory",
                    "description": "Ajouter une mémoire au cerveau collectif de l'équipe",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Contenu de la mémoire à ajouter"
                            },
                            "tags": {
                                "type": "string",
                                "description": "Tags séparés par des virgules",
                                "default": ""
                            },
                            "category": {
                                "type": "string",
                                "description": "Catégorie de la mémoire",
                                "default": "general"
                            },
                            "visibility": {
                                "type": "string",
                                "description": "Visibilité de la mémoire",
                                "default": "team"
                            }
                        },
                        "required": ["content"]
                    }
                }
            },
            "get_full_transcript": {
                "type": "function",
                "function": {
                    "name": "get_full_transcript",
                    "description": "Récupérer la transcription complète d'une conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "ID de la conversation à récupérer"
                            }
                        },
                        "required": ["chat_id"]
                    }
                }
            },
            "multi_query_search": {
                "type": "function",
                "function": {
                    "name": "multi_query_search",
                    "description": "Effectuer plusieurs requêtes de recherche avec différentes approches pour maximiser les résultats",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Terme de recherche principal"
                            },
                            "max_queries": {
                                "type": "integer",
                                "description": "Nombre maximum de variantes de recherche à effectuer",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "search_in_transcript": {
                "type": "function",
                "function": {
                    "name": "search_in_transcript",
                    "description": "Rechercher un terme spécifique dans la transcription complète d'une conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "string",
                                "description": "ID de la conversation à rechercher"
                            },
                            "search_term": {
                                "type": "string",
                                "description": "Terme à rechercher dans la transcription"
                            }
                        },
                        "required": ["chat_id", "search_term"]
                    }
                }
            },
            "search_archived_conversations": {
                "type": "function",
                "function": {
                    "name": "search_archived_conversations",
                    "description": "Recherche dans toutes les conversations archivées avec une approche exhaustive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Terme de recherche pour trouver des conversations pertinentes"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Nombre maximum de résultats à retourner",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "expand_search_keywords": {
                "type": "function",
                "function": {
                    "name": "expand_search_keywords",
                    "description": "Génère des mots-clés de recherche alternatifs et des synonymes pour une requête",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Requête de recherche originale"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "add_user_rule": {
                "type": "function",
                "function": {
                    "name": "add_user_rule",
                    "description": "Ajouter une règle utilisateur personnalisée qui sera vérifiée à chaque message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Le pattern à détecter (ex: 'ends_with_quoi', 'contains_quoi', 'exact_quoi', ou une regex)"
                            },
                            "response": {
                                "type": "string",
                                "description": "La réponse à donner quand le pattern est détecté"
                            },
                            "rule_type": {
                                "type": "string",
                                "description": "Type de règle: 'pattern_match', 'keyword_match', 'exact_match'",
                                "default": "pattern_match"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description de la règle",
                                "default": ""
                            }
                        },
                        "required": ["pattern", "response"]
                    }
                }
            },
            "update_user_portfolio": {
                "type": "function",
                "function": {
                    "name": "update_user_portfolio",
                    "description": "Mettre à jour le portfolio utilisateur avec de nouvelles informations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "ID de l'utilisateur"
                            },
                            "updates": {
                                "type": "object",
                                "description": "Objet contenant les mises à jour du portfolio (profile, rules, context, events, reminders, learning)"
                            }
                        },
                        "required": ["user_id", "updates"]
                    }
                }
            },
            "get_user_portfolio_summary": {
                "type": "function",
                "function": {
                    "name": "get_user_portfolio_summary",
                    "description": "Obtenir un résumé du portfolio utilisateur",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "ID de l'utilisateur"
                            }
                        },
                        "required": ["user_id"]
                    }
                }
            },
            "add_reminder": {
                "type": "function",
                "function": {
                    "name": "add_reminder",
                    "description": "Ajouter un rappel intelligent pour l'utilisateur",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Titre du rappel"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description détaillée du rappel"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Date/heure du rappel (format ISO ou description naturelle)"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priorité: low, medium, high",
                                "default": "medium"
                            },
                            "reminder_type": {
                                "type": "string",
                                "description": "Type de rappel: meeting, deadline, personal, work, other",
                                "default": "general"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID de l'utilisateur (injecté automatiquement)"
                            },
                            "team_id": {
                                "type": "string",
                                "description": "ID de l'équipe (injecté automatiquement)"
                            }
                        },
                        "required": ["title", "description", "due_date"]
                    }
                }
            },
            "check_upcoming_reminders": {
                "type": "function",
                "function": {
                    "name": "check_upcoming_reminders",
                    "description": "Vérifier les rappels à venir pour l'utilisateur",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "string",
                                "description": "ID de l'équipe"
                            },
                            "hours_ahead": {
                                "type": "integer",
                                "description": "Nombre d'heures à l'avance pour vérifier les rappels",
                                "default": 24
                            }
                        },
                        "required": ["team_id"]
                    }
                }
            },
            "list_reminders": {
                "type": "function",
                "function": {
                    "name": "list_reminders",
                    "description": "Lister tous les rappels de l'utilisateur",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            "delete_reminder": {
                "type": "function",
                "function": {
                    "name": "delete_reminder",
                    "description": "Supprimer un rappel spécifique par son ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reminder_id": {
                                "type": "string",
                                "description": "ID du rappel à supprimer"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID de l'utilisateur (injecté automatiquement)"
                            },
                            "team_id": {
                                "type": "string",
                                "description": "ID de l'équipe (injecté automatiquement)"
                            }
                        },
                        "required": ["reminder_id"]
                    }
                }
            },
            "delete_all_reminders": {
                "type": "function",
                "function": {
                    "name": "delete_all_reminders",
                    "description": "Supprimer tous les rappels de l'utilisateur",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        }
        
        # Ajouter les schémas spécifiques seulement si le stockage est disponible
        if storage_available:
            # Prioriser les outils de mémoire
            priority_tools = ["search_memories", "add_memory", "list_memories", "search_past_conversations"]
            for name in priority_tools:
                if name in tool_schemas:
                    tools_for_mistral.append(tool_schemas[name])
            
            # Ajouter les autres outils
            for name, schema in tool_schemas.items():
                if name not in priority_tools and name in available_tools:
                    tools_for_mistral.append(schema)
        else:
            # Si le stockage n'est pas disponible, ajouter seulement les outils de base
            basic_tools = ["add_memory", "search_memories", "list_memories"]
            for name in basic_tools:
                if name in tool_schemas:
                    tools_for_mistral.append(tool_schemas[name])
        
        # Ajouter les autres outils avec des schémas basiques
        for name, func in available_tools.items():
            if name not in tool_schemas:
                tools_for_mistral.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": func.__doc__.strip().split("\n")[0] if func.__doc__ else "",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                })

        # Boucle de conversation pour permettre les appels d'outils multiples
        max_iterations = 20  # Pour éviter les boucles infinies
        for i in range(max_iterations):
            print(f"🔄 Itération {i+1} de la boucle de conversation...")

            # Premier appel à Mistral avec les outils
            response = Mistral.chat.complete(
                model="mistral-large-latest",
                messages=active_chats[chat_id],
                tools=tools_for_mistral,
                tool_choice="auto"
            )

            # Ajouter la réponse initiale (qui peut contenir des appels d'outils) à l'historique
            assistant_response_message = response.choices[0].message
            active_chats[chat_id].append(assistant_response_message)
            
            # Sauvegarder en continu la conversation avec le message utilisateur original
            conversation_for_save = []
            for msg in active_chats[chat_id]:
                if isinstance(msg, dict):
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                else:
                    role = getattr(msg, 'role', '')
                    content = getattr(msg, 'content', '')
                
                # Pour les messages utilisateur, remplacer par le message original
                if role == 'user':
                    conversation_for_save.append({"role": "user", "content": user_message})
                else:
                    conversation_for_save.append(msg)
            
            save_conversation_to_file(chat_id, conversation_for_save)

            # Si Mistral ne demande pas d'outils, c'est la réponse finale
            if not assistant_response_message.tool_calls:
                final_assistant_message = assistant_response_message.content.strip()
                print(f"✅ Réponse finale générée: {final_assistant_message[:100]}...")
                
                # Vérifier si la conversation doit être finalisée automatiquement
                finalize_conversation = False
                finalize_reason = ""
                
                # 1. Détecter les mots-clés de fin de conversation
                end_keywords = ['merci', 'au revoir', 'à bientôt', 'fin de conversation', 'terminé', 'c\'est tout', 'c est tout', 'bye', 'goodbye', 'end', 'quit', 'exit']
                if any(keyword in user_message.lower() for keyword in end_keywords):
                    finalize_conversation = True
                    finalize_reason = "Mots-clés de fin détectés"
                
                # 2. Finalisation automatique après un certain nombre de messages (par exemple 20 messages)
                elif len(active_chats[chat_id]) >= 20:
                    finalize_conversation = True
                    finalize_reason = "Limite de messages atteinte"
                
                # 3. Finalisation si la conversation est très longue (plus de 50 messages)
                elif len(active_chats[chat_id]) >= 50:
                    finalize_conversation = True
                    finalize_reason = "Conversation très longue"
                
                # Finaliser la conversation si nécessaire
                if finalize_conversation:
                    print(f"🔄 Finalisation automatique de la conversation: {finalize_reason}")
                    try:
                        # Appeler la fonction de finalisation
                        finalize_result = end_chat_and_summarize(chat_id)
                        finalize_data = json.loads(finalize_result)
                        
                        if finalize_data.get("status") == "success":
                            print(f"✅ Conversation finalisée et sauvegardée: {finalize_data.get('chat_id')}")
                            # Ajouter un message informatif à la réponse
                            final_assistant_message += f"\n\n📝 **Conversation automatiquement finalisée** ({finalize_reason})"
                        else:
                            print(f"⚠️ Erreur lors de la finalisation: {finalize_data.get('message')}")
                    except Exception as e:
                        print(f"❌ Erreur lors de la finalisation automatique: {e}")
                
                return json.dumps({"status": "success", "response": final_assistant_message, "chat_id": chat_id})

            # Si Mistral demande d'utiliser des outils
            tool_calls = assistant_response_message.tool_calls
            tool_outputs = []
            print(f"🛠️ Appels d'outils détectés: {[t.function.name for t in tool_calls]}")
            add_ai_log("tool_call", f"Appels d'outils: {[t.function.name for t in tool_calls]}")

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name in available_tools:
                    try:
                        # Injecter user_id et team_id pour les outils qui les supportent
                        if function_name in ["search_memories", "add_memory", "list_memories", "delete_memory", "search_past_conversations", "get_user_portfolio_summary", "update_user_portfolio", "add_reminder", "check_upcoming_reminders_tool", "list_reminders", "delete_reminder", "delete_all_reminders"]:
                            function_args["user_id"] = user_id
                            function_args["team_id"] = team_id
                        
                        # Appel dynamique de la fonction outil
                        output = available_tools[function_name](**function_args)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })
                    except TypeError as e:
                        # Gestion spéciale pour les arguments manquants
                        error_msg = f"Arguments manquants pour l'outil '{function_name}': {str(e)}"
                        print(f"❌ {error_msg}")
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"status": "error", "message": error_msg})
                        })
                    except Exception as e:
                        print(f"❌ Erreur lors de l'exécution de l'outil '{function_name}': {e}")
                        # Message d'erreur plus informatif
                        if "stockage" in str(e).lower() or "qdrant" in str(e).lower():
                            error_msg = f"Le service de stockage vectoriel n'est pas disponible pour le moment. Tu peux toujours répondre aux questions générales sans accéder aux anciennes conversations."
                        else:
                            error_msg = f"Erreur lors de l'exécution de l'outil '{function_name}': {str(e)}"
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"status": "error", "message": error_msg})
                        })
                else:
                    # Outil non trouvé
                    print(f"❌ Outil '{function_name}' non trouvé")
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps({"status": "error", "message": f"Outil '{function_name}' non disponible"})
                        })
            
            # Ajouter les résultats des outils à l'historique pour la prochaine itération
            # Trier par tool_call_id pour éviter les conflits d'ordre
            tool_outputs.sort(key=lambda x: x["tool_call_id"])
            for tool_output in tool_outputs:
                active_chats[chat_id].append({
                    "role": "tool",
                    "content": tool_output["output"],
                    "tool_call_id": tool_output["tool_call_id"]
                })

        # Si la boucle se termine sans réponse, c'est une erreur
        print("⚠️ Limite d'itérations atteinte.")
        return json.dumps({
            "status": "error",
            "message": "Le modèle n'a pas pu générer de réponse finale après plusieurs tentatives d'utilisation d'outils."
        })

    except Exception as e:
        print(f"❌ Erreur dans `chat_with_mistral`: {e}")
        return json.dumps({"status": "error", "message": str(e)})

def end_chat_and_summarize(chat_id: str) -> str:
    """Terminer une conversation, la résumer et la préparer pour le stockage."""

    # Récupérer le token
    user_token = extract_token_from_headers()
    if not user_token:
        print("🧪 MODE TEST: Utilisation du token de test")
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"
    
    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({"status": "error", "message": "Token invalide."})

    team_id = user_info["team_id"]

    # Vérifier que la conversation existe
    if chat_id not in active_chats:
        return json.dumps({"status": "error", "message": "Conversation non trouvée."})

    conversation_history = active_chats[chat_id]
    
    # S'assurer que Mistral est disponible pour le résumé
    ensure_mistral_import()
    if not Mistral:
        return json.dumps({"status": "error", "message": "Mistral non disponible pour le résumé."})

    # Préparer le texte de la conversation pour le résumé
    conversation_text = ""
    for msg in conversation_history:
        role = "Utilisateur" if msg.get('role') == 'user' else "Assistant"
        content = msg.get('content', '')
        conversation_text += f"{role}: {content}\n"
    
    prompt = f"""
    Résume la conversation suivante en identifiant les points clés, les décisions et les actions à entreprendre.
    Le résumé doit être concis et factuel.

    Conversation :
    {conversation_text}

    Résumé :
    """
    
    try:
        # Appel à l'API Mistral pour le résumé
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2
        )
        summary = response.choices[0].message.content.strip()

        # Étape 4: Sauvegarder la transcription et stocker le résumé
        transcript_dir = "transcripts"
        os.makedirs(transcript_dir, exist_ok=True)
        transcript_path = os.path.join(transcript_dir, f"{chat_id}.txt")
        
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(conversation_text)
        
        print(f"💾 Transcription sauvegardée: {transcript_path}")
        
        # Étape 5: Extraire des tags intelligents à partir du contenu
        auto_tags = extract_keywords_for_tags(summary + "\n" + conversation_text)

        storage = get_storage()
        if storage:
            try:
                storage.store_conversation_summary(
                    chat_id=chat_id,
                    summary=summary,
                    team_id=team_id,
                    transcript_path=transcript_path,
                    message_count=len(conversation_history),
                    auto_tags=auto_tags # Ajout des tags auto
                )
            except Exception as e:
                print(f"⚠️ Erreur de stockage Qdrant, le résumé n'a pas été sauvegardé: {e}")
                # En cas d'échec, nous pouvons décider de ne pas supprimer le chat actif
                # pour permettre une nouvelle tentative, mais pour l'instant, on continue.
        
        # Supprimer la conversation de la mémoire active
        del active_chats[chat_id]

        return json.dumps({
            "status": "success",
            "chat_id": chat_id,
            "summary": summary,
            "message": "Conversation terminée et résumée. Prête pour l'archivage.",
            "auto_tags": auto_tags
        })

    except Exception as e:
        print(f"❌ Erreur lors du résumé de la conversation: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Erreur lors du résumé: {e}"
        })


# --- Fin des nouvelles fonctionnalités ---


# Middleware pour capturer les headers
def capture_headers_middleware(request, call_next):
    """Middleware pour capturer les headers HTTP"""
    try:
        # Capturer les headers de la requête
        headers = dict(request.headers)
        set_request_headers(headers)
        print(f"🔍 Headers capturés: {headers}")
    except Exception as e:
        print(f"❌ Erreur capture headers: {e}")
    
    response = call_next(request)
    return response

# Initialisation paresseuse de MCP
def auto_archive_existing_conversations():
    """Archiver automatiquement les conversations existantes au démarrage"""
    try:
        print("🔄 Vérification de l'archivage automatique...")
        
        storage = get_storage()
        if not storage:
            print("⚠️ Stockage non disponible, archivage différé")
            return
        
        # Vérifier si le répertoire conversations existe
        conversations_dir = "conversations"
        if not os.path.exists(conversations_dir):
            print("📁 Aucune conversation à archiver")
            return
        
        # Vérifier si le répertoire transcripts existe
        transcript_dir = "transcripts"
        os.makedirs(transcript_dir, exist_ok=True)
        
        # Configuration pour l'archivage
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"  # Token de test par défaut
        user_info = verify_user_token(user_token)
        team_id = user_info["team_id"]
        
        archived_count = 0
        skipped_count = 0
        
        for filename in os.listdir(conversations_dir):
            if filename.endswith('.json'):
                chat_id = filename.replace('.json', '')
                transcript_path = os.path.join(transcript_dir, f"{chat_id}.txt")
                
                # Vérifier si déjà archivé
                if os.path.exists(transcript_path):
                    skipped_count += 1
                    continue
                
                conv_path = os.path.join(conversations_dir, filename)
                
                try:
                    # Lire la conversation
                    with open(conv_path, 'r', encoding='utf-8') as f:
                        conv_data = json.load(f)
                    
                    # Créer le texte de la conversation
                    conversation_text = ""
                    for msg in conv_data.get('messages', []):
                        role = "Utilisateur" if msg.get('role') == 'user' else "Assistant"
                        content = msg.get('content', '')
                        conversation_text += f"{role}: {content}\n"
                    
                    # Sauvegarder la transcription
                    with open(transcript_path, 'w', encoding='utf-8') as f:
                        f.write(conversation_text)
                    
                    # Générer un résumé simple
                    summary = f"Conversation {chat_id} - {len(conv_data.get('messages', []))} messages"
                    
                    # Extraire des tags basiques
                    auto_tags = "conversation,archived"
                    if "python" in conversation_text.lower():
                        auto_tags += ",python"
                    if "code" in conversation_text.lower():
                        auto_tags += ",code"
                    if "tictactoe" in conversation_text.lower() or "tic-tac-toe" in conversation_text.lower():
                        auto_tags += ",tictactoe,game"
                    if "winning_move" in conversation_text.lower():
                        auto_tags += ",winning_move,game"
                    if "félicitations" in conversation_text.lower() or "felicitations" in conversation_text.lower():
                        auto_tags += ",félicitations,victoire"
                    
                    # Stocker le résumé dans Qdrant
                    storage.store_conversation_summary(
                        chat_id=chat_id,
                        summary=summary,
                        team_id=team_id,
                        transcript_path=transcript_path,
                        message_count=len(conv_data.get('messages', [])),
                        auto_tags=auto_tags
                    )
                    
                    archived_count += 1
                    print(f"✅ Archivé: {filename}")
                    
                except Exception as e:
                    print(f"❌ Erreur archivage {filename}: {e}")
        
        if archived_count > 0:
            print(f"📁 {archived_count} conversations archivées automatiquement")
        if skipped_count > 0:
            print(f"⏭️ {skipped_count} conversations déjà archivées")
        
    except Exception as e:
        print(f"⚠️ Erreur archivage automatique: {e}")

def initialize_mcp():
    """Initialiser MCP de manière paresseuse"""
    global mcp
    
    if mcp is None:
        mcp = get_mcp()
        
        if mcp:
            # Ajouter le middleware pour capturer les headers
            try:
                # FastMCP utilise uvicorn, on doit accéder à l'app FastAPI différemment
                if hasattr(mcp, '_app') and mcp._app:
                    mcp._app.middleware("http")(capture_headers_middleware)
                    print("✅ Middleware headers ajouté")
                else:
                    print("⚠️ App FastAPI non accessible pour le middleware")
            except Exception as e:
                print(f"⚠️ Impossible d'ajouter le middleware: {e}")
            
            # Ajouter l'endpoint de santé via l'outil MCP
            mcp.tool(
                title="Health Check",
                description="Vérifier l'état du système et des services",
            )(health_check)
            
            # Enregistrer les outils
            mcp.tool(
                title="Add Memory",
                description="Ajouter une mémoire au cerveau collectif de l'équipe",
            )(add_memory)
            
            mcp.tool(
                title="Search Memories",
                description="Rechercher dans le cerveau collectif de l'équipe",
            )(search_memories)
            
            mcp.tool(
                title="Delete Memory",
                description="Supprimer une mémoire du cerveau collectif",
            )(delete_memory)
            
            mcp.tool(
                title="List All Memories",
                description="Lister toutes les mémoires du cerveau collectif",
            )(list_memories)
            
            mcp.tool(
                title="Get Team Insights",
                description="Obtenir des insights sur l'activité de l'équipe",
            )(get_team_insights)
            
            # Outils pour les conversations
            mcp.tool(
                title="Record Conversation Message",
                description="Enregistrer un message dans une conversation",
            )(record_conversation_message)
            
            mcp.tool(
                title="Get Conversation Summary",
                description="Obtenir le résumé d'une conversation",
            )(get_conversation_summary)
            
            mcp.tool(
                title="List Team Conversations",
                description="Lister les conversations de l'équipe",
            )(list_team_conversations)
            
            mcp.tool(
                title="Generate Conversation Insights",
                description="Générer des insights détaillés sur une conversation avec Mistral",
            )(generate_conversation_insights)
            
            # Outil de chat interactif
            # mcp.tool(
            #     title="Chat with Mistral",
            #     description="Maintenir une conversation interactive avec Mistral Large."
            # )(chat_with_mistral)
            
            mcp.tool(
                title="End Chat and Summarize",
                description="Terminer une conversation et générer son résumé pour archivage."
            )(end_chat_and_summarize)
            
            mcp.tool(
                title="Search Past Conversations",
                description="Rechercher dans les résumés des conversations archivées."
            )(search_past_conversations)
            
            mcp.tool(
                title="Get Full Transcript",
                description="Récupérer la transcription complète d'une conversation à partir de son ID."
            )(get_full_transcript)
            
            mcp.tool(
                title="Get Conversation Transcript",
                description="Récupérer le contenu d'un fichier de transcription de conversation (format utilisateur/assistant uniquement)."
            )(get_conversation_transcript)
            
            mcp.tool(
                title="List Available Transcripts",
                description="Lister tous les fichiers de transcription disponibles dans le dossier transcripts/."
            )(list_available_transcripts)
            
            # Outil de chat interactif - exposé pour l'inspecteur MCP
            mcp.tool(
                title="Chat with Mistral",
                description="Maintenir une conversation interactive avec Mistral Large avec accès aux outils de mémoire."
            )(chat_with_mistral)
            
            if not IS_LAMBDA:
                print("✅ MCP initialisé avec succès")
        else:
            if not IS_LAMBDA:
                print("❌ Impossible d'initialiser MCP")
    
    return mcp

def search_past_conversations(query: str, limit: int = 3, user_id: str = None, team_id: str = None) -> str:
    """Rechercher dans les résumés des conversations passées pour trouver des informations pertinentes."""
    
    # Utiliser les paramètres fournis ou récupérer depuis les headers
    if user_id and team_id:
        # Utiliser les paramètres fournis (mode multi-utilisateur)
        pass
    else:
        # Mode par défaut avec token
        user_token = extract_token_from_headers()
        if not user_token:
            user_token = "user_d8a7996df3c777e9ac2914ef16d5b501" # Test fallback

        user_info = verify_user_token(user_token)
        if not user_info:
            return json.dumps({"status": "error", "message": "Token invalide."})

        user_id = user_info["user_id"]
        team_id = user_info["team_id"]
    
    storage = get_storage()

    if not storage:
        return json.dumps({
            "status": "error", 
            "message": "Le service de stockage vectoriel n'est pas disponible. Les conversations passées ne peuvent pas être recherchées.",
            "fallback_available": False
        })

    try:
        results = storage.search_conversation_summaries(query, team_id, limit)
        return json.dumps({
            "status": "success",
            "results": results
        })
    except Exception as e:
        return json.dumps({
            "status": "error", 
            "message": f"Erreur lors de la recherche dans les conversations passées: {str(e)}",
            "error_type": "search_error"
        })

def get_full_transcript(chat_id: str) -> str:
    """Lire et retourner la transcription complète d'une conversation archivée."""
    
    # L'authentification a implicitement été vérifiée par l'outil de recherche précédent.
    # On ajoute une vérification de base pour s'assurer que le chemin est sûr.
    if ".." in chat_id or "/" in chat_id or "\\" in chat_id:
        return json.dumps({"status": "error", "message": "Chat ID invalide."})

    transcript_path = os.path.join("transcripts", f"{chat_id}.txt")
    
    try:
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
            return json.dumps({
                "status": "success",
                "chat_id": chat_id,
                "transcript": content
            })
        else:
            return json.dumps({"status": "error", "message": "Transcription non trouvée."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Erreur de lecture: {e}"})

def search_in_transcript(chat_id: str, search_term: str) -> str:
    """Recherche un terme spécifique dans la transcription complète d'une conversation."""
    if ".." in chat_id or "/" in chat_id or "\\" in chat_id:
        return json.dumps({"status": "error", "message": "Chat ID invalide."})

    transcript_path = os.path.join("transcripts", f"{chat_id}.txt")
    
    try:
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Recherche simple du terme dans le contenu
            if search_term.lower() in content.lower():
                # Trouver le contexte autour du terme
                lines = content.split('\n')
                matching_lines = []
                for i, line in enumerate(lines):
                    if search_term.lower() in line.lower():
                        # Ajouter quelques lignes de contexte avant et après
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = '\n'.join(lines[start:end])
                        matching_lines.append(f"Ligne {i+1}: {context}")
                
                return json.dumps({
                    "status": "success",
                    "chat_id": chat_id,
                    "search_term": search_term,
                    "found": True,
                    "matches": matching_lines
                })
            else:
                return json.dumps({
                    "status": "success",
                    "chat_id": chat_id,
                    "search_term": search_term,
                    "found": False,
                    "message": "Terme non trouvé dans la transcription."
                })
        else:
            return json.dumps({"status": "error", "message": "Transcription non trouvée."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Erreur de recherche: {e}"})

def detect_conversation_ids(text: str) -> List[str]:
    """Détecte les IDs de conversation dans un texte."""
    import re
    # Pattern pour détecter les IDs de conversation (ex: conv_20250914_035735_cj3jno)
    pattern = r'conv_[a-zA-Z0-9_]+'
    matches = re.findall(pattern, text)
    return matches

def search_archived_conversations(query: str, limit: int = 10) -> str:
    """Recherche dans toutes les conversations archivées avec une approche exhaustive."""
    user_token = extract_token_from_headers()
    if not user_token:
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"

    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({"status": "error", "message": "Token invalide."})

    team_id = user_info["team_id"]
    storage = get_storage()

    if not storage:
        return json.dumps({
            "status": "error", 
            "message": "Le service de stockage vectoriel n'est pas disponible pour la recherche dans les conversations archivées.",
            "fallback_available": False
        })

    try:
        # Recherche principale
        results = storage.search_conversation_summaries(query, team_id, limit)
        
        # Si peu de résultats, essayer avec des termes plus larges
        if len(results) < 3:
            # Essayer de diviser la requête en mots-clés individuels
            words = query.split()
            if len(words) > 1:
                for word in words:
                    if len(word) > 3:  # Ignorer les mots trop courts
                        additional_results = storage.search_conversation_summaries(word, team_id, limit//2)
                        results.extend(additional_results)
        
        # Dédupliquer les résultats
        seen_chat_ids = set()
        unique_results = []
        for result in results:
            chat_id = result.get('chat_id')
            if chat_id and chat_id not in seen_chat_ids:
                seen_chat_ids.add(chat_id)
                unique_results.append(result)
        
        return json.dumps({
            "status": "success",
            "results": unique_results[:limit],
            "total_found": len(unique_results)
        })
    except Exception as e:
        return json.dumps({
            "status": "error", 
            "message": f"Erreur lors de la recherche dans les conversations archivées: {str(e)}",
            "error_type": "search_error"
        })

def multi_query_search(query: str, max_queries: int = 5) -> str:
    """Effectue plusieurs requêtes de recherche avec différentes approches pour maximiser les résultats."""
    user_token = extract_token_from_headers()
    if not user_token:
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"

    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({"status": "error", "message": "Token invalide."})

    team_id = user_info["team_id"]
    storage = get_storage()

    if not storage:
        return json.dumps({
            "status": "error", 
            "message": "Le service de stockage vectoriel n'est pas disponible.",
            "fallback_available": False
        })

    all_results = []
    search_terms = [query]
    
    # Générer des variantes de recherche
    if len(query.split()) > 1:
        # Ajouter des mots individuels
        for word in query.split():
            if len(word) > 3:
                search_terms.append(word)
        
        # Ajouter des variations
        search_terms.extend([
            query.lower(),
            query.upper(),
            query.replace(" ", "_"),
            query.replace(" ", "-")
        ])
    
    # Effectuer plusieurs recherches
    for i, term in enumerate(search_terms[:max_queries]):
        if term.strip():
            try:
                results = storage.search_conversation_summaries(term, team_id, 5)
                for result in results:
                    result['search_term'] = term
                    result['search_rank'] = i + 1
                all_results.extend(results)
            except Exception as e:
                print(f"⚠️ Erreur recherche avec terme '{term}': {e}")
    
    # Dédupliquer et scorer les résultats
    seen_chat_ids = {}
    for result in all_results:
        chat_id = result.get('chat_id')
        if chat_id:
            if chat_id not in seen_chat_ids:
                seen_chat_ids[chat_id] = result
            else:
                # Garder le résultat avec le meilleur score
                if result.get('score', 0) > seen_chat_ids[chat_id].get('score', 0):
                    seen_chat_ids[chat_id] = result
    
    final_results = list(seen_chat_ids.values())
    final_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return json.dumps({
        "status": "success",
        "results": final_results[:10],
        "total_queries": len(search_terms[:max_queries]),
        "unique_conversations": len(final_results)
    })

def expand_search_keywords(query: str) -> str:
    """Génère des mots-clés de recherche alternatifs et des synonymes pour une requête."""
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        return json.dumps([query])

    ensure_mistral_import()
    if not Mistral:
        return json.dumps([query])

    prompt = f"""Étant donné la requête de recherche de l'utilisateur, génère une liste de 5 à 7 mots-clés et concepts alternatifs pour une recherche sémantique exhaustive. Inclus des synonymes, des termes plus larges, des termes plus spécifiques et des concepts associés.

Requête originale: "{query}"

Retourne UNIQUEMENT une liste JSON de chaînes de caractères. Par exemple: ["motclé1", "motclé2", "concept3"].
"""
    try:
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        keywords_str = response.choices[0].message.content.strip()
        
        if keywords_str.startswith("```json"):
            keywords_str = keywords_str.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        keywords = json.loads(keywords_str)
        if query not in keywords:
            keywords.insert(0, query)
        print(f"🔍 Mots-clés étendus pour '{query}': {keywords}")
        return json.dumps(keywords)
    except Exception as e:
        print(f"❌ Erreur d'expansion de mots-clés: {e}")
        return json.dumps([query])

def extract_keywords_for_tags(content: str) -> str:
    """Extrait des mots-clés pertinents d'un texte pour les utiliser comme tags."""
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        return ""

    ensure_mistral_import()
    if not Mistral:
        return ""
        
    prompt = f"""Extrait les 5 à 10 entités, concepts et mots-clés les plus importants du texte suivant. Les mots-clés doivent être concis (1-3 mots), en minuscules, et pertinents pour une recherche future.

Texte:
"{content[:1000]}"

Retourne une chaîne de caractères unique avec les mots-clés séparés par des virgules. Par exemple: "motclé1,concept2,entité3".
"""
    try:
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2,
        )
        tags_str = response.choices[0].message.content.strip()
        print(f"🏷️ Tags extraits: {tags_str}")
        return tags_str
    except Exception as e:
        print(f"❌ Erreur d'extraction de tags: {e}")
        return ""


# --- Système de Portfolio Utilisateur Dynamique ---

# Répertoire pour les portfolios utilisateur
PORTFOLIOS_DIR = "portfolios"

def ensure_portfolios_dir():
    """Créer le répertoire portfolios s'il n'existe pas"""
    if not os.path.exists(PORTFOLIOS_DIR):
        os.makedirs(PORTFOLIOS_DIR)
        print(f"📁 Répertoire portfolios créé: {PORTFOLIOS_DIR}")

def get_user_portfolio_path(user_id: str) -> str:
    """Obtenir le chemin du fichier portfolio d'un utilisateur"""
    ensure_portfolios_dir()
    return os.path.join(PORTFOLIOS_DIR, f"user_{user_id}.json")

def load_user_portfolio(user_id: str) -> Dict:
    """Charger le portfolio d'un utilisateur"""
    portfolio_path = get_user_portfolio_path(user_id)
    
    if not os.path.exists(portfolio_path):
        # Créer un portfolio par défaut
        default_portfolio = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "profile": {
                "name": "",
                "preferences": [],
                "communication_style": "professional",
                "interests": [],
                "goals": []
            },
            "rules": {
                "response_patterns": {},
                "topics_to_avoid": [],
                "preferred_topics": [],
                "special_instructions": []
            },
            "context": {
                "current_projects": [],
                "recent_activities": [],
                "important_notes": [],
                "relationships": {}
            },
            "events": {
                "upcoming": [],
                "completed": [],
                "recurring": []
            },
            "reminders": {
                "active": [],
                "completed": [],
                "snoozed": []
            },
            "learning": {
                "topics_learned": [],
                "skills_developed": [],
                "knowledge_gaps": []
            }
        }
        save_user_portfolio(user_id, default_portfolio)
        return default_portfolio
    
    try:
        with open(portfolio_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Erreur chargement portfolio {user_id}: {e}")
        return {}

def save_user_portfolio(user_id: str, portfolio: Dict):
    """Sauvegarder le portfolio d'un utilisateur"""
    portfolio_path = get_user_portfolio_path(user_id)
    
    # Mettre à jour le timestamp
    portfolio["updated_at"] = datetime.now().isoformat()
    
    try:
        with open(portfolio_path, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, indent=2, ensure_ascii=False)
        print(f"💾 Portfolio sauvegardé: {portfolio_path}")
    except IOError as e:
        print(f"❌ Erreur sauvegarde portfolio {user_id}: {e}")

def update_user_portfolio(user_id: str, updates: Dict, team_id: str = None) -> str:
    """Mettre à jour le portfolio d'un utilisateur de manière intelligente"""
    # Mode multi-utilisateur : utiliser l'ID fourni directement
    if user_id.startswith("user_") and ("baptiste" in user_id or "henri" in user_id):
        print(f"🔄 Mode multi-utilisateur: {user_id}")
        # Pas de redirection pour Baptiste et Henri
    elif user_id.startswith("user_") and "unified" not in user_id:
        # Redirection uniquement pour les anciens IDs de test
        user_id = "user_unified_test"
        print(f"🔄 Redirection vers user_id unifié: {user_id}")
    
    portfolio = load_user_portfolio(user_id)
    
    # Mise à jour intelligente des sections
    for section, data in updates.items():
        if section in portfolio:
            if isinstance(portfolio[section], dict) and isinstance(data, dict):
                # Mise à jour récursive pour les dictionnaires imbriqués
                for key, value in data.items():
                    if key in portfolio[section]:
                        if isinstance(portfolio[section][key], list) and isinstance(value, list):
                            # Fusionner les listes en évitant les doublons
                            for item in value:
                                if item not in portfolio[section][key]:
                                    portfolio[section][key].append(item)
                        else:
                            portfolio[section][key] = value
                    else:
                        portfolio[section][key] = value
            elif isinstance(portfolio[section], list) and isinstance(data, list):
                portfolio[section].extend(data)
            else:
                portfolio[section] = data
        else:
            portfolio[section] = data
    
    save_user_portfolio(user_id, portfolio)
    
    return json.dumps({
        "status": "success",
        "message": f"Portfolio utilisateur {user_id} mis à jour",
        "updated_sections": list(updates.keys())
    })

def get_user_portfolio_summary(user_id: str, team_id: str = None) -> str:
    """Obtenir un résumé du portfolio d'un utilisateur"""
    # Mode multi-utilisateur : utiliser l'ID fourni directement
    if user_id.startswith("user_") and ("baptiste" in user_id or "henri" in user_id):
        print(f"🔄 Mode multi-utilisateur: {user_id}")
        # Pas de redirection pour Baptiste et Henri
    elif user_id.startswith("user_") and "unified" not in user_id:
        # Redirection uniquement pour les anciens IDs de test
        user_id = "user_unified_test"
        print(f"🔄 Redirection vers user_id unifié: {user_id}")
    
    portfolio = load_user_portfolio(user_id)
    
    if not portfolio:
        return json.dumps({
            "status": "error",
            "message": "Portfolio non trouvé"
        })
    
    summary = {
        "user_id": user_id,
        "profile": portfolio.get("profile", {}),
        "rules_count": len(portfolio.get("rules", {}).get("response_patterns", {})),
        "active_reminders": len(portfolio.get("reminders", {}).get("active", [])),
        "upcoming_events": len(portfolio.get("events", {}).get("upcoming", [])),
        "last_updated": portfolio.get("updated_at", "Unknown")
    }
    
    return json.dumps({
        "status": "success",
        "summary": summary
    })

# --- Branche de Rappels Intelligente ---

# Répertoire pour les rappels
REMINDERS_DIR = "reminders"

def ensure_reminders_dir():
    """Créer le répertoire reminders s'il n'existe pas"""
    if not os.path.exists(REMINDERS_DIR):
        os.makedirs(REMINDERS_DIR)
        print(f"📁 Répertoire reminders créé: {REMINDERS_DIR}")

def get_reminders_file_path(team_id: str) -> str:
    """Obtenir le chemin du fichier de rappels d'une équipe"""
    ensure_reminders_dir()
    return os.path.join(REMINDERS_DIR, f"team_{team_id}_reminders.json")

def load_reminders(team_id: str) -> List[Dict]:
    """Charger les rappels d'une équipe"""
    reminders_path = get_reminders_file_path(team_id)
    
    if not os.path.exists(reminders_path):
        return []
    
    try:
        with open(reminders_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("reminders", [])
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Erreur chargement rappels {team_id}: {e}")
        return []

def save_reminders(team_id: str, reminders: List[Dict]):
    """Sauvegarder les rappels d'une équipe"""
    reminders_path = get_reminders_file_path(team_id)
    
    data = {
        "team_id": team_id,
        "last_updated": datetime.now().isoformat(),
        "reminders": reminders
    }
    
    try:
        with open(reminders_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Rappels sauvegardés: {reminders_path}")
    except IOError as e:
        print(f"❌ Erreur sauvegarde rappels {team_id}: {e}")

def add_reminder(
    title: str,
    description: str,
    due_date: str,
    priority: str = "medium",
    reminder_type: str = "general",
    user_id: str = None,
    team_id: str = None
) -> str:

    """Ajouter un rappel intelligent"""
    # Utiliser la logique unifiée pour obtenir le contexte
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"⏰ Ajout rappel - User: {user_id}, Team: {team_id}")
    
    # Charger les rappels existants
    reminders = load_reminders(team_id)
    
    # Créer le nouveau rappel
    new_reminder = {
        "id": hashlib.md5(f"{title}{due_date}{user_id}".encode()).hexdigest(),
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "type": reminder_type,
        "user_id": user_id,
        "team_id": team_id,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "notifications_sent": []
    }
    
    reminders.append(new_reminder)
    save_reminders(team_id, reminders)
    
    return json.dumps({
        "status": "success",
        "message": f"Rappel '{title}' ajouté",
        "reminder_id": new_reminder["id"]
    })

def analyze_conversation_for_reminders(conversation_text: str, user_id: str, team_id: str) -> List[Dict]:
    """Analyser une conversation pour détecter des rappels potentiels avec Mistral"""
    if not MISTRAL_ENABLED or not MISTRAL_API_KEY:
        return []
    
    ensure_mistral_import()
    if not Mistral:
        return []
    
    current_time = datetime.now()
    prompt = f"""Analyse cette conversation et détecte les événements futurs, rappels, ou engagements qui nécessitent un suivi.

Date et heure actuelle: {current_time.strftime("%Y-%m-%d %H:%M:%S")}

Conversation:
{conversation_text}

Retourne un JSON avec une liste de rappels potentiels. Chaque rappel doit avoir:
- "title": titre court du rappel
- "description": description détaillée
- "due_date": date/heure de l'événement (format ISO ou description naturelle)
- "priority": "low", "medium", "high"
- "type": "meeting", "deadline", "personal", "work", "other"

Format JSON uniquement:
[
  {{
    "title": "Exemple de rappel",
    "description": "Description détaillée",
    "due_date": "2025-09-15T14:00:00",
    "priority": "medium",
    "type": "meeting"
  }}
]

Si aucun rappel n'est détecté, retourne un tableau vide: []"""

    try:
        response = Mistral.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        reminders_text = response.choices[0].message.content.strip()
        
        if reminders_text.startswith("```json"):
            reminders_text = reminders_text.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        reminders = json.loads(reminders_text)
        print(f"🔔 Rappels détectés: {len(reminders)}")
        return reminders
        
    except Exception as e:
        print(f"❌ Erreur analyse rappels: {e}")
        return []

def check_upcoming_reminders(team_id: str, hours_ahead: int = 24) -> List[Dict]:
    """Vérifier les rappels à venir dans les prochaines heures"""
    reminders = load_reminders(team_id)
    current_time = datetime.now()
    upcoming = []
    
    for reminder in reminders:
        if reminder.get("status") != "active":
            continue
            
        try:
            due_date_str = reminder["due_date"]
            
            # Gérer les dates en format texte
            if due_date_str in ["demain", "la semaine prochaine", "le mois prochain"]:
                # Ignorer les rappels avec des dates textuelles pour l'instant
                continue
            
            # Parser les dates ISO avec gestion des fuseaux horaires
            if 'T' in due_date_str:
                if due_date_str.endswith('Z'):
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                elif '+' in due_date_str or due_date_str.count('-') > 2:
                    due_date = datetime.fromisoformat(due_date_str)
                else:
                    # Date ISO locale (sans fuseau)
                    due_date = datetime.fromisoformat(due_date_str)
            else:
                # Date simple (YYYY-MM-DD) - considérer comme minuit local
                due_date = datetime.fromisoformat(due_date_str)
            
            # Calculer la différence en heures (plus précis)
            time_diff_seconds = (due_date - current_time).total_seconds()
            time_diff_hours = time_diff_seconds / 3600
            
            # Vérifier si le rappel est dans la plage de temps
            if 0 <= time_diff_hours <= hours_ahead:
                reminder["hours_until"] = round(time_diff_hours, 1)
                reminder["minutes_until"] = round(time_diff_seconds / 60, 0)
                upcoming.append(reminder)
                
        except Exception as e:
            print(f"⚠️ Erreur parsing date rappel {reminder.get('id')}: {e}")
            continue
    
    return sorted(upcoming, key=lambda x: x.get("hours_until", 0))

def check_upcoming_reminders_tool(team_id: str, hours_ahead: int = 24) -> str:
    """Outil pour vérifier les rappels à venir (retourne du JSON)"""
    upcoming_reminders = check_upcoming_reminders(team_id, hours_ahead)
    
    if not upcoming_reminders:
        return json.dumps({
            "status": "success",
            "message": "Aucun rappel à venir",
            "reminders": [],
            "total": 0
        })
    
    # Formater les rappels pour l'affichage
    formatted_reminders = []
    for reminder in upcoming_reminders:
        minutes_until = reminder.get("minutes_until", 0)
        hours_until = reminder.get("hours_until", 0)
        
        if minutes_until < 60:
            time_str = f"dans {int(minutes_until)} minutes"
        elif hours_until < 24:
            time_str = f"dans {hours_until:.1f} heures"
        else:
            days = hours_until / 24
            time_str = f"dans {days:.1f} jours"
        
        formatted_reminders.append({
            "id": reminder.get("id"),
            "title": reminder.get("title"),
            "description": reminder.get("description"),
            "due_date": reminder.get("due_date"),
            "priority": reminder.get("priority"),
            "time_until": time_str,
            "minutes_until": minutes_until,
            "hours_until": hours_until
        })
    
    return json.dumps({
        "status": "success",
        "message": f"{len(formatted_reminders)} rappel(s) à venir",
        "reminders": formatted_reminders,
        "total": len(formatted_reminders)
    })

def should_show_reminders(chat_id: str, upcoming_reminders: List[Dict]) -> bool:
    """Déterminer si on doit afficher les rappels selon la fréquence"""
    if not upcoming_reminders:
        return False
    
    current_time = datetime.now()
    
    # Initialiser le tracking pour cette conversation
    if chat_id not in reminder_notifications:
        reminder_notifications[chat_id] = {
            "last_reminder_time": None,
            "reminder_count": 0
        }
    
    tracking = reminder_notifications[chat_id]
    
    # Règle 1: Toujours afficher si c'est très urgent (moins de 30 minutes)
    urgent_reminders = [r for r in upcoming_reminders if r.get("minutes_until", 0) <= 30]
    if urgent_reminders:
        print(f"🚨 Rappels urgents détectés: {len(urgent_reminders)} (affichage forcé)")
        return True
    
    # Règle 2: Première fois dans cette conversation
    if tracking["last_reminder_time"] is None:
        tracking["last_reminder_time"] = current_time
        tracking["reminder_count"] = 1
        print(f"🆕 Premier rappel dans cette conversation (affichage autorisé)")
        return True
    
    # Règle 3: Attendre au moins 10 minutes entre les rappels
    time_since_last = (current_time - tracking["last_reminder_time"]).total_seconds() / 60
    if time_since_last < 10:
        print(f"⏰ Rappels limités: {10 - time_since_last:.1f} minutes restantes (affichage bloqué)")
        return False
    
    # Règle 4: Limiter à 3 rappels par conversation
    if tracking["reminder_count"] >= 3:
        print(f"🚫 Limite de rappels atteinte: {tracking['reminder_count']}/3 (affichage bloqué)")
        return False
    
    # Mettre à jour le tracking
    tracking["last_reminder_time"] = current_time
    tracking["reminder_count"] += 1
    print(f"✅ Rappel autorisé: {tracking['reminder_count']}/3")
    return True

def detect_duplicate_reminders(reminders: List[Dict]) -> List[Dict]:
    """Détecter et gérer les rappels en double"""
    if not reminders:
        return reminders
    
    # Grouper par titre et description similaire
    seen_reminders = {}
    unique_reminders = []
    
    for reminder in reminders:
        title = reminder.get("title", "").lower().strip()
        description = reminder.get("description", "").lower().strip()
        
        # Créer une clé unique basée sur le titre et la description
        key = f"{title}_{description}"
        
        if key not in seen_reminders:
            seen_reminders[key] = reminder
            unique_reminders.append(reminder)
        else:
            # Rappel en double détecté - garder le plus proche dans le temps
            existing = seen_reminders[key]
            if reminder.get("minutes_until", 0) < existing.get("minutes_until", 0):
                # Remplacer par le plus proche
                unique_reminders.remove(existing)
                unique_reminders.append(reminder)
                seen_reminders[key] = reminder
                print(f"🔄 Rappel en double détecté et fusionné: {title}")
            else:
                print(f"🔄 Rappel en double ignoré: {title}")
    
    return unique_reminders

def delete_reminder(reminder_id: str, user_id: str = None, team_id: str = None) -> str:
    """Supprimer un rappel"""
    # Utiliser la logique unifiée pour obtenir le contexte
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"🗑️ Suppression rappel - User: {user_id}, Team: {team_id}")
    
    # Charger les rappels existants
    reminders = load_reminders(team_id)
    
    # Trouver et supprimer le rappel
    original_count = len(reminders)
    reminders = [r for r in reminders if r.get("id") != reminder_id]
    
    if len(reminders) == original_count:
        return json.dumps({
            "status": "error",
            "message": "Rappel non trouvé"
        })
    
    # Sauvegarder les rappels mis à jour
    save_reminders(team_id, reminders)
    
    return json.dumps({
        "status": "success",
        "message": f"Rappel {reminder_id} supprimé"
    })

def list_reminders(user_id: str = None, team_id: str = None) -> str:
    """Lister tous les rappels de l'équipe"""
    # Utiliser la logique unifiée pour obtenir le contexte
    if not (user_id and team_id):
        user_token = extract_token_from_headers() or "test-token"
        context = get_unified_team_context(
            user_token=user_token,
            user_id=user_id,
            team_id=team_id
        )
        user_id = context["user_id"]
        team_id = context["team_id"]
        user_name = context["user_name"]
    else:
        user_name = user_id.replace("user_", "").replace("_", " ").title()
    
    print(f"📋 Liste rappels - User: {user_id}, Team: {team_id}")
    reminders = load_reminders(team_id)
    
    return json.dumps({
        "status": "success",
        "reminders": reminders,
        "total": len(reminders)
    })

def delete_all_reminders() -> str:
    """Supprimer tous les rappels de l'équipe"""
    user_token = extract_token_from_headers()
    if not user_token:
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"

    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({"status": "error", "message": "Token invalide."})
    
    team_id = user_info.get("team_id")
    
    # Supprimer tous les rappels
    save_reminders(team_id, [])
    
    return json.dumps({
        "status": "success",
        "message": "Tous les rappels ont été supprimés"
    })

def auto_update_portfolio(user_message: str, user_id: str, team_id: str):
    """Mise à jour automatique du portfolio basée sur l'analyse du message"""
    try:
        portfolio = load_user_portfolio(user_id)
        if not portfolio:
            print(f"⚠️ Portfolio non trouvé pour {user_id}, création d'un nouveau portfolio")
            return
        
        updates = {}
        message_lower = user_message.lower()
        
        # Détection des règles de réponse
        
        # Détection des préférences et informations personnelles
        if any(word in message_lower for word in ["j'aime", "j'adore", "je préfère", "j'apprécie", "je suis", "mon nom", "je m'appelle", "je travaille", "je fais"]):
            if "profile" not in updates:
                updates["profile"] = {}
            if "preferences" not in updates["profile"]:
                updates["profile"]["preferences"] = []
            
            # Extraire les préférences mentionnées
            preferences = []
            if "python" in message_lower:
                preferences.append("Python")
            if "javascript" in message_lower:
                preferences.append("JavaScript")
            if "ia" in message_lower or "intelligence artificielle" in message_lower:
                preferences.append("Intelligence Artificielle")
            if "développement" in message_lower or "dev" in message_lower:
                preferences.append("Développement")
            if "innovation" in message_lower:
                preferences.append("Innovation")
            if "mail" in message_lower or "email" in message_lower:
                preferences.append("Communication par email")
            if "marc" in message_lower:
                preferences.append("Contact avec Marc")
            
            # Détection du nom
            if "je m'appelle" in message_lower or "mon nom est" in message_lower:
                # Extraire le nom après "je m'appelle" ou "mon nom est"
                import re
                name_match = re.search(r"(?:je m'appelle|mon nom est)\s+([a-zA-ZÀ-ÿ\s]+)", message_lower)
                if name_match:
                    name = name_match.group(1).strip().title()
                    updates["profile"]["name"] = name
                    print(f"📋 Nom détecté: {name}")
            
            if preferences:
                updates["profile"]["preferences"].extend(preferences)
                print(f"📋 Préférences détectées: {preferences}")
        
        # Détection des projets
        if any(word in message_lower for word in ["je travaille sur", "mon projet", "je développe", "je crée"]):
            if "context" not in updates:
                updates["context"] = {}
            if "current_projects" not in updates["context"]:
                updates["context"]["current_projects"] = []
            
            # Extraire les projets mentionnés
            projects = []
            if "portfolio" in message_lower:
                projects.append("Système Portfolio")
            if "rappel" in message_lower or "reminder" in message_lower:
                projects.append("Système de Rappels")
            if "chat" in message_lower or "conversation" in message_lower:
                projects.append("Système de Chat IA")
            
            if projects:
                updates["context"]["current_projects"].extend(projects)
                print(f"📋 Projets détectés: {projects}")
        
        # Détection des événements futurs et rappels
        if any(word in message_lower for word in ["demain", "la semaine prochaine", "le mois prochain", "dans", "à", "pour", "rappel", "préviens", "dis-moi", "6h", "7h", "8h", "9h", "10h", "11h", "12h", "13h", "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h", "22h", "23h"]):
            if "events" not in updates:
                updates["events"] = {}
            if "upcoming" not in updates["events"]:
                updates["events"]["upcoming"] = []
            
            # Extraire les événements mentionnés
            events = []
            if "réunion" in message_lower:
                events.append("Réunion prévue")
            if "rendez-vous" in message_lower or "rdv" in message_lower:
                events.append("Rendez-vous")
            if "déjeuner" in message_lower or "dîner" in message_lower:
                events.append("Repas professionnel")
            if "mail" in message_lower and "marc" in message_lower:
                events.append("Envoi de mail à Marc")
            if "préviens" in message_lower or "rappel" in message_lower:
                events.append("Rappel personnalisé")
            
            if events:
                updates["events"]["upcoming"].extend(events)
                print(f"📋 Événements détectés: {events}")
            
            # Détection des rappels temporels spécifiques
            import re
            time_patterns = [
                r"(\d{1,2})h(\d{0,2})",  # 6h11, 14h30, etc.
                r"à\s+(\d{1,2})h(\d{0,2})",  # à 6h11
                r"(\d{1,2}):(\d{2})",  # 6:11
            ]
            
            for pattern in time_patterns:
                matches = re.finditer(pattern, message_lower)
                for match in matches:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if match.group(2) else 0
                    
                    # Créer un rappel automatique
                    current_time = datetime.now()
                    target_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target_time <= current_time:
                        target_time = target_time.replace(day=target_time.day + 1)
                    
                    # Ajouter le rappel
                    reminder_title = "Rappel automatique"
                    if "mail" in message_lower and "marc" in message_lower:
                        reminder_title = "Envoi de mail à Marc"
                    elif "préviens" in message_lower:
                        reminder_title = "Rappel personnalisé"
                    
                    add_reminder(
                        title=reminder_title,
                        description=user_message,
                        due_date=target_time.isoformat(),
                        priority="medium",
                        reminder_type="personal"
                    )
                    print(f"📋 Rappel créé pour {hour:02d}:{minute:02d}")
        
        # Détection du style de communication
        if any(word in message_lower for word in ["formel", "professionnel", "décontracté", "amical"]):
            if "profile" not in updates:
                updates["profile"] = {}
            if "formel" in message_lower or "professionnel" in message_lower:
                updates["profile"]["communication_style"] = "professional"
            elif "décontracté" in message_lower or "amical" in message_lower:
                updates["profile"]["communication_style"] = "friendly"
            print(f"📋 Style de communication détecté: {updates['profile'].get('communication_style')}")
        
        # Détection des intérêts
        if any(word in message_lower for word in ["intéressé par", "passionné de", "fasciné par"]):
            if "profile" not in updates:
                updates["profile"] = {}
            if "interests" not in updates["profile"]:
                updates["profile"]["interests"] = []
            
            interests = []
            if "technologie" in message_lower or "tech" in message_lower:
                interests.append("Technologie")
            if "science" in message_lower:
                interests.append("Science")
            if "art" in message_lower or "créatif" in message_lower:
                interests.append("Art et Créativité")
            if "sport" in message_lower:
                interests.append("Sport")
            
            if interests:
                updates["profile"]["interests"].extend(interests)
                print(f"📋 Intérêts détectés: {interests}")
        
        # Appliquer les mises à jour si il y en a
        if updates:
            print(f"📋 Mise à jour automatique du portfolio: {list(updates.keys())}")
            update_user_portfolio(user_id, updates)
        else:
            print("📋 Aucune mise à jour automatique du portfolio détectée")
            
    except Exception as e:
        print(f"❌ Erreur mise à jour automatique portfolio: {e}")

# --- Ancien système de règles (maintenant dans le portfolio) ---

# Fichier pour stocker les règles personnalisées persistantes (déprécié)
RULES_FILE = "user_rules.json"

def load_user_rules() -> List[Dict]:
    """Charger les règles utilisateur depuis le fichier JSON."""
    if not os.path.exists(RULES_FILE):
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump({"rules": []}, f)
        return []
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("rules", [])
    except (IOError, json.JSONDecodeError):
        return []

def save_user_rules(rules: List[Dict]):
    """Sauvegarder les règles utilisateur dans le fichier JSON."""
    try:
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump({"rules": rules}, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"❌ Erreur sauvegarde règles: {e}")

def add_user_rule(
    pattern: str,
    response: str,
    rule_type: str = "pattern_match",
    description: str = ""
) -> str:
    """Ajouter une règle utilisateur personnalisée."""
    user_token = extract_token_from_headers()
    if not user_token:
        user_token = "user_d8a7996df3c777e9ac2914ef16d5b501"

    user_info = verify_user_token(user_token)
    if not user_info:
        return json.dumps({"status": "error", "message": "Token invalide."})
    
    team_id = user_info.get("team_id")
    user_id = user_info.get("user_id")
    rules = load_user_rules()
    
    # Vérifier les doublons
    rule_updated = False
    for rule in rules:
        if (rule.get("pattern") == pattern and 
            rule.get("team_id") == team_id and
            rule.get("rule_type") == rule_type):
            rule["response"] = response
            rule["updated_at"] = datetime.now().isoformat()
            rule_updated = True
            break
    
    if not rule_updated:
        rules.append({
            "id": hashlib.md5(f"{pattern}{team_id}{rule_type}".encode()).hexdigest(),
            "pattern": pattern,
            "response": response,
            "rule_type": rule_type,
            "description": description,
            "user_id": user_id,
            "team_id": team_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    save_user_rules(rules)
    
    message = f"Règle '{pattern}' mise à jour." if rule_updated else f"Règle '{pattern}' ajoutée."
    return json.dumps({
        "status": "success",
        "message": message
    })

def check_user_portfolio_rules(user_message: str, user_id: str) -> Optional[str]:
    """Vérifier si le message de l'utilisateur déclenche une règle du portfolio."""
    import re
    portfolio = load_user_portfolio(user_id)
    
    if not portfolio:
        return None
    
    response_patterns = portfolio.get("rules", {}).get("response_patterns", {})
    
    if not response_patterns:
        return None

    for pattern, response in response_patterns.items():
        if pattern == "ends_with_quoi":
            # Normaliser le message: enlever la ponctuation finale et les espaces
            normalized_message = re.sub(r'[\s\?\.!]+$', '', user_message).lower()
            if normalized_message.endswith("quoi"):
                return response
        elif pattern == "contains_quoi":
            if "quoi" in user_message.lower():
                return response
        elif pattern == "exact_quoi":
            if user_message.strip().lower() == "quoi":
                return response
        else:
            # Pattern regex personnalisé
            try:
                if re.search(pattern, user_message, re.IGNORECASE):
                    return response
            except re.error:
                # Pattern invalide, ignorer
                continue
    
    return None

def reflective_thinking_process(user_message: str, user_id: str, team_id: str) -> Dict:
    """Processus de réflexion multi-étapes avant de répondre avec portfolio utilisateur."""
    thinking_steps = []
    
    # Étape 1: Analyse du message
    thinking_steps.append(f"🧠 ÉTAPE 1 - Analyse du message: '{user_message}'")
    
    # Étape 2: Vérification du portfolio utilisateur
    thinking_steps.append("🔍 ÉTAPE 2 - Vérification du portfolio utilisateur...")
    portfolio = load_user_portfolio(user_id)
    
    if portfolio:
        thinking_steps.append(f"📋 Portfolio trouvé pour {user_id}")
        
        # Vérifier les règles de réponse
        rule_response = check_user_portfolio_rules(user_message, user_id)
        if rule_response:
            thinking_steps.append(f"✅ Règle portfolio déclenchée: {rule_response}")
            return {
                "response": rule_response,
                "thinking_steps": thinking_steps,
                "rule_triggered": True,
                "confidence": 1.0,
                "source": "portfolio"
            }
        else:
            thinking_steps.append("ℹ️ Aucune règle portfolio déclenchée")
    else:
        thinking_steps.append("⚠️ Portfolio utilisateur non trouvé")
    
    # Étape 3: Analyse sémantique et détection de patterns
    thinking_steps.append("🔍 ÉTAPE 3 - Analyse sémantique du message...")
    
    patterns_detected = []
    if user_message.strip().lower().endswith("quoi"):
        patterns_detected.append("se_termine_par_quoi")
    if "quoi" in user_message.lower():
        patterns_detected.append("contient_quoi")
    if user_message.strip().lower() == "quoi":
        patterns_detected.append("exactement_quoi")
    
    # Détecter les références temporelles pour les rappels
    time_references = detect_time_references(user_message)
    if time_references:
        thinking_steps.append(f"⏰ Références temporelles détectées: {len(time_references)}")
        patterns_detected.append("contient_references_temps")
    
    if patterns_detected:
        thinking_steps.append(f"🎯 Patterns détectés: {patterns_detected}")
    
    # Étape 4: Vérifier les rappels à venir
    thinking_steps.append("🔔 ÉTAPE 4 - Vérification des rappels à venir...")
    upcoming_reminders = check_upcoming_reminders(team_id, hours_ahead=24)
    if upcoming_reminders:
        thinking_steps.append(f"⏰ {len(upcoming_reminders)} rappels à venir détectés")
        patterns_detected.append("rappels_a_venir")
    
    # Étape 5: Déterminer la stratégie de réponse
    thinking_steps.append("🎯 ÉTAPE 5 - Stratégie de réponse déterminée")
    
    search_terms = ["règle", "pattern", "réponse"]
    if time_references:
        search_terms.extend(["rappel", "événement", "temps"])
    
    return {
        "response": None,
        "thinking_steps": thinking_steps,
        "rule_triggered": False,
        "patterns_detected": patterns_detected,
        "time_references": time_references,
        "upcoming_reminders": upcoming_reminders,
        "needs_memory_search": True,
        "search_terms": search_terms,
        "portfolio_available": bool(portfolio)
    }

# Dictionnaire global pour mapper les noms d'outils aux fonctions
available_tools = {
    "add_memory": add_memory,
    "search_memories": search_memories,
    "delete_memory": delete_memory,
    "list_memories": list_memories,
    "get_team_insights": get_team_insights,
    "record_conversation_message": record_conversation_message,
    "get_conversation_summary": get_conversation_summary,
    "list_team_conversations": list_team_conversations,
    "generate_conversation_insights": generate_conversation_insights,
    "end_chat_and_summarize": end_chat_and_summarize,
    "search_past_conversations": search_past_conversations,
    "get_full_transcript": get_full_transcript,
    "search_in_transcript": search_in_transcript,
    "get_conversation_transcript": get_conversation_transcript,
    "list_available_transcripts": list_available_transcripts,
    "search_archived_conversations": search_archived_conversations,
    "multi_query_search": multi_query_search,
    "expand_search_keywords": expand_search_keywords,
    "add_user_rule": add_user_rule,
    # Nouveaux outils portfolio et rappels
    "update_user_portfolio": update_user_portfolio,
    "get_user_portfolio_summary": get_user_portfolio_summary,
    "add_reminder": add_reminder,
    "check_upcoming_reminders": check_upcoming_reminders_tool,
    "list_reminders": list_reminders,
    "delete_reminder": delete_reminder,
    "delete_all_reminders": delete_all_reminders,
}

# --- Fin des nouvelles fonctionnalités ---


if __name__ == "__main__":
    if not IS_LAMBDA:
        print("🎯 Démarrage du serveur MCP Collective Brain...")
    
    # Archivage automatique des conversations existantes
    auto_archive_existing_conversations()
    
    # Initialisation paresseuse
    mcp = initialize_mcp()
    
    if mcp:
        if not IS_LAMBDA:
            print("🚀 Serveur MCP Collective Brain démarré - prêt à recevoir des requêtes")
        mcp.run(transport="streamable-http")
    else:
        if not IS_LAMBDA:
            print("❌ Impossible de démarrer le serveur MCP")
