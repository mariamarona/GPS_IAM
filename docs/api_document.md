# Documentation API - IAMGPS

## 1. Presentation

L'API IAMGPS permet de gerer les utilisateurs, les modules, les zones GPS, les sessions de cours, les pointages et les alertes de fraude.

Adresse locale du backend :

```text
http://127.0.0.1:8000/api/
```

Format des donnees :

```text
JSON
```

## 2. Authentification

### Connexion

```http
POST /api/auth/login/
```

Corps de la requete :

```json
{
  "email": "amadou3@email.com",
  "mot_de_passe": "motdepasse"
}
```

Reponse en cas de succes :

```json
{
  "access": "token_access",
  "refresh": "token_refresh",
  "utilisateur": {
    "id": "uuid",
    "matricule": "ETU003",
    "nom": "Diallo",
    "prenom": "Amadou",
    "email": "amadou3@email.com",
    "role": "STUDENT"
  }
}
```

### Deconnexion

```http
POST /api/auth/logout/
```

Corps de la requete :

```json
{
  "refresh": "token_refresh"
}
```

### Rafraichir le token

```http
POST /api/auth/refresh/
```

Corps de la requete :

```json
{
  "refresh": "token_refresh"
}
```

### Changer le mot de passe

```http
POST /api/auth/change-password/
```

Corps de la requete :

```json
{
  "utilisateur_id": "uuid",
  "ancien_mot_de_passe": "ancien",
  "nouveau_mot_de_passe": "nouveau"
}
```

## 3. Utilisateurs

### Liste des utilisateurs

```http
GET /api/utilisateurs/
```

Filtrer par role :

```http
GET /api/utilisateurs/?role=STUDENT
GET /api/utilisateurs/?role=TEACHER
GET /api/utilisateurs/?role=ADMIN
```

### Creer un utilisateur

```http
POST /api/utilisateurs/
```

Exemple :

```json
{
  "matricule": "ETU004",
  "nom": "Traore",
  "prenom": "Awa",
  "email": "awa@email.com",
  "mot_de_passe": "123456",
  "role": "STUDENT",
  "is_active": true
}
```

### Presence d'un etudiant

```http
GET /api/utilisateurs/{id}/presence/
```

Cette route retourne le taux de presence global et le detail par module.

### Historique d'un etudiant

```http
GET /api/utilisateurs/{id}/historique/
```

Filtres possibles :

```http
GET /api/utilisateurs/{id}/historique/?module_id=1
GET /api/utilisateurs/{id}/historique/?date_debut=2026-06-01&date_fin=2026-06-30
```

### Absences d'un etudiant

```http
GET /api/utilisateurs/{id}/absences/
```

### Sessions creees par un enseignant

```http
GET /api/utilisateurs/{id}/sessions/
```

## 4. Modules

### Liste des modules

```http
GET /api/modules/
```

### Creer un module

```http
POST /api/modules/
```

Exemple :

```json
{
  "code": "INFO101",
  "intitule": "Systemes d'information",
  "enseignant": "uuid_enseignant",
  "seuil_presence_pct": 75
}
```

### Etudiants inscrits a un module

```http
GET /api/modules/{id}/etudiants/
```

### Statistiques d'un module

```http
GET /api/modules/{id}/stats/
```

## 5. Zones GPS

### Liste des zones

```http
GET /api/zones/
```

### Creer une zone GPS

```http
POST /api/zones/
```

Exemple :

```json
{
  "nom": "Campus IAM Bamako",
  "latitude": 12.639232,
  "longitude": -8.002889,
  "rayon_m": 100
}
```

Une zone GPS represente l'espace geographique autorise pour une session de presence.

## 6. Sessions

### Liste des sessions

```http
GET /api/sessions/
```

Filtres possibles :

```http
GET /api/sessions/?module_id=1
GET /api/sessions/?statut=EN_COURS
GET /api/sessions/?date=2026-07-01
```

### Sessions du jour

```http
GET /api/sessions/aujourd-hui/
```

### Creer une session

```http
POST /api/sessions/
```

Exemple :

```json
{
  "module": 1,
  "zone": 1,
  "created_by": "uuid_enseignant",
  "date": "2026-07-01",
  "heure_debut": "08:00:00",
  "heure_fin": "10:00:00",
  "statut": "PLANIFIE"
}
```

### Demarrer une session

```http
POST /api/sessions/{id}/demarrer/
```

### Terminer une session

```http
POST /api/sessions/{id}/terminer/
```

### Annuler une session

```http
POST /api/sessions/{id}/annuler/
```

### Liste des absents d'une session

```http
GET /api/sessions/{id}/absents/
```

## 7. Pointages

### Valider un pointage GPS

```http
POST /api/pointages/valider/
```

Corps de la requete :

```json
{
  "utilisateur_id": "uuid_etudiant",
  "session_id": 1,
  "latitude": 12.639200,
  "longitude": -8.002800,
  "precision_gps_m": 12.5
}
```

Reponse possible si l'etudiant est dans la zone :

```json
{
  "pointage_id": 10,
  "statut": "VALIDE",
  "dans_zone": true,
  "distance_m": 25.4,
  "rayon_zone_m": 100.0,
  "est_fraude": false,
  "message": "Pointage valide"
}
```

Reponse possible si l'etudiant est hors zone :

```json
{
  "pointage_id": 11,
  "statut": "HORS_ZONE",
  "dans_zone": false,
  "distance_m": 450.2,
  "rayon_zone_m": 100.0,
  "est_fraude": true,
  "message": "Hors zone GPS - alerte creee"
}
```

### Statistiques des pointages

```http
GET /api/pointages/stats/
```

Filtres possibles :

```http
GET /api/pointages/stats/?utilisateur_id=uuid
GET /api/pointages/stats/?session_id=1
```

### Pointages par session

```http
GET /api/pointages/par-session/?session_id=1
```

## 8. Alertes de fraude

### Liste des alertes

```http
GET /api/alertes/
```

Filtres possibles :

```http
GET /api/alertes/?statut=NON_TRAITEE
GET /api/alertes/?type_fraude=hors_zone
GET /api/alertes/?niveau_severite=ELEVE
GET /api/alertes/?utilisateur_id=uuid
```

### Alertes non traitees

```http
GET /api/alertes/non-traitees/
```

### Tableau de bord des alertes

```http
GET /api/alertes/dashboard/
```

### Alertes par etudiant

```http
GET /api/alertes/par-etudiant/?utilisateur_id=uuid
```

### Traiter une alerte

```http
PATCH /api/alertes/{id}/traiter/
```

Exemple :

```json
{
  "statut": "FRAUDE_CONFIRMEE",
  "traite_par": "uuid_admin",
  "commentaire": "L'etudiant etait hors de la zone autorisee."
}
```

Statuts acceptes :

- `EN_INVESTIGATION` ;
- `FRAUDE_CONFIRMEE` ;
- `FAUSSE_ALERTE`.

## 9. Inscriptions

### Liste des inscriptions

```http
GET /api/inscriptions/
```

### Inscrire un etudiant a un module

```http
POST /api/inscriptions/
```

Exemple :

```json
{
  "etudiant": "uuid_etudiant",
  "module": 1,
  "is_active": true
}
```

## 10. Codes de reponse courants

- `200 OK` : requete traitee avec succes ;
- `201 Created` : ressource creee ;
- `400 Bad Request` : donnees invalides ou manquantes ;
- `401 Unauthorized` : identifiants invalides ;
- `403 Forbidden` : compte desactive ou action interdite ;
- `404 Not Found` : ressource introuvable.

## 11. Remarque sur la detection de fraude

Dans la version actuelle, la detection de fraude repose principalement sur la distance entre la position GPS de l'etudiant et la zone autorisee. Une evolution importante du projet consiste a ajouter un module de scoring plus avance prenant en compte :

- la distance a la zone ;
- la precision GPS ;
- l'heure du pointage ;
- les doublons ;
- les coordonnees identiques repetees ;
- l'historique de comportement de l'etudiant.
