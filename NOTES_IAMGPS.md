# Notes IAMGPS — mise à jour de l'interface admin

Ce projet est votre projet complet, **déjà à jour** avec toutes les modifications
demandées. Rien à copier-coller : lancez simplement le backend et le frontend comme
d'habitude.

## Démarrage rapide

```bash
# 1. Backend
cd backend
python manage.py migrate
python manage.py seed_demo        # crée des comptes + données de démo (voir plus bas)
python manage.py runserver

# 2. Frontend (dans un autre terminal)
cd frontend/iamgps-web
cp .env.example .env              # ajuster VITE_API_URL si besoin
npm install
npm run dev
```

## Se connecter

Après `seed_demo`, ouvrez l'application : vous arrivez maintenant sur un **écran de
connexion** (avant, elle sautait directement sur le tableau de bord — c'est corrigé).
Connectez-vous avec (les emails exacts s'affichent dans la console si des noms
similaires existaient déjà en base) :

| Rôle | Email | Mot de passe |
|---|---|---|
| Admin | `admin@iamgps.com` | `@iamgps123` |
| Enseignant | `ibrahim@iamgps.com` ou `seydou@iamgps.com` | `@ensgps123` |
| Étudiant | `ibrahim.s@iamgps.com`, `nabintou@iamgps.com`, `oumar@iamgps.com`, `aboubacar@iamgps.com`, `djeneba@iamgps.com`, `aissata@iamgps.com` | `@etugps123` |

## Ce qui a été fait

- **Espace étudiant web** (`/etudiant`, React) toujours présent et fonctionnel (créé
  précédemment) — mais suite à votre choix, c'est **l'application Flutter** qui devient
  le canal principal pour le pointage GPS étudiant (plus adapté : GPS plus précis,
  fonctionnement hors-ligne possible). Le web reste focalisé sur l'administration.
- **Application mobile Flutter (`mobile_flutter/`)** — c'est maintenant elle qui gère le
  pointage étudiant avec GPS + carte :
  - **Bouton "Démarrer la séance" sur chaque module** (écran enseignant) : avant, ce
    bouton n'existait que si une séance était déjà planifiée aujourd'hui — il fallait
    zéro action possible si ce n'était pas le cas. Il est maintenant sur **chaque
    module** dans "Mes modules", et crée la séance du jour à la volée si besoin (en
    reprenant la zone/horaire de la dernière séance connue), puis la démarre en un clic.
    Nouveau endpoint backend : `POST /api/modules/{id}/demarrer-session/`.
  - **Carte de la zone IAM** ajoutée sur l'écran de pointage étudiant (OpenStreetMap,
    gratuit, sans clé API) : affiche le centre de la zone autorisée, son rayon, et la
    position de l'étudiant une fois localisée. Nouvelles dépendances `flutter_map` et
    `latlong2` ajoutées à `pubspec.yaml`.

  ⚠️ **Important** : contrairement au backend Django et au frontend React (que j'ai pu
  compiler et tester réellement avant chaque livraison), je n'ai pas Flutter/Dart
  installé dans mon environnement de travail, donc **je n'ai pas pu compiler ce code
  mobile**. Je l'ai écrit avec soin en suivant le style déjà présent dans votre projet,
  mais si `flutter pub get` ou `flutter run` remonte une erreur, envoyez-la-moi
  exactement pour que je corrige.
- **Déconnexion fonctionnelle** : le bouton appelle `/api/auth/logout/`, invalide le
  jeton et vous renvoie à l'écran de connexion.
- Toutes les requêtes API envoient désormais le jeton d'authentification
  (`Authorization: Bearer ...`), et une session expirée/invalide vous renvoie
  automatiquement vers `/login`.
- **Tableau de bord**, **Alertes de fraude** et **Gestion des cours** reconstruits pour
  correspondre à vos maquettes de référence (`app_v6.zip`), avec panneau d'analyse IA
  détaillée par facteurs, panneau "Voir le modèle IA", actions contextuelles par statut.
- Nouveau champ `analyse_ia` sur les alertes (facteurs pondérés + recommandation),
  rempli automatiquement par `seed_demo` pour les 5 scénarios de démonstration.
- Pas de notion de "Groupe" (retiré à votre demande).
- Les identifiants générés par `seed_demo` suivent vos conventions : matricules à
  partir de `202122`, emails `prenom@iamgps.com`, mots de passe par rôle.

⚠️ Note de sécurité : côté backend, les endpoints API acceptent encore les requêtes
sans jeton valide (`AllowAny` partout) — le frontend exige bien la connexion, mais
l'API elle-même n'est pas encore verrouillée. Si vous voulez qu'on restreigne l'API
aux utilisateurs authentifiés, dites-le-moi, c'est une modification séparée.

⚠️ Le modèle IA (précision, facteurs, etc.) est **illustratif** — il n'y a pas encore de
vrai modèle de machine learning entraîné dans ce projet (`backend/api/fraud_detection.py`
est vide). Les scores affichés viennent des données de démonstration.
