"""
Script pour initialiser la base de données
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from app.config import settings

def create_database():
    """Crée la base de données si elle n'existe pas"""
    # Parser l'URL de la base de données
    # Format: mysql+pymysql://user:password@host:port/database
    db_url = settings.DATABASE_URL
    
    # Extraire les informations de connexion
    parts = db_url.replace("mysql+pymysql://", "").split("/")
    connection_part = parts[0]
    db_name = parts[1].split("?")[0] if len(parts) > 1 else "clinique_db"
    
    # Extraire user, password, host, port
    if "@" in connection_part:
        user_pass, host_port = connection_part.split("@")
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
        else:
            user = user_pass
            password = ""
    else:
        user = "root"
        password = ""
        host_port = connection_part
    
    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host = host_port
        port = 3306
    
    print(f"Connexion à MySQL sur {host}:{port} avec l'utilisateur {user}")
    
    try:
        # Connexion sans spécifier de base de données
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Créer la base de données si elle n'existe pas
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ Base de données '{db_name}' créée ou déjà existante")
        
        cursor.close()
        connection.close()
        
        return True
        
    except pymysql.Error as e:
        print(f"✗ Erreur lors de la création de la base de données: {e}")
        return False

if __name__ == "__main__":
    if create_database():
        print("\n✓ Initialisation de la base de données réussie!")
        print("Vous pouvez maintenant exécuter les migrations avec: alembic upgrade head")
    else:
        print("\n✗ Échec de l'initialisation de la base de données")
        print("Vérifiez que MySQL est démarré et que les informations de connexion sont correctes dans .env")
