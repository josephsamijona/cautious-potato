import os

# Structure des dossiers et fichiers
structure = {
    "views": ["__init__.py", "auth.py", "client.py", "translator.py", "admin.py", "common.py"],
    "forms": ["__init__.py", "auth.py", "client.py", "translator.py", "admin.py"],
    "urls": ["__init__.py", "auth.py", "client.py", "translator.py", "admin.py"],
    "services": ["__init__.py", "email.py", "notification.py", "payment.py", "document.py"],
    "utils": ["__init__.py", "decorators.py", "validators.py", "helpers.py"],
    "tasks": ["__init__.py", "notifications.py"],
}

# Créer les dossiers et fichiers
def create_structure(base_path="."):
    for folder, files in structure.items():
        folder_path = os.path.join(base_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        for file in files:
            file_path = os.path.join(folder_path, file)
            with open(file_path, "w") as f:
                pass  # Crée un fichier vide
                print(f"Created: {file_path}")

if __name__ == "__main__":
    create_structure()
