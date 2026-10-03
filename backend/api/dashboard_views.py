"""
Vue d'agrégation pour le tableau de bord administrateur (frontend React).
Regroupe en un seul appel toutes les statistiques affichées sur l'écran
« Tableau de bord administrateur » : cartes principales, présence
hebdomadaire (Lun→Ven) et résumé du jour.
"""
import datetime

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Utilisateur, Module, Session, Pointage, AlerteFraude, Inscription

RETARD_MINUTES = 15
JOURS_SEMAINE = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven']


def _compter_presence(sessions_qs):
    """Pour un ensemble de sessions, retourne (présents, absents, en_retard)
    en comparant les inscrits du module à leurs pointages VALIDE."""
    presents, absents, en_retard = 0, 0, 0

    for session in sessions_qs.select_related('module'):
        inscrits_ids = list(
            Inscription.objects.filter(module=session.module, is_active=True)
            .values_list('etudiant_id', flat=True)
        )
        if not inscrits_ids:
            continue

        limite_retard = datetime.datetime.combine(session.date, session.heure_debut) \
            + datetime.timedelta(minutes=RETARD_MINUTES)

        pointes_ids = set()
        for p in Pointage.objects.filter(session=session, statut='VALIDE'):
            pointes_ids.add(p.utilisateur_id)
            ts = timezone.localtime(p.timestamp) if timezone.is_aware(p.timestamp) else p.timestamp
            if ts.replace(tzinfo=None) > limite_retard:
                en_retard += 1
            else:
                presents += 1

        absents += len([uid for uid in inscrits_ids if uid not in pointes_ids])

    return presents, absents, en_retard


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_dashboard(request):
    # ── Cartes principales ──────────────────────────────────────
    etudiants_inscrits = Utilisateur.objects.filter(role='STUDENT', is_active=True).count()
    cours_actifs = Module.objects.count()
    fraudes_detectees = AlerteFraude.objects.count()

    sessions_terminees = Session.objects.filter(statut='TERMINE')
    total_attendu, total_valide = 0, 0
    for s in sessions_terminees.select_related('module'):
        total_attendu += Inscription.objects.filter(module=s.module, is_active=True).count()
        total_valide += Pointage.objects.filter(session=s, statut='VALIDE').count()
    taux_moyen_presence = round((total_valide / total_attendu * 100), 1) if total_attendu > 0 else 0

    # ── Présence hebdomadaire (semaine en cours, Lundi → Vendredi) ─
    today = timezone.localdate()
    lundi = today - datetime.timedelta(days=today.weekday())
    presence_hebdo = []
    for i in range(5):
        jour_date = lundi + datetime.timedelta(days=i)
        sessions_jour = Session.objects.filter(date=jour_date, statut='TERMINE')
        p, a, r = _compter_presence(sessions_jour)
        presence_hebdo.append({'jour': JOURS_SEMAINE[i], 'presents': p, 'absents': a, 'en_retard': r})

    # ── Aujourd'hui ──────────────────────────────────────────────
    sessions_today = Session.objects.filter(date=today)
    p_today, a_today, r_today = _compter_presence(sessions_today)
    alertes_en_attente = AlerteFraude.objects.filter(statut='NON_TRAITEE').count()

    return Response({
        'etudiants_inscrits': etudiants_inscrits,
        'taux_moyen_presence': taux_moyen_presence,
        'fraudes_detectees': fraudes_detectees,
        'cours_actifs': cours_actifs,
        'presence_hebdomadaire': presence_hebdo,
        'aujourdhui': {
            'presents': p_today,
            'absents': a_today,
            'en_retard': r_today,
            'alertes_en_attente': alertes_en_attente,
        },
    })
