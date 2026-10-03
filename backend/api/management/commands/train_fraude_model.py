"""
Entraîne (ou ré-entraîne) le modèle de détection de fraude sur les pointages réels.

Usage :
    python manage.py train_fraud_model

À relancer périodiquement à mesure que de nouveaux pointages s'accumulent, et surtout
à mesure que des administrateurs confirment ou rejettent des alertes — le modèle
s'améliore avec l'usage réel du système plutôt que de rester figé.
"""
import os

from django.core.management.base import BaseCommand

from api.models import Pointage, AlerteFraude
from api.fraud_detection import (
    FEATURE_NAMES, extraire_features, MODEL_DIR,
    ISOLATION_FOREST_PATH, RANDOM_FOREST_PATH,
)

MIN_POINTAGES_ML       = 15
MIN_EXEMPLES_SUPERVISE = 10


class Command(BaseCommand):
    help = "Entraîne le modèle de détection de fraude (IsolationForest, + RandomForest si assez de données labellisées)."

    def handle(self, *args, **options):
        try:
            import joblib
            import numpy as np
            from sklearn.ensemble import IsolationForest, RandomForestClassifier
        except ImportError:
            self.stdout.write(self.style.ERROR(
                "scikit-learn n'est pas installé. Lancez : pip install -r requirements.txt"
            ))
            return

        os.makedirs(MODEL_DIR, exist_ok=True)

        pointages = list(Pointage.objects.select_related('session__zone').all())
        self.stdout.write(f'{len(pointages)} pointage(s) trouvé(s) en base.')

        if len(pointages) < 2:
            self.stdout.write(self.style.ERROR(
                "Pas assez de pointages pour entraîner quoi que ce soit (minimum 2). "
                "Lancez d'abord seed_demo, ou utilisez l'application pour créer de vrais pointages."
            ))
            return

        if len(pointages) < MIN_POINTAGES_ML:
            self.stdout.write(self.style.WARNING(
                f"Moins de {MIN_POINTAGES_ML} pointages en base — le modèle va être entraîné quand "
                "même, mais sa fiabilité restera limitée tant que plus de données réelles ne "
                "s'accumulent pas. Ce n'est pas un problème bloquant, juste une limite honnête à "
                "avoir en tête."
            ))

        # ── Modèle non supervisé (IsolationForest) — sur TOUS les pointages ──
        X = []
        for p in pointages:
            zone = p.session.zone
            feats = extraire_features(p, p.session, zone, float(p.distance_zone_m or 0))
            X.append([feats[k] for k in FEATURE_NAMES])
        X = np.array(X)

        modele_iso = IsolationForest(n_estimators=150, contamination='auto', random_state=42)
        modele_iso.fit(X)
        joblib.dump(modele_iso, ISOLATION_FOREST_PATH)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Modèle non supervisé (IsolationForest) entraîné sur {len(X)} pointages et sauvegardé."
        ))

        # ── Modèle supervisé (RandomForest) — si assez d'alertes tranchées par un admin ──
        alertes_labellisees = AlerteFraude.objects.filter(
            statut__in=['FRAUDE_CONFIRMEE', 'FAUSSE_ALERTE']
        ).select_related('pointage__session__zone')

        nb_labels = alertes_labellisees.count()
        if nb_labels < MIN_EXEMPLES_SUPERVISE:
            self.stdout.write(self.style.WARNING(
                f"{nb_labels} alerte(s) confirmée(s)/rejetée(s) par un admin trouvée(s) — il en faut "
                f"au moins {MIN_EXEMPLES_SUPERVISE} pour entraîner un modèle supervisé fiable. Pour "
                "l'instant, seul le modèle non supervisé (IsolationForest) est utilisé — c'est normal "
                "et attendu en tout début de projet."
            ))
            return

        X_sup, y_sup = [], []
        for a in alertes_labellisees:
            p = a.pointage
            zone = p.session.zone
            feats = extraire_features(p, p.session, zone, float(p.distance_zone_m or 0))
            X_sup.append([feats[k] for k in FEATURE_NAMES])
            y_sup.append(1 if a.statut == 'FRAUDE_CONFIRMEE' else 0)

        nb_positifs = sum(y_sup)
        nb_negatifs = len(y_sup) - nb_positifs
        if nb_positifs == 0 or nb_negatifs == 0:
            self.stdout.write(self.style.WARNING(
                "Toutes les alertes labellisées sont du même côté (toutes confirmées ou toutes "
                "rejetées) — impossible d'entraîner un classifieur avec une seule classe. "
                "Continuez à traiter des alertes des deux types pour débloquer le modèle supervisé."
            ))
            return

        modele_rf = RandomForestClassifier(n_estimators=150, random_state=42, class_weight='balanced')
        modele_rf.fit(np.array(X_sup), np.array(y_sup))
        joblib.dump(modele_rf, RANDOM_FOREST_PATH)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Modèle supervisé (RandomForest) entraîné sur {nb_labels} alerte(s) tranchée(s) "
            f"({nb_positifs} confirmée(s), {nb_negatifs} fausse(s) alerte(s)) et sauvegardé. "
            "C'est maintenant lui qui calcule le score de risque en priorité."
        ))