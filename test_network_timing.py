#!/usr/bin/env python3
"""
Script de test réseau simple pour mesurer les temps de connexion
Ne nécessite pas d'installer qdrant_client
"""

import time
import socket
import urllib.parse
import urllib.request
import ssl
from datetime import datetime

def test_tcp_connection():
    """Test de connexion TCP simple"""
    print("🔌 Test de connexion TCP")
    print("-" * 30)
    
    url = "https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333"
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 443
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    
    # Test TCP
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        tcp_time = time.time() - start_time
        
        if result == 0:
            print(f"✅ Connexion TCP réussie en {tcp_time:.3f}s")
            return tcp_time
        else:
            print(f"❌ Connexion TCP échouée (code: {result})")
            return None
            
    except Exception as e:
        print(f"❌ Erreur TCP: {e}")
        return None

def test_https_request():
    """Test de requête HTTPS"""
    print("\n🌐 Test de requête HTTPS")
    print("-" * 30)
    
    url = "https://f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io:6333/collections"
    
    # Test HTTPS
    start_time = time.time()
    try:
        # Créer un contexte SSL
        ssl_context = ssl.create_default_context()
        
        # Créer la requête
        request = urllib.request.Request(url)
        request.add_header('api-key', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.dTojrUAcLmujBlbrJyQ_oILGXQcWVhF7B8sOTWiIyLw')
        
        # Exécuter la requête
        with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
            data = response.read()
            https_time = time.time() - start_time
            
            print(f"✅ Requête HTTPS réussie en {https_time:.3f}s")
            print(f"   Status: {response.status}")
            print(f"   Taille réponse: {len(data)} bytes")
            return https_time
            
    except Exception as e:
        https_time = time.time() - start_time
        print(f"❌ Erreur HTTPS après {https_time:.3f}s: {e}")
        return None

def test_multiple_connections():
    """Test de plusieurs connexions pour mesurer la stabilité"""
    print("\n🔄 Test de connexions multiples")
    print("-" * 30)
    
    times = []
    for i in range(5):
        print(f"Connexion {i+1}/5...", end=" ")
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io", 6333))
            sock.close()
            
            connect_time = time.time() - start_time
            
            if result == 0:
                times.append(connect_time)
                print(f"{connect_time:.3f}s ✅")
            else:
                print(f"Échec ❌")
                
        except Exception as e:
            print(f"Erreur ❌")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 Statistiques:")
        print(f"   Moyenne: {avg_time:.3f}s")
        print(f"   Minimum: {min_time:.3f}s")
        print(f"   Maximum: {max_time:.3f}s")
        print(f"   Connexions réussies: {len(times)}/5")
        
        return avg_time
    else:
        print("❌ Aucune connexion réussie")
        return None

def test_dns_resolution():
    """Test de résolution DNS"""
    print("\n🔍 Test de résolution DNS")
    print("-" * 30)
    
    hostname = "f22a8bbc-f8d2-4282-8b09-eec1afac3074.europe-west3-0.gcp.cloud.qdrant.io"
    
    start_time = time.time()
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        dns_time = time.time() - start_time
        
        print(f"✅ DNS résolu en {dns_time:.3f}s")
        print(f"   IP: {ip}")
        return dns_time
        
    except Exception as e:
        dns_time = time.time() - start_time
        print(f"❌ Erreur DNS après {dns_time:.3f}s: {e}")
        return None

def analyze_results(tcp_time, https_time, avg_time, dns_time):
    """Analyse des résultats"""
    print("\n" + "=" * 50)
    print("📊 ANALYSE DES RÉSULTATS")
    print("=" * 50)
    
    if tcp_time:
        print(f"Connexion TCP: {tcp_time:.3f}s")
        if tcp_time > 5:
            print("  ❌ PROBLÈME: Connexion TCP très lente (>5s)")
        elif tcp_time > 3:
            print("  ⚠️ ATTENTION: Connexion TCP lente (>3s)")
        else:
            print("  ✅ OK: Connexion TCP acceptable")
    
    if https_time:
        print(f"Requête HTTPS: {https_time:.3f}s")
        if https_time > 10:
            print("  ❌ PROBLÈME: Requête HTTPS très lente (>10s)")
        elif https_time > 5:
            print("  ⚠️ ATTENTION: Requête HTTPS lente (>5s)")
        else:
            print("  ✅ OK: Requête HTTPS acceptable")
    
    if avg_time:
        print(f"Connexions moyennes: {avg_time:.3f}s")
        if avg_time > 5:
            print("  ❌ PROBLÈME: Connexions instables (>5s)")
        elif avg_time > 3:
            print("  ⚠️ ATTENTION: Connexions lentes (>3s)")
        else:
            print("  ✅ OK: Connexions stables")
    
    if dns_time:
        print(f"Résolution DNS: {dns_time:.3f}s")
        if dns_time > 2:
            print("  ❌ PROBLÈME: DNS très lent (>2s)")
        elif dns_time > 1:
            print("  ⚠️ ATTENTION: DNS lent (>1s)")
        else:
            print("  ✅ OK: DNS rapide")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS:")
    print("-" * 30)
    
    if tcp_time and tcp_time > 3:
        print("• Réduire le timeout Qdrant à 5s maximum")
        print("• Considérer l'utilisation d'un CDN ou d'un proxy")
    
    if https_time and https_time > 5:
        print("• Optimiser les requêtes HTTPS")
        print("• Vérifier la configuration réseau")
    
    if avg_time and avg_time > 3:
        print("• Implémenter un système de retry avec backoff")
        print("• Considérer un cache local")
    
    print("• Utiliser l'initialisation paresseuse (lazy loading)")
    print("• Implémenter un fallback vers stockage local")

if __name__ == "__main__":
    print("🚀 Test de connectivité réseau Qdrant")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Tests
    dns_time = test_dns_resolution()
    tcp_time = test_tcp_connection()
    https_time = test_https_request()
    avg_time = test_multiple_connections()
    
    # Analyse
    analyze_results(tcp_time, https_time, avg_time, dns_time)
    
    print("\n🎯 CONCLUSION:")
    print("=" * 50)
    if tcp_time and tcp_time > 3:
        print("❌ Le problème vient probablement de la lenteur de connexion réseau")
        print("   La connexion TCP prend plus de 3 secondes, ce qui peut causer")
        print("   des timeouts dans AWS Lambda.")
    else:
        print("✅ La connectivité réseau semble acceptable")
        print("   Le problème pourrait venir d'ailleurs (imports, initialisation, etc.)")
