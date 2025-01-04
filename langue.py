import os
import django
from datetime import datetime
import sys

# Configuration initiale
print(f"[{datetime.now()}] Starting language population script...")
print(f"[{datetime.now()}] Setting up Django environment...")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "translation_platform.settings")
django.setup()

from translations.models import Language

def populate_languages():
    print(f"\n[{datetime.now()}] Starting language population process...")
    print("=" * 50)

    languages_data = [
    {"name": "Français", "code": "fr"},
    {"name": "English", "code": "en"},
    {"name": "Español", "code": "es"},
    {"name": "Deutsch", "code": "de"},
    {"name": "Italiano", "code": "it"},
    {"name": "Português", "code": "pt"},
    {"name": "Русский", "code": "ru"},
    {"name": "中文 (简体)", "code": "zh-hans"},
    {"name": "中文 (繁體)", "code": "zh-hant"},
    {"name": "日本語", "code": "ja"},
    {"name": "한국어", "code": "ko"},
    {"name": "العربية", "code": "ar"},
    {"name": "हिन्दी", "code": "hi"},
    {"name": "Türkçe", "code": "tr"},
    {"name": "Nederlands", "code": "nl"},
    {"name": "Polski", "code": "pl"},
    {"name": "Svenska", "code": "sv"},
    {"name": "Dansk", "code": "da"},
    {"name": "Suomi", "code": "fi"},
    {"name": "Ελληνικά", "code": "el"},
    {"name": "Tiếng Việt", "code": "vi"},
    {"name": "ไทย", "code": "th"},
    {"name": "Bahasa Indonesia", "code": "id"},
    {"name": "Čeština", "code": "cs"},
    {"name": "Magyar", "code": "hu"},
    {"name": "Română", "code": "ro"},
    {"name": "українська", "code": "uk"},
    {"name": "Hrvatski", "code": "hr"},
    {"name": "Norsk", "code": "no"},
    {"name": "עברית", "code": "he"},
    {"name": "বাংলা", "code": "bn"},
    {"name": "فارسی", "code": "fa"},
    {"name": "български", "code": "bg"},
    {"name": "Català", "code": "ca"},
    {"name": "Eesti", "code": "et"},
    {"name": "Slovenčina", "code": "sk"},
    {"name": "Lietuvių", "code": "lt"},
    {"name": "Latviešu", "code": "lv"},
    {"name": "Slovenščina", "code": "sl"},
    {"name": "Македонски", "code": "mk"},
    {"name": "Монгол", "code": "mn"},
    {"name": "ភាសាខ្មែរ", "code": "km"},
    {"name": "नेपाली", "code": "ne"},
    {"name": "සිංහල", "code": "si"},
    {"name": "ລາວ", "code": "lo"},
    {"name": "မြန်မာ", "code": "my"},
    {"name": "Հայերեն", "code": "hy"},
    {"name": "ქართული", "code": "ka"},
    {"name": "Кыргызча", "code": "ky"},
    {"name": "O'zbek", "code": "uz"},
    {"name": "Afrikaans", "code": "af"},
    {"name": "Kiswahili", "code": "sw"},
    {"name": "Gaeilge", "code": "ga"},
    {"name": "Cymraeg", "code": "cy"},
    {"name": "Gàidhlig", "code": "gd"},
    {"name": "Euskara", "code": "eu"},
    {"name": "Galego", "code": "gl"},
    {"name": "Malti", "code": "mt"},
    {"name": "Shqip", "code": "sq"},
    {"name": "Português do Brasil", "code": "pt-br"},
    {"name": "Español de México", "code": "es-mx"},
    {"name": "العربية السعودية", "code": "ar-sa"},
    {"name": "Bosnian", "code": "bs"},
    {"name": "Српски", "code": "sr"},
    {"name": "Wolof", "code": "wo"},
    {"name": "Yorùbá", "code": "yo"},
    {"name": "Igbo", "code": "ig"},
    {"name": "Urdu", "code": "ur"},
    {"name": "Punjabi", "code": "pa"},
    {"name": "Tamil", "code": "ta"},
    {"name": "Telugu", "code": "te"},
    {"name": "Kannada", "code": "kn"},
    {"name": "Malayalam", "code": "ml"},
    {"name": "Gujarati", "code": "gu"},
    {"name": "Marathi", "code": "mr"},
    {"name": "Kreyòl Ayisyen", "code": "ht"}
 ]


    total_languages = len(languages_data)
    languages_created = 0
    languages_updated = 0
    errors = []

    print(f"\n[{datetime.now()}] Found {total_languages} languages to process")
    print("=" * 50)

    for index, lang_data in enumerate(languages_data, 1):
        try:
            print(f"\n[{datetime.now()}] Processing {index}/{total_languages}: {lang_data['name']} ({lang_data['code']})")
            
            # Vérification de l'existence
            existing = Language.objects.filter(code=lang_data["code"]).exists()
            status = "Updating" if existing else "Creating"
            print(f"Status: {status} language entry...")

            # Création ou mise à jour
            language, created = Language.objects.update_or_create(
                code=lang_data["code"],
                defaults={
                    "name": lang_data["name"],
                    "is_active": True
                }
            )
            
            if created:
                languages_created += 1
                print(f"✓ Successfully created: {lang_data['name']}")
            else:
                languages_updated += 1
                print(f"✓ Successfully updated: {lang_data['name']}")

            # Barre de progression
            progress = (index / total_languages) * 100
            sys.stdout.write('\rProgress: [%-50s] %.1f%%' % ('=' * int(progress/2), progress))
            sys.stdout.flush()

        except Exception as e:
            error_msg = f"Error processing {lang_data['name']}: {str(e)}"
            errors.append(error_msg)
            print(f"\n⚠ {error_msg}")

    # Résumé final
    print("\n\n" + "=" * 50)
    print(f"\n[{datetime.now()}] Operation completed!")
    print("\nSummary:")
    print(f"- Total languages processed: {total_languages}")
    print(f"- New languages created: {languages_created}")
    print(f"- Existing languages updated: {languages_updated}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nNo errors encountered during the process.")

    success_rate = ((languages_created + languages_updated) / total_languages) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    print("\n" + "=" * 50)

if __name__ == "__main__":
    try:
        populate_languages()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        sys.exit(1)