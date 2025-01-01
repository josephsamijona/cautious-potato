import os

def create_filesystem():
    base_dir = "templates"
    structure = {
        "base": [
            "base.html",
            "client_base.html",
            "translator_base.html",
            "admin_base.html",
        ],
        "auth": [
            "login.html",
            "register.html",
            "verify_otp.html",
        ],
        "profile": [
            "client.html",
            "translator.html",
        ],
        "client": [
            "dashboard.html",
            "quotes.html",
            "translations.html",
        ],
        "translator": [
            "dashboard.html",
            "translations.html",
            "payments.html",
        ],
        "admin": [
            "dashboard.html",
            "users.html",
            "translations.html",
            "quotes.html",
        ],
        "components": {
            "client": ["nav.html"],
            "translator": ["nav.html"],
            "admin": ["nav.html"],
            "common": ["forms.html", "cards.html"],
        },
    }

    def create_files(path, files):
        for file in files:
            file_path = os.path.join(path, file)
            with open(file_path, "w") as f:
                f.write(f"<!-- {file} -->\n")

    def create_structure(base_path, struct):
        for folder, content in struct.items():
            folder_path = os.path.join(base_path, folder)
            os.makedirs(folder_path, exist_ok=True)
            if isinstance(content, list):
                create_files(folder_path, content)
            elif isinstance(content, dict):
                create_structure(folder_path, content)

    os.makedirs(base_dir, exist_ok=True)
    create_structure(base_dir, structure)

if __name__ == "__main__":
    create_filesystem()
    print("Filesystem and files created successfully.")
