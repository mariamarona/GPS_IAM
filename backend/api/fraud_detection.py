"""
Module de détection de fraude — IAMGPS.

Combine :
- des RÈGLES explicites pour déterminer LE TYPE de fraude (hors_zone, doublon,
  coords_fixes, heure_invalide, spoofing_gps) — une information catégorielle, donc
  naturellement gérée par des règles plutôt que par un modèle ;
- un VRAI modèle de machine learning entraîné (scikit-learn) pour calculer un score
  de risque continu (0-100).

Pourquoi une détection d'anomalies non supervisée (IsolationForest) au démarrage,
plutôt qu'un classifieur classique fraude/légitime ?
Un classifieur supervisé a besoin de nombreux exemples étiquetés des deux classes
pour être fiable. Au tout début du projet, ces données n'existent pas. L'IsolationForest
apprend le comportement "normal" à partir de TOUS les pointages, sans étiquette,
ce qui la rend utilisable dès le premier jour.

Dès qu'au moins MIN_EXEMPLES_SUPERVISE alertes ont été confirmées ou rejetées par un
administrateur (voir management/commands/train_fraud_model.py), un second modèle
supervisé (RandomForestClassifier) est entraîné en plus et prend le relais — le
système progresse avec l'usage réel, sans jamais prétendre être plus fiable qu'il ne
l'est réellement.

Aucun modèle entraîné trouvé sur disque → on retombe sur un score heuristique
(pondération manuelle, explicite) le temps que `train_fraud_model` soit lancée au
moins une fois.
"""
import datetime
import os

from django.conf import settings
from django.utils import timezone

from .utils import calculer_distance_metres

MODEL_DIR              = os.path.join(settings.BASE_DIR, 'api', 'ml_models')
ISOLATION_FOREST_PATH  = os.path.join(MODEL_DIR, 'fraud_isolation_forest.joblib')
RANDOM_FOREST_PATH     = os.path.join(MODEL_DIR, 'fraud_random_forest.joblib')

RETARD_TOLERANCE_MIN     = 10     # minutes au-delà desquelles un retard est suspect
VITESSE_SPOOFING_KMH     = 120.0  # vitesse humainement/en véhicule normal improbable sur un campus
COORDS_IDENTIQUES_METRES = 3.0    # deux positions à moins de 3m sont considérées "identiques"
COORDS_REPETEES_SEUIL    = 2      # nombre de répétitions avant de qualifier "coordonnées fixes"

FEATURE_NAMES = [
    'distance_ratio', 'precision_gps_m', 'minutes_retard',
    'vitesse_kmh', 'coords_repetees', 'is_doublon',
]


def _load_model(path):
    """Charge un modèle joblib s'il existe, sans jamais planter si le fichier est
    absent ou corrompu (on retombe simplement sur le niveau de détection suivant)."""
    if not os.path.exists(path):
        return None
    try:
        import joblib
        return joblib.load(path)
    except Exception:
        return None


def extraire_features(pointage, session, zone, distance_m):
    """Calcule les variables numériques utilisées à la fois par les règles et par le
    modèle ML, à partir d'UN pointage (déjà créé ou sur le point de l'être)."""
    from .models import Pointage  # import local pour éviter un import circulaire

    debut_dt = datetime.datetime.combine(session.date, session.heure_debut)
    ts = pointage.timestamp
    ts_naive = timezone.localtime(ts).replace(tzinfo=None) if timezone.is_aware(ts) else ts
    minutes_retard = max(0.0, (ts_naive - debut_dt).total_seconds() / 60.0)

    # Vitesse depuis le pointage précédent du même étudiant (si moins de 3h d'écart).
    precedent = (
        Pointage.objects.filter(utilisateur=pointage.utilisateur)
        .exclude(id=pointage.id)
        .order_by('-timestamp')
        .first()
    )
    vitesse_kmh = 0.0
    if precedent is not None:
        delta_s = abs((pointage.timestamp - precedent.timestamp).total_seconds())
        if 0 < delta_s <= 3 * 3600:
            dist_prev_m = calculer_distance_metres(
                pointage.latitude, pointage.longitude, precedent.latitude, precedent.longitude
            )
            vitesse_kmh = (dist_prev_m / 1000.0) / (delta_s / 3600.0)

    # Nombre de pointages passés (30 derniers jours) à une position quasi identique.
    il_y_a_30j = timezone.now() - datetime.timedelta(days=30)
    coords_repetees = 0
    for p in Pointage.objects.filter(utilisateur=pointage.utilisateur, timestamp__gte=il_y_a_30j).exclude(id=pointage.id):
        d = calculer_distance_metres(pointage.latitude, pointage.longitude, p.latitude, p.longitude)
        if d <= COORDS_IDENTIQUES_METRES:
            coords_repetees += 1

    # Doublon : un autre pointage VALIDE existe déjà pour cette session+étudiant.
    is_doublon = Pointage.objects.filter(
        utilisateur=pointage.utilisateur, session=session, statut=Pointage.Statut.VALIDE
    ).exclude(id=pointage.id).exists()

    return {
        'distance_ratio':  round(distance_m / float(zone.rayon_m), 3) if zone.rayon_m else 0.0,
        'precision_gps_m': float(pointage.precision_gps_m) if pointage.precision_gps_m is not None else 15.0,
        'minutes_retard':  round(minutes_retard, 1),
        'vitesse_kmh':     round(vitesse_kmh, 1),
        'coords_repetees': coords_repetees,
        'is_doublon':      1.0 if is_doublon else 0.0,
    }


def determiner_type_fraude(features):
    """Règles explicites — décident QUEL type de fraude, s'il y en a un. Priorité :
    la géolocalisation prime (hors_zone), puis les patterns suspects sur l'appareil."""
    if features['distance_ratio'] > 1.0:
        return 'hors_zone'
    if features['is_doublon']:
        return 'doublon'
    if features['coords_repetees'] >= COORDS_REPETEES_SEUIL:
        return 'coords_fixes'
    if features['vitesse_kmh'] > VITESSE_SPOOFING_KMH:
        return 'spoofing_gps'
    if features['minutes_retard'] > RETARD_TOLERANCE_MIN:
        return 'heure_invalide'
    return None


def _score_heuristique(features):
    """Filet de sécurité utilisé UNIQUEMENT si aucun modèle ML n'a encore été
    entraîné (avant le premier lancement de train_fraud_model)."""
    score = 0.0
    score += min(features['distance_ratio'], 3.0) / 3.0 * 40
    score += min(features['coords_repetees'] / 5.0, 1.0) * 20
    score += (1.0 if features['is_doublon'] else 0.0) * 20
    score += min(features['vitesse_kmh'] / VITESSE_SPOOFING_KMH, 1.0) * 15
    score += min(features['minutes_retard'] / 60.0, 1.0) * 5
    return round(min(score, 100.0), 1)


def calculer_score(features):
    """Renvoie (score_0_100, source). `source` indique quel niveau de détection a
    réellement produit le score — utile pour rester honnête dans l'UI sur ce qui
    tourne vraiment (modèle supervisé > modèle non supervisé > heuristique)."""
    import numpy as np

    x = np.array([[features[k] for k in FEATURE_NAMES]])

    modele_rf = _load_model(RANDOM_FOREST_PATH)
    if modele_rf is not None:
        try:
            proba_fraude = modele_rf.predict_proba(x)[0][1]
            return round(float(proba_fraude) * 100, 1), 'ml_supervise'
        except Exception:
            pass

    modele_iso = _load_model(ISOLATION_FOREST_PATH)
    if modele_iso is not None:
        try:
            anomaly = -modele_iso.decision_function(x)[0]
            score = max(0.0, min(100.0, 50 + anomaly * 50))
            return round(float(score), 1), 'ml_non_supervise'
        except Exception:
            pass

    return _score_heuristique(features), 'heuristique'


def niveau_severite(score):
    if score >= 90:
        return 'CRITIQUE'
    if score >= 70:
        return 'ELEVE'
    if score >= 40:
        return 'MOYEN'
    return 'FAIBLE'


MODEL_VERSION_LABEL = {
    'ml_supervise':     'RandomForest (entraîné sur des alertes confirmées par un admin)',
    'ml_non_supervise': "IsolationForest (détection d'anomalies, scikit-learn)",
    'heuristique':       'Heuristique — modèle ML pas encore entraîné (lancez train_fraud_model)',
}

RECOMMANDATIONS = {
    'hors_zone':      "Vérifier la position déclarée : pointage hors du périmètre autorisé.",
    'doublon':        "Vérifier si un autre appareil a été utilisé pour pointer à la place de l'étudiant.",
    'coords_fixes':   "Position quasi identique sur plusieurs séances — vérifier une éventuelle app de simulation GPS.",
    'spoofing_gps':   "Déplacement physiquement improbable détecté — vérifier l'appareil utilisé.",
    'heure_invalide': "Retard significatif — vérifier si légitime (transport, imprévu) ou récurrent.",
}


def construire_facteurs(features):
    """Facteurs explicables affichés dans le panneau 'Analyse IA détaillée' du site
    web — calculés à partir des VRAIES features de ce pointage, jamais de texte figé."""
    facteurs = []
    if features['distance_ratio'] > 0:
        facteurs.append({
            'name': 'Distance à la zone', 'weight': 0.35,
            'value': round(min(features['distance_ratio'], 2.0) / 2.0, 2),
            'description': f"Distance à {round(features['distance_ratio'] * 100)}% du rayon autorisé",
        })
    if features['coords_repetees'] > 0:
        facteurs.append({
            'name': 'Coordonnées répétées', 'weight': 0.2,
            'value': round(min(features['coords_repetees'] / 5.0, 1.0), 2),
            'description': f"{features['coords_repetees']} pointage(s) récent(s) à une position quasi identique",
        })
    if features['is_doublon']:
        facteurs.append({
            'name': 'Pointage en double', 'weight': 0.2, 'value': 0.95,
            'description': 'Un autre pointage valide existe déjà pour cette session',
        })
    if features['vitesse_kmh'] > 5:
        facteurs.append({
            'name': 'Vitesse de déplacement', 'weight': 0.15,
            'value': round(min(features['vitesse_kmh'] / VITESSE_SPOOFING_KMH, 1.0), 2),
            'description': f"{features['vitesse_kmh']} km/h depuis le pointage précédent",
        })
    if features['minutes_retard'] > 0:
        facteurs.append({
            'name': 'Retard', 'weight': 0.1,
            'value': round(min(features['minutes_retard'] / 60.0, 1.0), 2),
            'description': f"Pointage {round(features['minutes_retard'])} min après le début de la séance",
        })
    return facteurs


def analyser_pointage(pointage, session, zone, distance_m):
    """Point d'entrée principal, appelé par POST /api/pointages/valider/.
    Renvoie le type de fraude détecté (ou None), le score, le niveau de sévérité, et
    un dict prêt à être stocké tel quel dans AlerteFraude.analyse_ia."""
    features = extraire_features(pointage, session, zone, distance_m)
    type_fraude = determiner_type_fraude(features)
    score, source = calculer_score(features)
    niveau = niveau_severite(score)

    analyse_ia = {
        'risk_score':      round(score / 100, 3),
        'model_version':   MODEL_VERSION_LABEL[source],
        'recommendation':  RECOMMANDATIONS.get(type_fraude, 'Aucune anomalie significative détectée.'),
        'factors':         construire_facteurs(features),
    }

    return {
        'type_fraude':     type_fraude,
        'score_ia':        score,
        'niveau_severite': niveau if type_fraude else None,
        'analyse_ia':      analyse_ia if type_fraude else None,
        'source_score':    source,
        'features':        features,
    }