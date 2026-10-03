"""
Commande de seed — génère un jeu de données de démonstration complet pour IAMGPS.

Usage :
    python manage.py seed_demo

Conventions imposées :
    - matricule : séquentiel, commence à 202122 (202122, 202123, 202124, ...)
    - email     : prenom@iamgps.com (désaccentué, en minuscule ; suffixe si collision)
    - mot de passe (en clair, avant hash bcrypt) :
        - Administrateur : @iamgps123
        - Enseignant     : @ensgps123
        - Étudiant       : @etugps123

La commande est idempotente pour les utilisateurs (identifiés par prénom+nom+rôle) :
la relancer ne crée pas de doublons. Les sessions/pointages/alertes de la semaine en
cours sont recréés à chaque exécution afin que le tableau de bord affiche toujours des
données récentes.
"""
import bcrypt
import random
import unicodedata
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import Utilisateur, Module, ZoneGPS, Session, Pointage, AlerteFraude, Inscription


PASSWORDS = {
    Utilisateur.Role.ADMIN:   '@iamgps123',
    Utilisateur.Role.TEACHER: '@ensgps123',
    Utilisateur.Role.STUDENT: '@etugps123',
}

MATRICULE_DEPART = 202122


def _hash(raw_password):
    return bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _sans_accents(texte):
    return unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode('ascii').lower()


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (utilisateurs, cours, zones GPS, sessions, pointages, alertes)."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._matricule_compteur = MATRICULE_DEPART
            self._emails_utilises = set(Utilisateur.objects.values_list('email', flat=True))

            admin  = self._creer_utilisateur('Admin', 'Système', Utilisateur.Role.ADMIN)
            konare = self._creer_utilisateur('Ibrahim', 'KONARE', Utilisateur.Role.TEACHER)
            daou   = self._creer_utilisateur('Seydou', 'DAOU', Utilisateur.Role.TEACHER)

            sissoko   = self._creer_utilisateur('Ibrahim', 'SISSOKO', Utilisateur.Role.STUDENT)
            nabintou  = self._creer_utilisateur('Nabintou', 'TRAORE', Utilisateur.Role.STUDENT)
            oumar     = self._creer_utilisateur('Oumar', 'DIARRA', Utilisateur.Role.STUDENT)
            aboubacar = self._creer_utilisateur('Aboubacar', 'TRAORE', Utilisateur.Role.STUDENT)
            diakite   = self._creer_utilisateur('Djénèba', 'DIAKITE', Utilisateur.Role.STUDENT)
            aissata   = self._creer_utilisateur('Aissata', 'DIARRA', Utilisateur.Role.STUDENT)

            liste_etudiants = [
                (sissoko, 0.85), (nabintou, 0.95), (oumar, 0.75),
                (aboubacar, 0.90), (diakite, 0.65), (aissata, 0.92),
            ]

            # ── Zones GPS + Modules (5 cours, comme dans la maquette) ──
            modules_def = [
                ('SYC-BI',   'Power Business Intelligence (Power BI)', konare, 0,
                 datetime.time(9, 0),  datetime.time(12, 0)),
                ('SYC-BCT',  'Bonnes pratiques de codage et tests',    konare, 0,
                 datetime.time(13, 0), datetime.time(16, 0)),
                ('SYC-IOT',  "Introduction à l'internet des objets",   daou,   1,
                 datetime.time(9, 0),  datetime.time(12, 0)),
                ('SYC-RC',   'Réseaux de capteurs',                    daou,   1,
                 datetime.time(13, 0), datetime.time(16, 0)),
                ('SYC-ELEC', 'Électronique (Circuit logique)',         daou,   2,
                 datetime.time(15, 0), datetime.time(18, 0)),
            ]

            modules = []
            for i, (code, intitule, enseignant, jour_idx, h_debut, h_fin) in enumerate(modules_def):
                zone = self._creer_zone(f'Amphithéâtre IAM {i + 1}', 12.6398, -8.0268, 50)
                module, _ = Module.objects.get_or_create(
                    code=code, defaults={'intitule': intitule, 'enseignant': enseignant, 'seuil_presence_pct': 75}
                )
                modules.append({'module': module, 'zone': zone, 'jour_idx': jour_idx,
                                 'heure_debut': h_debut, 'heure_fin': h_fin, 'enseignant': enseignant})

            # ── Inscriptions : tous les étudiants dans tous les cours ──
            for m in modules:
                for etudiant, _ in liste_etudiants:
                    Inscription.objects.get_or_create(etudiant=etudiant, module=m['module'])

            # ── Sessions de la semaine en cours (dates ≤ aujourd'hui) ──
            # La session du jour (si elle tombe aujourd'hui) reste "EN_COURS" et SANS
            # pointages pré-remplis, pour que le bouton de pointage soit testable en vrai.
            # Les sessions des jours précédents sont marquées "TERMINE" avec des pointages
            # simulés, pour peupler le graphique hebdomadaire et l'historique.
            #
            # IMPORTANT : le statut n'est fixé QUE lors de la création de la séance.
            # Une séance déjà existante n'est plus jamais retouchée ici — avant, relancer
            # seed_demo un autre jour recalculait "aujourd'hui" et repassait de force une
            # séance EN_COURS (avec les vrais pointages des étudiants) en TERMINE, ce qui
            # donnait l'impression que les séances se désactivaient toutes seules. Désormais,
            # seuls les boutons Démarrer / Terminer / Annuler changent le statut d'une séance.
            aujourdhui = timezone.localdate()
            sessions_par_module = {}
            sessions_du_jour = set()
            for m in modules:
                date_session = self._date_recente_pour_jour(m['jour_idx'])
                est_aujourdhui = date_session == aujourdhui
                statut_cible = Session.Statut.EN_COURS if est_aujourdhui else Session.Statut.TERMINE
                session, _ = Session.objects.get_or_create(
                    module=m['module'], zone=m['zone'], date=date_session,
                    heure_debut=m['heure_debut'], heure_fin=m['heure_fin'],
                    defaults={'created_by': m['enseignant'], 'statut': statut_cible},
                )
                sessions_par_module[m['module'].code] = session
                if est_aujourdhui:
                    sessions_du_jour.add(session.id)

            # ── Pointages "normaux" (aléatoire pondéré par la fiabilité de l'étudiant) ──
            # On ne pré-remplit PAS la session du jour : elle doit rester "vierge" pour la démo.
            random.seed(42)
            for m in modules:
                session = sessions_par_module[m['module'].code]
                if session.id in sessions_du_jour:
                    continue
                for etudiant, fiab in liste_etudiants:
                    if Pointage.objects.filter(utilisateur=etudiant, session=session).exists():
                        continue
                    tirage = random.random()
                    debut_dt = datetime.datetime.combine(session.date, session.heure_debut)
                    if tirage < fiab:
                        ts = timezone.make_aware(debut_dt + datetime.timedelta(minutes=random.randint(1, 8)))
                        Pointage.objects.create(
                            utilisateur=etudiant, session=session, timestamp=ts,
                            latitude=m['zone'].latitude, longitude=m['zone'].longitude,
                            precision_gps_m=8.0, distance_zone_m=round(random.uniform(2, 25), 1),
                            statut=Pointage.Statut.VALIDE,
                        )
                    elif tirage < fiab + 0.08:
                        ts = timezone.make_aware(debut_dt + datetime.timedelta(minutes=random.randint(16, 35)))
                        Pointage.objects.create(
                            utilisateur=etudiant, session=session, timestamp=ts,
                            latitude=m['zone'].latitude, longitude=m['zone'].longitude,
                            precision_gps_m=9.0, distance_zone_m=round(random.uniform(2, 25), 1),
                            statut=Pointage.Statut.VALIDE,
                        )
                    # sinon : absent, aucun pointage créé

            # ── 5 alertes de fraude (scénarios repris de la maquette) ──
            # Si un des scénarios tombe sur la session du jour (encore vierge), on saute cette
            # alerte plutôt que de "pré-pointer" un étudiant à sa place sur une session en cours.
            self._creer_alertes_demo(sessions_par_module, sessions_du_jour, diakite, oumar, sissoko)

        self.stdout.write(self.style.SUCCESS(
            "\nJeu de données de démonstration créé avec succès.\n"
            f"  Mot de passe Admin      : {PASSWORDS[Utilisateur.Role.ADMIN]}\n"
            f"  Mot de passe Enseignant : {PASSWORDS[Utilisateur.Role.TEACHER]}\n"
            f"  Mot de passe Étudiant   : {PASSWORDS[Utilisateur.Role.STUDENT]}\n"
            "  (voir les emails générés dans les lignes ci-dessus)"
        ))

    # ─────────────────────────────────────────────
    #  Helpers utilisateurs
    # ─────────────────────────────────────────────
    def _next_matricule(self):
        while Utilisateur.objects.filter(matricule=str(self._matricule_compteur)).exists():
            self._matricule_compteur += 1
        matricule = str(self._matricule_compteur)
        self._matricule_compteur += 1
        return matricule

    def _make_email(self, prenom, nom):
        base = _sans_accents(prenom).replace(' ', '').replace('-', '')
        candidats = [f'{base}@iamgps.com', f'{base}.{_sans_accents(nom)[:1]}@iamgps.com']
        candidat = None
        for c in candidats:
            if c not in self._emails_utilises:
                candidat = c
                break
        if candidat is None:
            i = 2
            while f'{base}{i}@iamgps.com' in self._emails_utilises:
                i += 1
            candidat = f'{base}{i}@iamgps.com'
        self._emails_utilises.add(candidat)
        return candidat

    def _creer_utilisateur(self, prenom, nom, role):
        existant = Utilisateur.objects.filter(prenom=prenom, nom=nom, role=role).first()
        if existant:
            return existant
        email = self._make_email(prenom, nom)
        matricule = self._next_matricule()
        utilisateur = Utilisateur.objects.create(
            matricule=matricule, prenom=prenom, nom=nom, email=email,
            mot_de_passe=_hash(PASSWORDS[role]), role=role, is_active=True,
        )
        self.stdout.write(f'  + {role:8s} {prenom} {nom:10s} matricule={matricule:8s} email={email}')
        return utilisateur

    def _creer_zone(self, nom, lat, lon, rayon):
        zone, _ = ZoneGPS.objects.get_or_create(
            nom=nom, defaults={'latitude': lat, 'longitude': lon, 'rayon_m': rayon}
        )
        return zone

    def _date_recente_pour_jour(self, jour_idx):
        """Renvoie la date la plus récente (≤ aujourd'hui) correspondant au jour de semaine demandé
        (0=Lundi ... 4=Vendredi), pour que les sessions de démo restent toujours 'passées'."""
        aujourdhui = timezone.localdate()
        delta = (aujourdhui.weekday() - jour_idx) % 7
        return aujourdhui - datetime.timedelta(days=delta)

    # ─────────────────────────────────────────────
    #  Alertes de fraude de démonstration
    # ─────────────────────────────────────────────
    def _creer_alertes_demo(self, sessions_par_module, sessions_du_jour, diakite, oumar, sissoko):
        scenarios = [
            {
                'module': 'SYC-BI', 'etudiant': diakite, 'minutes': 5,
                'type': 'hors_zone', 'niveau': 'CRITIQUE', 'statut': 'NON_TRAITEE', 'score': 96,
                'distance_m': 350.0,
                'commentaire': "Pointage effectué à 350m de la zone autorisée (rayon: 50m). "
                               "Position GPS incompatible avec l'Amphithéâtre IAM Bamako.",
                'analyse_ia': {
                    'risk_score': 0.96,
                    'model_version': 'IAMGPS-FraudNet v2.1',
                    'recommendation': "Fraude très probable. Recommandation : confirmer la fraude et "
                                       "convoquer l'étudiant.",
                    'factors': [
                        {'name': 'Distance hors zone', 'weight': 0.40, 'value': 0.98,
                         'description': 'Distance 7x supérieure au rayon autorisé'},
                        {'name': 'Historique fraude', 'weight': 0.20, 'value': 0.75,
                         'description': '2 alertes précédentes sur les 30 derniers jours'},
                        {'name': 'Cohérence temporelle', 'weight': 0.15, 'value': 0.90,
                         'description': 'Pointage 5 min après le début — déplacement physique impossible'},
                        {'name': 'Précision GPS', 'weight': 0.15, 'value': 0.85,
                         'description': 'Précision GPS anormalement élevée (±2m) pour cette distance'},
                        {'name': 'Pattern comportemental', 'weight': 0.10, 'value': 0.70,
                         'description': 'Absences fréquentes suivies de pointages suspects'},
                    ],
                },
            },
            {
                'module': 'SYC-IOT', 'etudiant': oumar, 'minutes': 3,
                'type': 'coords_fixes', 'niveau': 'ELEVE', 'statut': 'EN_INVESTIGATION', 'score': 88,
                'distance_m': 5.0,
                'commentaire': "3 pointages consécutifs avec coordonnées identiques (12.639200, -8.002900). "
                               "Suspicion d'utilisation d'un faux GPS ou application de spoofing.",
                'analyse_ia': {
                    'risk_score': 0.88,
                    'model_version': 'IAMGPS-FraudNet v2.1',
                    'recommendation': "Spoofing GPS probable. Vérifier l'appareil de l'étudiant et comparer "
                                       "avec les logs réseau.",
                    'factors': [
                        {'name': 'Coordonnées statiques', 'weight': 0.35, 'value': 0.95,
                         'description': 'Même position exacte sur 3 sessions différentes — probabilité naturelle < 0.1%'},
                        {'name': 'Variance GPS nulle', 'weight': 0.25, 'value': 0.92,
                         'description': 'Aucune micro-variation GPS détectée (normalement ±3-5m)'},
                        {'name': 'Empreinte appareil', 'weight': 0.20, 'value': 0.75,
                         'description': "Signature d'application de mock GPS détectée dans les métadonnées"},
                        {'name': 'Historique étudiant', 'weight': 0.20, 'value': 0.80,
                         'description': 'Taux de présence en baisse de 15% ce mois-ci'},
                    ],
                },
            },
            {
                'module': 'SYC-BCT', 'etudiant': diakite, 'minutes': 45,
                'type': 'heure_invalide', 'niveau': 'MOYEN', 'statut': 'NON_TRAITEE', 'score': 72,
                'distance_m': 10.0,
                'commentaire': "Pointage effectué 45 minutes après le début de la session. "
                               "Le délai maximum autorisé est de 15 minutes.",
                'analyse_ia': {
                    'risk_score': 0.72,
                    'model_version': 'IAMGPS-FraudNet v2.1',
                    'recommendation': 'Retard récurrent. Possiblement légitime mais pattern à surveiller.',
                    'factors': [
                        {'name': 'Retard excessif', 'weight': 0.40, 'value': 0.85,
                         'description': 'Pointage à +45min — seuil max : 15min'},
                        {'name': 'Position valide', 'weight': 0.30, 'value': 0.20,
                         'description': 'Position GPS dans la zone autorisée (facteur atténuant)'},
                        {'name': 'Fréquence retards', 'weight': 0.30, 'value': 0.65,
                         'description': '4 retards sur les 10 dernières sessions'},
                    ],
                },
            },
            {
                'module': 'SYC-RC', 'etudiant': oumar, 'minutes': 2,
                'type': 'doublon', 'niveau': 'ELEVE', 'statut': 'FRAUDE_CONFIRMEE', 'score': 91,
                'distance_m': 5.0,
                'commentaire': "Double pointage détecté pour la même session. Premier pointage à 09:02, "
                               "second à 09:03 depuis un appareil différent.",
                'analyse_ia': {
                    'risk_score': 0.91,
                    'model_version': 'IAMGPS-FraudNet v2.1',
                    'recommendation': "Fraude confirmée par l'IA. Un étudiant a pointé pour un autre.",
                    'factors': [
                        {'name': 'Double pointage', 'weight': 0.40, 'value': 0.95,
                         'description': '2 pointages en 1 minute pour la même session'},
                        {'name': 'Appareils multiples', 'weight': 0.30, 'value': 0.90,
                         'description': 'Device IDs différents — tentative de pointage pour un tiers'},
                        {'name': 'Positions divergentes', 'weight': 0.30, 'value': 0.88,
                         'description': "Les 2 positions sont à 120m l'une de l'autre"},
                    ],
                },
            },
            {
                'module': 'SYC-ELEC', 'etudiant': sissoko, 'minutes': 6,
                'type': 'spoofing_gps', 'niveau': 'MOYEN', 'statut': 'FAUSSE_ALERTE', 'score': 58,
                'distance_m': 15.0,
                'commentaire': "Saut de position GPS détecté: déplacement de 2.3km en 30 secondes "
                               "(vitesse physiquement impossible).",
                'analyse_ia': {
                    'risk_score': 0.58,
                    'model_version': 'IAMGPS-FraudNet v2.1',
                    'recommendation': 'Probablement une erreur GPS en intérieur. Recommandation : classer en '
                                       'fausse alerte.',
                    'factors': [
                        {'name': 'Vitesse de déplacement', 'weight': 0.35, 'value': 0.80,
                         'description': 'Déplacement 2.3km/30s — possible erreur GPS en intérieur'},
                        {'name': 'Correction rapide', 'weight': 0.25, 'value': 0.30,
                         'description': 'Position corrigée en 10s — typique d\'un recalibrage GPS'},
                        {'name': 'Historique fiable', 'weight': 0.25, 'value': 0.15,
                         'description': 'Aucune alerte précédente — étudiant fiable'},
                        {'name': 'Environnement', 'weight': 0.15, 'value': 0.45,
                         'description': 'Zone connue pour interférences GPS (bâtiment béton)'},
                    ],
                },
            },
        ]

        for s in scenarios:
            # Idempotence réelle : si CETTE alerte de démo (même étudiant + même type +
            # même module) existe déjà — peu importe la date/session — on ne la recrée pas.
            # Sans ce garde-fou, relancer seed_demo un jour différent créait une nouvelle
            # session "du jour" donc une nouvelle alerte en double.
            deja_existante = AlerteFraude.objects.filter(
                type_fraude=s['type'],
                pointage__utilisateur=s['etudiant'],
                pointage__session__module__code=s['module'],
            ).exists()
            if deja_existante:
                continue

            session = sessions_par_module[s['module']]
            if session.id in sessions_du_jour:
                continue  # session du jour laissée vierge pour la démo du bouton de pointage

            # Réutilise le pointage "normal" déjà généré s'il existe, sinon en crée un dédié.
            pointage = Pointage.objects.filter(utilisateur=s['etudiant'], session=session).first()
            debut_dt = datetime.datetime.combine(session.date, session.heure_debut)
            ts = timezone.make_aware(debut_dt + datetime.timedelta(minutes=s['minutes']))
            if pointage is None:
                pointage = Pointage.objects.create(
                    utilisateur=s['etudiant'], session=session, timestamp=ts,
                    latitude=session.zone.latitude, longitude=session.zone.longitude,
                    precision_gps_m=12.0, distance_zone_m=s['distance_m'],
                    statut=Pointage.Statut.VALIDE if s['type'] != 'hors_zone' else Pointage.Statut.HORS_ZONE,
                )
            else:
                pointage.timestamp = ts
                pointage.distance_zone_m = s['distance_m']
                if s['type'] == 'hors_zone':
                    pointage.statut = Pointage.Statut.HORS_ZONE
                pointage.save()

            if hasattr(pointage, 'alerte_fraude'):
                continue  # une alerte OneToOne existe déjà pour ce pointage

            AlerteFraude.objects.create(
                pointage=pointage, type_fraude=s['type'], score_ia=s['score'],
                niveau_severite=s['niveau'], statut=s['statut'], commentaire=s['commentaire'],
                analyse_ia=s['analyse_ia'],
            )