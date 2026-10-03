# Guide d'installation - IAMGPS

## 1. Objectif

Ce guide explique comment installer et lancer le systeme IAMGPS, une application de gestion de presence basee sur la geolocalisation GPS et la detection de fraude.

Le projet contient trois parties principales :

- un backend Django REST pour les donnees, l'authentification et les API ;
- une application mobile Flutter pour les etudiants, enseignants et administrateurs ;
- une base de donnees MySQL pour stocker les utilisateurs, sessions, pointages et alertes.

## 2. Prerequis

Installer les outils suivants :

- Python 3.10 ou version superieure ;
- MySQL Server ;
- Flutter SDK ;
- Git ;
- un editeur de code comme Visual Studio Code.

## 3. Installation du backend

Ouvrir un terminal dans le dossier du projet, puis aller dans le dossier backend :

```bash
cd backend
```

Creer un environnement virtuel Python :

```bash
python -m venv venv
```

Activer l'environnement virtuel sous Windows :

```bash
venv\Scripts\activate
```

Installer les dependances :

```bash
pip install -r requirements.txt
```

Les principales dependances utilisees sont :

- Django ;
- Django REST Framework ;
- django-cors-headers ;
- djangorestframework-simplejwt ;
- bcrypt ;
- mysqlclient.

## 4. Configuration de la base de donnees

Dans MySQL, creer une base de donnees :

```sql
CREATE DATABASE pointage_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Verifier ensuite les informations de connexion dans :

```text
backend/scolarite_api/settings.py
```

Configuration actuelle :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pointage_db',
        'USER': 'root',
        'PASSWORD': 'ProjetMaster',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

Adapter le mot de passe si necessaire selon votre installation MySQL.

## 5. Migration de la base de donnees

Depuis le dossier backend :

```bash
python manage.py makemigrations
python manage.py migrate
```

Pour creer un compte administrateur Django :

```bash
python manage.py createsuperuser
```

## 6. Lancement du backend

Demarrer le serveur Django :

```bash
python manage.py runserver
```

Le backend sera disponible a l'adresse :

```text
http://127.0.0.1:8000/
```

Les API principales seront disponibles sous :

```text
http://127.0.0.1:8000/api/
```

## 7. Installation de l'application Flutter

Aller dans le dossier mobile :

```bash
cd mobile_flutter
```

Installer les dependances Flutter :

```bash
flutter pub get
```

Lancer l'application en mode web :

```bash
flutter run -d chrome
```

Pour lancer l'application sur Android, utiliser un emulateur ou un telephone connecte :

```bash
flutter run
```

## 8. Configuration de l'adresse API

Dans Flutter Web ou Desktop, l'adresse du backend doit etre :

```dart
const String BASE_URL = 'http://127.0.0.1:8000';
```

Dans un emulateur Android, l'adresse peut etre :

```dart
const String BASE_URL = 'http://10.0.2.2:8000';
```

Sur un telephone physique, il faut utiliser l'adresse IP du PC sur le reseau local, par exemple :

```dart
const String BASE_URL = 'http://192.168.1.10:8000';
```

## 9. Verification rapide

Avant de tester la connexion dans l'application, verifier que :

- le serveur Django est lance ;
- MySQL est lance ;
- le compte utilisateur existe dans la base ;
- l'adresse `BASE_URL` correspond au support utilise ;
- le mot de passe saisi correspond au mot de passe enregistre.

## 10. Problemes frequents

### Impossible de contacter le serveur

Causes possibles :

- le backend Django n'est pas lance ;
- l'application utilise `10.0.2.2` dans Chrome au lieu de `127.0.0.1` ;
- le port 8000 est bloque ou deja utilise ;
- le telephone et le PC ne sont pas sur le meme reseau.

### Identifiant ou mot de passe incorrect

Causes possibles :

- l'email n'existe pas ;
- le mot de passe est incorrect ;
- le mot de passe n'a pas ete chiffre avec bcrypt ;
- le compte utilisateur est desactive.

### Erreur de localisation

Causes possibles :

- la localisation est desactivee ;
- l'utilisateur a refuse la permission GPS ;
- le navigateur ou l'appareil ne donne pas une precision suffisante ;
- le test est effectue en interieur avec un signal GPS faible.
