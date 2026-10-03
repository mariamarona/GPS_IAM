# Guide utilisateur - IAMGPS

## 1. Presentation de l'application

IAMGPS est un systeme de gestion de presence qui permet de verifier la presence des etudiants grace a la localisation GPS. Le systeme aide aussi l'administration a detecter des comportements suspects, comme un pointage effectue hors de la zone autorisee.

L'application comporte trois profils :

- Etudiant ;
- Enseignant ;
- Administrateur.

Chaque profil dispose de fonctionnalites adaptees a son role.

## 2. Connexion

Pour acceder a l'application :

1. Ouvrir l'application IAMGPS.
2. Choisir le profil correspondant : Etudiant, Enseignant ou Admin.
3. Saisir l'identifiant ou l'adresse email.
4. Saisir le mot de passe.
5. Cliquer sur le bouton de connexion.

Si la connexion echoue, verifier :

- que le serveur est lance ;
- que l'email est correct ;
- que le mot de passe est correct ;
- que le compte est actif.

## 3. Profil Etudiant

Le profil etudiant permet de :

- consulter les sessions disponibles ;
- effectuer un pointage GPS ;
- consulter son historique de presence ;
- consulter son taux de presence par module ;
- voir les absences detectees.

### Effectuer un pointage

Pour pointer sa presence :

1. Se connecter avec un compte etudiant.
2. Aller dans l'ecran de pointage.
3. Selectionner la session en cours.
4. Autoriser l'acces a la localisation.
5. Cliquer sur le bouton pour obtenir la position GPS.
6. Cliquer sur le bouton de pointage.

Le systeme calcule automatiquement la distance entre la position de l'etudiant et la zone GPS de la session.

Si l'etudiant est dans la zone autorisee, le pointage est valide.

Si l'etudiant est hors zone, le pointage est signale comme suspect et une alerte de fraude est creee.

### Historique de presence

L'etudiant peut consulter :

- la date des pointages ;
- le module concerne ;
- la session concernee ;
- le statut du pointage ;
- la distance par rapport a la zone autorisee.

## 4. Profil Enseignant

Le profil enseignant permet de :

- consulter les sessions du jour ;
- demarrer une session ;
- terminer une session ;
- suivre le nombre de presents ;
- consulter les absents d'une session ;
- consulter les statistiques d'un module.

### Demarrer une session

Pour demarrer une session :

1. Se connecter avec un compte enseignant.
2. Ouvrir le tableau de bord enseignant.
3. Choisir une session planifiee.
4. Cliquer sur demarrer.

Une fois la session demarree, les etudiants peuvent effectuer leur pointage.

### Terminer une session

Pour terminer une session :

1. Selectionner une session en cours.
2. Cliquer sur terminer.
3. Le systeme calcule le resume de la session : inscrits, presents, hors zone et absents.

## 5. Profil Administrateur

Le profil administrateur permet de :

- consulter les statistiques generales ;
- consulter les utilisateurs ;
- consulter les modules ;
- consulter les sessions ;
- consulter les alertes de fraude ;
- traiter les alertes.

### Gestion des alertes de fraude

Une alerte de fraude peut avoir plusieurs statuts :

- Non traitee ;
- En investigation ;
- Fraude confirmee ;
- Fausse alerte.

Pour traiter une alerte :

1. Ouvrir le tableau de bord administrateur.
2. Consulter la liste des alertes non traitees.
3. Lire les informations du pointage : etudiant, session, distance, zone.
4. Choisir le statut approprie.
5. Ajouter un commentaire si necessaire.
6. Enregistrer le traitement.

## 6. Fonctionnement du pointage GPS

Lorsqu'un etudiant pointe sa presence, l'application envoie au serveur :

- l'identifiant de l'etudiant ;
- l'identifiant de la session ;
- la latitude ;
- la longitude ;
- la precision GPS.

Le serveur compare ensuite la position de l'etudiant avec la zone GPS de la session.

La distance est calculee en metres. Si la distance est inferieure ou egale au rayon autorise, le pointage est valide. Sinon, le pointage est marque comme hors zone.

## 7. Detection de fraude

Dans la version actuelle, le systeme detecte principalement la fraude liee au pointage hors zone.

Exemples de situations suspectes :

- l'etudiant pointe loin du campus ;
- l'etudiant pointe hors de la salle ou du perimetre autorise ;
- la precision GPS est tres faible ;
- plusieurs pointages sont effectues avec des coordonnees identiques ;
- un pointage est effectue en dehors de l'horaire normal.

Une evolution du systeme consiste a attribuer un score de suspicion a chaque pointage. Ce score peut aider l'administrateur a prioriser les alertes.

## 8. Bonnes pratiques d'utilisation

Pour les etudiants :

- activer la localisation avant le pointage ;
- rester dans la zone autorisee ;
- pointer pendant la session ;
- eviter de partager ses identifiants.

Pour les enseignants :

- creer les sessions avec les bonnes heures ;
- associer chaque session a la bonne zone GPS ;
- terminer les sessions apres le cours ;
- verifier les absents.

Pour les administrateurs :

- verifier regulierement les alertes ;
- confirmer seulement les fraudes justifiees ;
- corriger les fausses alertes ;
- maintenir les comptes utilisateurs a jour.

## 9. Messages courants

### Impossible de contacter le serveur

Le backend n'est peut-etre pas lance ou l'adresse API est incorrecte.

### Permission de localisation refusee

L'utilisateur doit autoriser l'application a acceder a la position GPS.

### Hors zone GPS

L'etudiant est en dehors du perimetre autorise pour la session.

### Session non trouvee

La session selectionnee n'existe pas ou n'est pas disponible.

### Identifiant ou mot de passe incorrect

Les informations de connexion ne correspondent pas a un compte actif.

## 10. Limites actuelles

Le systeme fonctionne deja comme une base de gestion de presence par GPS, mais certaines ameliorations sont recommandees :

- renforcer la securite des API ;
- ajouter un vrai module de scoring IA ;
- ajouter des tests automatiques ;
- documenter les jeux de donnees ;
- ameliorer la gestion des cas hors ligne ;
- mieux gerer la precision GPS en interieur.
