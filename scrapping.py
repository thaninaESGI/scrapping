import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import sys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.cloud import storage
from google.cloud import secretmanager
import json
import logging
from dotenv import load_dotenv
from google.oauth2 import service_account

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

gcp_project = "pa-ingestion"




def get_secret(secret_id, version_id='latest'):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/pa-ingestion/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    secret = response.payload.data.decode('UTF-8')
    logging.debug(f"Secret fetched: {secret}")
    return secret

def load_service_account_key():
    try:
        secret_data = get_secret('my-service-account-key')
        key_data = json.loads(secret_data)
        logging.debug("Key data successfully loaded from Secret Manager.")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to load key data: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error retrieving key data: {e}")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_info(key_data)
    logging.debug("Credentials created successfully from key data.")
    return credentials

credentials = load_service_account_key()



# Obtenir le nom du bucket depuis Secret Manager
bucket_name = "ingestion_bucket_1"

# Configure the path to your Chrome driver
driver_path = "/usr/local/bin/chromedriver"

# Initialize Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Set preferences to allow multiple downloads
prefs = {
    "profile.default_content_setting_values.automatic_downloads": 1,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "download.default_content_setting_values.notifications": 2,
    "download.default_directory": os.path.join(os.getcwd(), "pdf_downloads")
}
options.add_experimental_option("prefs", prefs)

service = ChromeService(executable_path=driver_path)
driver = webdriver.Chrome(service=service, options=options)

def upload_to_gcs(bucket_name, source_folder):
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)
    
    for filename in os.listdir(source_folder):
        if filename.endswith(".pdf"):
            blob = bucket.blob(filename)
            blob.upload_from_filename(os.path.join(source_folder, filename))
            print(f"Uploaded {filename} to {bucket_name}")

try:
    # Ouvre la page de connexion
    driver.get("https://myges.fr/common/student-documents")
    print("Page de connexion ouverte.")

    # Attend que les champs de connexion soient disponibles
    wait = WebDriverWait(driver, 20)
    email_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    password_field = driver.find_element(By.NAME, "password")
    print("Champs de connexion trouvés.")

    # Remplit les champs de connexion et soumet le formulaire
    username = "slena"
    password = "sandro!LEna35763576"
    
    email_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    print("Identifiants remplis et connexion envoyée.")

    # Attend que la connexion soit terminée
    time.sleep(4)
    print("Connexion effectuée.")

    # Navigue vers la page des documents
    driver.get("https://myges.fr/common/student-documents")
    print("Page des documents ouverte.")

    # Attend que la page se charge
    time.sleep(2)
    print("Page des documents chargée.")

    # Collecte toutes les URLs des fichiers PDF
    def collect_pdf_urls():
        pdf_urls = set()
        try:
            rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tr")))
            print(f"Nombre total de lignes trouvées : {len(rows)}")
            for row in rows:
                try:
                    icons = row.find_elements(By.XPATH, ".//a[contains(@href, 'private')]")
                    for icon in icons:
                        pdf_url = icon.get_attribute('href')
                        if pdf_url:
                            pdf_urls.add(pdf_url)
                except Exception as e:
                    print(f"Erreur lors de la collecte des URLs dans la ligne : {e}")
        except Exception as e:
            print(f"Erreur lors de la collecte des lignes : {e}")
        return pdf_urls

    pdf_urls = collect_pdf_urls()
    print(f"Nombre total de fichiers PDF trouvés : {len(pdf_urls)}")

    # Vérifier si des PDF ont été trouvés avant de continuer
    if not pdf_urls:
        raise Exception("Aucun fichier PDF trouvé. Vérifiez si vous êtes bien connecté et si des documents sont disponibles.")

    # Fonction pour télécharger les fichiers PDF
    def download_pdfs(urls):
        for pdf_url in urls:
            try:
                print(f"Tentative de téléchargement du fichier : {pdf_url}")
                driver.get(pdf_url)  # Navigue directement vers l'URL du PDF
                time.sleep(3)  # Attend que le téléchargement se termine
                print(f"Téléchargement terminé pour : {pdf_url}")
            except Exception as e:
                print(f"Erreur lors du téléchargement du fichier : {pdf_url} : {e}")

    download_pdfs(pdf_urls)

    # Upload les fichiers téléchargés vers Google Cloud Storage
    upload_to_gcs(bucket_name, os.path.join(os.getcwd(), "pdf_downloads"))
    print("Upload vers Google Cloud Storage terminé.")

except Exception as e:
    print(f"Erreur durant l'exécution du script : {e}")

finally:
    driver.quit()
    print("Script terminé, navigateur fermé.")
