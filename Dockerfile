# Utiliser une image Python de base
FROM python:3.10-slim

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libasound2 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    chromium-driver \
    && apt-get clean

# Copier et installer ChromeDriver
COPY chromedriver /usr/local/bin/chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires dans l'image
COPY . /app
# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Définir les variables d'environnement pour Google Cloud
CMD ["python", "scrapping.py"]
