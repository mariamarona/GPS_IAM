from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models.deletion import ProtectedError

from .models import Utilisateur, Module, ZoneGPS, Session, Pointage, AlerteFraude, Inscription, ControleGPS
from .serializers import (
    UtilisateurSerializer, ModuleSerializer, ZoneGPSSerializer,
    SessionSerializer, PointageSerializer, AlerteFraudeSerializer, InscriptionSerializer,
)
from .utils import calculer_distance_metres
from . import fraud_detection
import datetime


# ─────────────────────────────────────────────
#  UTILISATEUR
# ─────────────────────────────────────────────
class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset           = Utilisateur.objects.all()
    serializer_class   = UtilisateurSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs   = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

    def destroy(self, request, *args, **kwargs):
        # Un étudiant/enseignant avec des pointages, alertes ou sessions liées ne peut pas
        # être supprimé (clés étrangères PROTECT — utile pour l'audit d'un mémoire cybersécurité).
        # Avant : ça plantait avec une erreur 500. Maintenant : message clair, l'admin doit
        # désactiver le compte (is_active=false) plutôt que de le supprimer.
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'error': "Impossible de supprimer cet utilisateur : il a un historique "
                             "(pointages, alertes ou sessions) lié à son compte. "
                             "Désactivez plutôt son compte pour lui bloquer l'accès sans perdre l'historique.",
                    'code': 'protected',
                },
                status=status.HTTP_409_CONFLICT,
            )

    # ── GET /api/utilisateurs/prochain-matricule/ ─────────────
    # Suggère le prochain matricule séquentiel, selon la convention du projet
    # (202122, 202123, ...), pour pré-remplir le formulaire de création côté admin.
    @action(detail=False, methods=['GET'], url_path='prochain-matricule')
    def prochain_matricule(self, request):
        MATRICULE_DEPART = 202122
        matricules_numeriques = [
            int(m) for m in Utilisateur.objects.values_list('matricule', flat=True) if m and m.isdigit()
        ]
        prochain = max(matricules_numeriques, default=MATRICULE_DEPART - 1) + 1
        return Response({'matricule': str(prochain)})

    # ── GET /api/utilisateurs/{id}/presence/ ─────────────────
    @action(detail=True, methods=['GET'], url_path='presence')
    def presence(self, request, pk=None):
        utilisateur  = self.get_object()
        module_id    = request.query_params.get('module_id')
        inscriptions = Inscription.objects.filter(etudiant=utilisateur, is_active=True).select_related('module')
        if module_id:
            inscriptions = inscriptions.filter(module_id=module_id)

        data_modules           = []
        total_sessions_global  = 0
        total_presences_global = 0

        for inscription in inscriptions:
            module         = inscription.module
            sessions       = Session.objects.filter(module=module, statut='TERMINE')
            total_sessions = sessions.count()
            presences      = Pointage.objects.filter(utilisateur=utilisateur, session__module=module, statut='VALIDE').count()
            absences       = max(0, total_sessions - presences)
            taux           = round((presences / total_sessions * 100), 1) if total_sessions > 0 else 0
            seuil          = module.seuil_presence_pct
            alerte_seuil   = taux < seuil
            total_sessions_global  += total_sessions
            total_presences_global += presences
            data_modules.append({
                'module_id':       module.id,
                'module_code':     module.code,
                'module_intitule': module.intitule,
                'total_sessions':  total_sessions,
                'presences':       presences,
                'absences':        absences,
                'taux_presence':   f'{taux}%',
                'seuil_requis':    f'{seuil}%',
                'alerte_seuil':    alerte_seuil,
            })

        taux_global = round((total_presences_global / total_sessions_global * 100), 1) if total_sessions_global > 0 else 0

        return Response({
            'etudiant': {'id': str(utilisateur.id), 'matricule': utilisateur.matricule, 'nom': utilisateur.nom, 'prenom': utilisateur.prenom},
            'taux_global':     f'{taux_global}%',
            'total_sessions':  total_sessions_global,
            'total_presences': total_presences_global,
            'modules':         data_modules,
        }, status=status.HTTP_200_OK)

    # ── GET /api/utilisateurs/{id}/historique/ ────────────────
    @action(detail=True, methods=['GET'], url_path='historique')
    def historique(self, request, pk=None):
        utilisateur = self.get_object()
        module_id   = request.query_params.get('module_id')
        date_debut  = request.query_params.get('date_debut')
        date_fin    = request.query_params.get('date_fin')

        pointages = Pointage.objects.filter(utilisateur=utilisateur).select_related('session__module', 'session__zone').order_by('-timestamp')
        if module_id:
            pointages = pointages.filter(session__module_id=module_id)
        if date_debut:
            pointages = pointages.filter(session__date__gte=date_debut)
        if date_fin:
            pointages = pointages.filter(session__date__lte=date_fin)

        data = []
        for p in pointages:
            data.append({
                'pointage_id': p.id,
                'date':        str(p.session.date),
                'heure':       str(p.timestamp),
                'module':      p.session.module.code,
                'intitule':    p.session.module.intitule,
                'zone':        p.session.zone.nom,
                'statut':      p.statut,
                'distance_m':  p.distance_zone_m,
                'est_fraude':  p.statut == 'HORS_ZONE',
            })

        return Response({
            'etudiant': {'id': str(utilisateur.id), 'matricule': utilisateur.matricule, 'nom': utilisateur.nom, 'prenom': utilisateur.prenom},
            'total':     len(data),
            'pointages': data,
        }, status=status.HTTP_200_OK)

    # ── GET /api/utilisateurs/{id}/absences/ ──────────────────
    @action(detail=True, methods=['GET'], url_path='absences')
    def absences(self, request, pk=None):
        utilisateur        = self.get_object()
        modules_inscrits   = Inscription.objects.filter(etudiant=utilisateur, is_active=True).values_list('module_id', flat=True)
        sessions_terminees = Session.objects.filter(module_id__in=modules_inscrits, statut='TERMINE').select_related('module', 'zone')
        sessions_pointees  = Pointage.objects.filter(utilisateur=utilisateur, statut='VALIDE').values_list('session_id', flat=True)

        absences = []
        for session in sessions_terminees:
            if session.id not in sessions_pointees:
                absences.append({
                    'session_id':  session.id,
                    'module':      session.module.code,
                    'intitule':    session.module.intitule,
                    'date':        str(session.date),
                    'heure_debut': str(session.heure_debut),
                    'heure_fin':   str(session.heure_fin),
                    'zone':        session.zone.nom,
                })

        return Response({
            'etudiant': {'id': str(utilisateur.id), 'matricule': utilisateur.matricule, 'nom': utilisateur.nom, 'prenom': utilisateur.prenom},
            'total_absences': len(absences),
            'absences':       absences,
        }, status=status.HTTP_200_OK)

    # ── GET /api/utilisateurs/{id}/sessions/ ──────────────────
    @action(detail=True, methods=['GET'], url_path='sessions')
    def sessions(self, request, pk=None):
        utilisateur = self.get_object()
        statut      = request.query_params.get('statut')
        date        = request.query_params.get('date')

        sessions = Session.objects.filter(created_by=utilisateur).select_related('module', 'zone').order_by('-date', 'heure_debut')
        if statut:
            sessions = sessions.filter(statut=statut)
        if date:
            sessions = sessions.filter(date=date)

        data = []
        for s in sessions:
            nb_presences = Pointage.objects.filter(session=s, statut='VALIDE').count()
            nb_inscrits  = Inscription.objects.filter(module=s.module, is_active=True).count()
            data.append({
                'id':            s.id,
                'module':        s.module.code,
                'intitule':      s.module.intitule,
                'zone':          s.zone.nom,
                'date':          str(s.date),
                'heure_debut':   str(s.heure_debut),
                'heure_fin':     str(s.heure_fin),
                'statut':        s.statut,
                'nb_presences':  nb_presences,
                'nb_inscrits':   nb_inscrits,
                'taux_presence': f'{round(nb_presences / nb_inscrits * 100, 1) if nb_inscrits > 0 else 0}%',
            })

        return Response({
            'enseignant': {'id': str(utilisateur.id), 'matricule': utilisateur.matricule, 'nom': utilisateur.nom, 'prenom': utilisateur.prenom},
            'total':    len(data),
            'sessions': data,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  MODULE
# ─────────────────────────────────────────────
class ModuleViewSet(viewsets.ModelViewSet):
    queryset           = Module.objects.select_related('enseignant').prefetch_related(
        'sessions__zone', 'inscriptions__etudiant'
    )
    serializer_class   = ModuleSerializer
    permission_classes = [AllowAny]

    # ── GET /api/modules/{id}/etudiants/ ──────────────────────
    @action(detail=True, methods=['GET'], url_path='etudiants')
    def etudiants(self, request, pk=None):
        module       = self.get_object()
        inscriptions = Inscription.objects.filter(module=module, is_active=True).select_related('etudiant')
        sessions_terminees = Session.objects.filter(module=module, statut='TERMINE').count()

        data = []
        for inscription in inscriptions:
            etudiant  = inscription.etudiant
            presences = Pointage.objects.filter(utilisateur=etudiant, session__module=module, statut='VALIDE').count()
            taux      = round((presences / sessions_terminees * 100), 1) if sessions_terminees > 0 else 0
            data.append({
                'id':               str(etudiant.id),
                'matricule':        etudiant.matricule,
                'nom':              etudiant.nom,
                'prenom':           etudiant.prenom,
                'email':            etudiant.email,
                'date_inscription': str(inscription.date_inscription),
                'presences':        presences,
                'taux_presence':    f'{taux}%',
                'alerte_seuil':     taux < module.seuil_presence_pct,
            })

        return Response({
            'module': {'id': module.id, 'code': module.code, 'intitule': module.intitule, 'seuil_presence_pct': module.seuil_presence_pct},
            'total_inscrits': len(data),
            'etudiants':      data,
        }, status=status.HTTP_200_OK)

    # ── GET /api/modules/{id}/stats/ ──────────────────────────
    @action(detail=True, methods=['GET'], url_path='stats')
    def stats(self, request, pk=None):
        module = self.get_object()

        sessions_total     = Session.objects.filter(module=module).count()
        sessions_terminees = Session.objects.filter(module=module, statut='TERMINE').count()
        sessions_en_cours  = Session.objects.filter(module=module, statut='EN_COURS').count()
        sessions_planifiees = Session.objects.filter(module=module, statut='PLANIFIE').count()
        nb_inscrits        = Inscription.objects.filter(module=module, is_active=True).count()
        total_pointages    = Pointage.objects.filter(session__module=module, statut='VALIDE').count()
        taux_moyen         = round((total_pointages / (sessions_terminees * nb_inscrits) * 100), 1) if sessions_terminees > 0 and nb_inscrits > 0 else 0
        nb_alertes         = AlerteFraude.objects.filter(pointage__session__module=module).count()

        sous_seuil    = 0
        inscriptions  = Inscription.objects.filter(module=module, is_active=True).select_related('etudiant')
        for inscription in inscriptions:
            presences = Pointage.objects.filter(utilisateur=inscription.etudiant, session__module=module, statut='VALIDE').count()
            taux      = round((presences / sessions_terminees * 100), 1) if sessions_terminees > 0 else 0
            if taux < module.seuil_presence_pct:
                sous_seuil += 1

        return Response({
            'module': {'id': module.id, 'code': module.code, 'intitule': module.intitule, 'seuil_presence_pct': module.seuil_presence_pct, 'enseignant': f'{module.enseignant.prenom} {module.enseignant.nom}'},
            'sessions': {'total': sessions_total, 'terminees': sessions_terminees, 'en_cours': sessions_en_cours, 'planifiees': sessions_planifiees},
            'etudiants': {'total_inscrits': nb_inscrits, 'sous_seuil': sous_seuil},
            'presence': {'taux_moyen': f'{taux_moyen}%', 'total_pointages': total_pointages},
            'fraude': {'total_alertes': nb_alertes},
        }, status=status.HTTP_200_OK)

    # ── POST /api/modules/{id}/demarrer-session/ ───────────────
    # Démarre la séance du jour pour ce module — la crée si elle n'existe pas encore
    # (en reprenant la zone GPS et l'horaire de la dernière séance connue de ce module),
    # ou la relance si elle existe déjà mais n'est pas encore en cours.
    @action(detail=True, methods=['POST'], url_path='demarrer-session')
    def demarrer_session(self, request, pk=None):
        module = self.get_object()
        today  = timezone.localdate()

        session = Session.objects.filter(module=module, date=today).order_by('heure_debut').first()

        if session is None:
            reference = Session.objects.filter(module=module).order_by('-date', '-heure_debut').first()
            if reference is None:
                return Response(
                    {'error': "Aucune séance de référence pour ce module (zone GPS et horaire "
                              "inconnus). Créez d'abord une séance pour ce module avant de pouvoir "
                              "la démarrer en un clic."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            session = Session.objects.create(
                module=module, zone=reference.zone, date=today,
                heure_debut=reference.heure_debut, heure_fin=reference.heure_fin,
                created_by=module.enseignant, statut=Session.Statut.EN_COURS,
            )
        elif session.statut != Session.Statut.EN_COURS:
            # PLANIFIE, TERMINE ou ANNULEE : on (ré)active la séance à la demande de
            # l'enseignant. Avant, une séance TERMINE ne pouvait plus jamais être
            # redémarrée — ce qui bloquait le pointage si elle avait été terminée
            # par erreur (ou par l'ancien bug de seed_demo).
            session.statut = Session.Statut.EN_COURS
            session.save(update_fields=['statut'])

        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)




# ─────────────────────────────────────────────
#  ZONE GPS
# ─────────────────────────────────────────────
class ZoneGPSViewSet(viewsets.ModelViewSet):
    queryset           = ZoneGPS.objects.all()
    serializer_class   = ZoneGPSSerializer
    permission_classes = [AllowAny]


# ─────────────────────────────────────────────
#  INSCRIPTION
# ─────────────────────────────────────────────
class InscriptionViewSet(viewsets.ModelViewSet):
    queryset           = Inscription.objects.all()
    serializer_class   = InscriptionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs        = super().get_queryset()
        module_id = self.request.query_params.get('module')
        etudiant_id = self.request.query_params.get('etudiant')
        if module_id:
            qs = qs.filter(module_id=module_id)
        if etudiant_id:
            qs = qs.filter(etudiant_id=etudiant_id)
        return qs

    def create(self, request, *args, **kwargs):
        # Réactive une inscription désactivée plutôt que de planter sur la contrainte
        # unique (etudiant, module) si l'étudiant avait déjà été inscrit puis désinscrit.
        etudiant_id = request.data.get('etudiant')
        module_id   = request.data.get('module')
        existante   = Inscription.objects.filter(etudiant_id=etudiant_id, module_id=module_id).first()
        if existante:
            if existante.is_active:
                return Response(
                    {'error': 'Cet étudiant est déjà inscrit à ce cours.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            existante.is_active = True
            existante.save(update_fields=['is_active'])
            return Response(InscriptionSerializer(existante).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)


# ─────────────────────────────────────────────
#  SESSION
# ─────────────────────────────────────────────
class SessionViewSet(viewsets.ModelViewSet):
    queryset           = Session.objects.all()
    serializer_class   = SessionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs        = super().get_queryset()
        module_id = self.request.query_params.get('module_id')
        statut    = self.request.query_params.get('statut')
        date      = self.request.query_params.get('date')
        if module_id:
            qs = qs.filter(module_id=module_id)
        if statut:
            qs = qs.filter(statut=statut)
        if date:
            qs = qs.filter(date=date)
        return qs

    @action(detail=True, methods=['POST'], url_path='demarrer')
    def demarrer(self, request, pk=None):
        session = self.get_object()
        if session.statut == 'EN_COURS':
            return Response({'error': 'Cette séance est déjà en cours.'}, status=status.HTTP_400_BAD_REQUEST)
        # PLANIFIE, TERMINE ou ANNULEE peuvent tous être (re)démarrés à la demande de
        # l'enseignant — lui seul décide du cycle de vie de sa séance, plus jamais un
        # script automatique (voir le correctif de seed_demo).
        session.statut = Session.Statut.EN_COURS
        session.save()
        return Response({'message': f'Session {session.module.code} démarrée', 'session_id': session.id, 'statut': session.statut, 'module': session.module.code, 'zone': session.zone.nom, 'heure_debut': str(session.heure_debut), 'heure_fin': str(session.heure_fin)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='terminer')
    def terminer(self, request, pk=None):
        session = self.get_object()
        if session.statut != 'EN_COURS':
            return Response({'error': f'Impossible de terminer — statut actuel : {session.statut}'}, status=status.HTTP_400_BAD_REQUEST)
        session.statut = Session.Statut.TERMINE
        session.save()
        pointages     = Pointage.objects.filter(session=session)
        total_pointes = pointages.count()
        valides       = pointages.filter(statut='VALIDE').count()
        hors_zone     = pointages.filter(statut='HORS_ZONE').count()
        inscrits      = Inscription.objects.filter(module=session.module, is_active=True).count()
        absents       = max(0, inscrits - total_pointes)
        return Response({'message': f'Session {session.module.code} terminée', 'session_id': session.id, 'statut': session.statut, 'resume': {'inscrits': inscrits, 'total_pointes': total_pointes, 'valides': valides, 'hors_zone': hors_zone, 'absents': absents, 'taux_presence': f'{round(valides / inscrits * 100, 1) if inscrits > 0 else 0}%'}}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='annuler')
    def annuler(self, request, pk=None):
        session = self.get_object()
        if session.statut == 'TERMINE':
            return Response({'error': "Impossible d'annuler une session déjà terminée"}, status=status.HTTP_400_BAD_REQUEST)
        session.statut = Session.Statut.ANNULEE
        session.save()
        return Response({'message': f'Session {session.module.code} annulée', 'session_id': session.id, 'statut': session.statut}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], url_path='absents')
    def absents(self, request, pk=None):
        session     = self.get_object()
        inscrits    = Inscription.objects.filter(module=session.module, is_active=True).select_related('etudiant')
        pointes_ids = Pointage.objects.filter(session=session, statut='VALIDE').values_list('utilisateur_id', flat=True)
        absents = []
        for inscription in inscrits:
            if inscription.etudiant.id not in pointes_ids:
                absents.append({'id': str(inscription.etudiant.id), 'matricule': inscription.etudiant.matricule, 'nom': inscription.etudiant.nom, 'prenom': inscription.etudiant.prenom, 'email': inscription.etudiant.email})
        return Response({'session_id': session.id, 'module': session.module.code, 'date': str(session.date), 'total_inscrits': inscrits.count(), 'total_absents': len(absents), 'absents': absents}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path="aujourd-hui")
    def aujourd_hui(self, request):
        today    = datetime.date.today()
        sessions = Session.objects.filter(date=today).select_related('module', 'zone', 'created_by').order_by('heure_debut')
        data = []
        for s in sessions:
            nb = Pointage.objects.filter(session=s, statut='VALIDE').count()
            data.append({
                'id': s.id, 'module': s.module.code, 'intitule': s.module.intitule,
                'zone': s.zone.nom,
                'zone_detail': {
                    'nom': s.zone.nom, 'latitude': str(s.zone.latitude),
                    'longitude': str(s.zone.longitude), 'rayon_m': s.zone.rayon_m,
                },
                'date': str(s.date), 'heure_debut': str(s.heure_debut), 'heure_fin': str(s.heure_fin),
                'statut': s.statut, 'nb_presences': nb,
            })
        return Response({'date': str(today), 'total': len(data), 'sessions': data}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  ALERTE FRAUDE
# ─────────────────────────────────────────────
class AlerteFraudeViewSet(viewsets.ModelViewSet):
    queryset           = AlerteFraude.objects.select_related(
        'pointage__utilisateur', 'pointage__session__module'
    ).all()
    serializer_class   = AlerteFraudeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs              = super().get_queryset()
        statut          = self.request.query_params.get('statut')
        type_fraude     = self.request.query_params.get('type_fraude')
        niveau_severite = self.request.query_params.get('niveau_severite')
        utilisateur_id  = self.request.query_params.get('utilisateur_id')
        enseignant_id   = self.request.query_params.get('enseignant_id')
        if statut:
            qs = qs.filter(statut=statut)
        if type_fraude:
            qs = qs.filter(type_fraude=type_fraude)
        if niveau_severite:
            qs = qs.filter(niveau_severite=niveau_severite)
        if utilisateur_id:
            qs = qs.filter(pointage__utilisateur_id=utilisateur_id)
        if enseignant_id:
            # Un enseignant ne doit voir que les alertes de SES modules, pas celles de tout l'IAM.
            qs = qs.filter(pointage__session__module__enseignant_id=enseignant_id)
        return qs.order_by('-timestamp')

    @action(detail=True, methods=['PATCH'], url_path='traiter')
    def traiter(self, request, pk=None):
        alerte      = self.get_object()
        statut      = request.data.get('statut')
        traite_par  = request.data.get('traite_par')
        commentaire = request.data.get('commentaire', None)
        statuts_valides = ['EN_INVESTIGATION', 'FRAUDE_CONFIRMEE', 'FAUSSE_ALERTE']
        if not statut or statut not in statuts_valides:
            return Response({'error': f'Statut invalide. Choisir parmi : {statuts_valides}'}, status=status.HTTP_400_BAD_REQUEST)
        if alerte.statut in ['FRAUDE_CONFIRMEE', 'FAUSSE_ALERTE']:
            return Response({'error': f'Alerte déjà traitée — statut : {alerte.statut}'}, status=status.HTTP_400_BAD_REQUEST)
        alerte.statut = statut
        if commentaire:
            alerte.commentaire = commentaire
        if traite_par:
            try:
                admin = Utilisateur.objects.get(id=traite_par)
                alerte.traite_par = admin
            except Utilisateur.DoesNotExist:
                pass
        if statut in ['FRAUDE_CONFIRMEE', 'FAUSSE_ALERTE']:
            alerte.traite_at = timezone.now()
        alerte.save()
        return Response({'message': f'Alerte mise à jour → {statut}', 'alerte_id': alerte.id, 'statut': alerte.statut, 'traite_at': alerte.traite_at, 'commentaire': alerte.commentaire}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='non-traitees')
    def non_traitees(self, request):
        alertes = AlerteFraude.objects.filter(statut='NON_TRAITEE').select_related('pointage__utilisateur', 'pointage__session__module', 'pointage__session__zone').order_by('-timestamp')
        data = []
        for a in alertes:
            p = a.pointage
            data.append({'alerte_id': a.id, 'type_fraude': a.type_fraude, 'niveau_severite': a.niveau_severite, 'score_ia': a.score_ia, 'timestamp': a.timestamp, 'etudiant': {'id': str(p.utilisateur.id), 'matricule': p.utilisateur.matricule, 'nom': p.utilisateur.nom, 'prenom': p.utilisateur.prenom}, 'session': {'id': p.session.id, 'module': p.session.module.code, 'date': str(p.session.date), 'zone': p.session.zone.nom}, 'pointage': {'id': p.id, 'latitude': str(p.latitude), 'longitude': str(p.longitude), 'distance_m': p.distance_zone_m, 'timestamp': p.timestamp}})
        return Response({'total': len(data), 'alertes': data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='dashboard')
    def dashboard(self, request):
        total            = AlerteFraude.objects.count()
        non_traitees     = AlerteFraude.objects.filter(statut='NON_TRAITEE').count()
        en_investigation = AlerteFraude.objects.filter(statut='EN_INVESTIGATION').count()
        confirmees       = AlerteFraude.objects.filter(statut='FRAUDE_CONFIRMEE').count()
        fausses_alertes  = AlerteFraude.objects.filter(statut='FAUSSE_ALERTE').count()
        par_type = {}
        for t in AlerteFraude.TypeFraude:
            c = AlerteFraude.objects.filter(type_fraude=t.value).count()
            if c > 0:
                par_type[t.value] = c
        par_severite = {}
        for n in AlerteFraude.NiveauSeverite:
            c = AlerteFraude.objects.filter(niveau_severite=n.value).count()
            if c > 0:
                par_severite[n.value] = c
        return Response({'total': total, 'non_traitees': non_traitees, 'en_investigation': en_investigation, 'confirmees': confirmees, 'fausses_alertes': fausses_alertes, 'par_type': par_type, 'par_severite': par_severite}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='par-etudiant')
    def par_etudiant(self, request):
        utilisateur_id = request.query_params.get('utilisateur_id')
        if not utilisateur_id:
            return Response({'error': 'utilisateur_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        alertes = AlerteFraude.objects.filter(pointage__utilisateur_id=utilisateur_id).select_related('pointage__session__module').order_by('-timestamp')
        data = []
        for a in alertes:
            data.append({'alerte_id': a.id, 'type_fraude': a.type_fraude, 'niveau_severite': a.niveau_severite, 'score_ia': a.score_ia, 'statut': a.statut, 'timestamp': a.timestamp, 'traite_at': a.traite_at, 'commentaire': a.commentaire, 'module': a.pointage.session.module.code, 'date_session': str(a.pointage.session.date)})
        return Response({'utilisateur_id': utilisateur_id, 'total': len(data), 'alertes': data}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  POINTAGE
# ─────────────────────────────────────────────
class PointageViewSet(viewsets.ModelViewSet):
    queryset           = Pointage.objects.all()
    serializer_class   = PointageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs         = super().get_queryset()
        session_id = self.request.query_params.get('session_id')
        user_id    = self.request.query_params.get('utilisateur_id')
        statut     = self.request.query_params.get('statut')
        if session_id:
            qs = qs.filter(session_id=session_id)
        if user_id:
            qs = qs.filter(utilisateur_id=user_id)
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    @action(detail=False, methods=['POST'], url_path='valider')
    def valider(self, request):
        utilisateur_id = request.data.get('utilisateur_id')
        session_id     = request.data.get('session_id')
        latitude       = request.data.get('latitude')
        longitude      = request.data.get('longitude')
        precision      = request.data.get('precision_gps_m', None)
        timestamp_appareil = request.data.get('timestamp_appareil')
        if not all([utilisateur_id, session_id, latitude, longitude]):
            return Response({'error': 'utilisateur_id, session_id, latitude et longitude sont requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            utilisateur = Utilisateur.objects.get(id=utilisateur_id)
        except Utilisateur.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        try:
            session = Session.objects.select_related('zone').get(id=session_id)
        except Session.DoesNotExist:
            return Response({'error': 'Session non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        if session.statut not in ['EN_COURS', 'PLANIFIE']:
            return Response({'error': f'Session {session.statut} — pointage impossible'}, status=status.HTTP_400_BAD_REQUEST)
        zone     = session.zone
        distance = calculer_distance_metres(latitude, longitude, zone.latitude, zone.longitude)
        dans_zone       = distance <= float(zone.rayon_m)
        statut_pointage = Pointage.Statut.VALIDE if dans_zone else Pointage.Statut.HORS_ZONE

        # Horodatage du pointage : on utilise l'heure exacte de l'appareil de
        # l'étudiant (envoyée par l'appli mobile au moment du pointage) plutôt
        # que l'heure du serveur, pour que l'heure affichée corresponde
        # toujours à celle du téléphone. Si l'appli ne l'envoie pas ou si la
        # valeur est invalide, on retombe sur l'heure du serveur.
        horodatage_pointage = timezone.now()
        if timestamp_appareil:
            try:
                ts = datetime.datetime.fromisoformat(timestamp_appareil)
                if timezone.is_naive(ts):
                    ts = timezone.make_aware(ts, timezone.get_current_timezone())
                horodatage_pointage = ts
            except (ValueError, TypeError):
                pass

        # Un étudiant ne doit avoir qu'UN SEUL pointage par séance : s'il retente après un
        # échec "hors zone" (mauvais GPS, mauvais emplacement...), on met à jour sa ligne
        # existante (nouvelle heure, nouvelle position, nouveau statut) au lieu d'en créer
        # une seconde — sinon l'historique et les statistiques de présence ne coïncident plus.
        pointage_existant = Pointage.objects.filter(utilisateur=utilisateur, session=session).first()
        if pointage_existant and pointage_existant.statut == Pointage.Statut.VALIDE:
            return Response({
                'error': 'Vous avez déjà pointé pour cette séance.',
                'pointage_id': pointage_existant.id,
                'statut': pointage_existant.statut,
                'timestamp': pointage_existant.timestamp.isoformat(),
            }, status=status.HTTP_400_BAD_REQUEST)

        if pointage_existant:
            pointage_existant.latitude        = latitude
            pointage_existant.longitude       = longitude
            pointage_existant.precision_gps_m = precision
            pointage_existant.distance_zone_m = round(distance, 2)
            pointage_existant.statut          = statut_pointage
            pointage_existant.timestamp       = horodatage_pointage
            pointage_existant.save(update_fields=[
                'latitude', 'longitude', 'precision_gps_m', 'distance_zone_m', 'statut', 'timestamp',
            ])
            pointage = pointage_existant
        else:
            pointage = Pointage.objects.create(utilisateur=utilisateur, session=session, latitude=latitude, longitude=longitude, precision_gps_m=precision, distance_zone_m=round(distance, 2), statut=statut_pointage, timestamp=horodatage_pointage)

        # Détection de fraude réelle (règles + modèle ML entraîné — voir fraud_detection.py),
        # pas seulement la vérification "hors zone" : doublon, coordonnées répétées, retard,
        # vitesse de déplacement improbable sont maintenant aussi couverts.
        analyse    = fraud_detection.analyser_pointage(pointage, session, zone, distance)
        est_fraude = analyse['type_fraude'] is not None

        if est_fraude:
            AlerteFraude.objects.create(
                pointage=pointage, type_fraude=analyse['type_fraude'],
                score_ia=analyse['score_ia'], niveau_severite=analyse['niveau_severite'],
                statut=AlerteFraude.Statut.NON_TRAITEE,
                commentaire=analyse['analyse_ia']['recommendation'],
                analyse_ia=analyse['analyse_ia'],
            )

        return Response({
            'pointage_id': pointage.id, 'statut': statut_pointage, 'dans_zone': dans_zone,
            'distance_m': round(distance, 2), 'rayon_zone_m': float(zone.rayon_m),
            'est_fraude': est_fraude, 'type_fraude': analyse['type_fraude'],
            'timestamp': pointage.timestamp.isoformat(),
            'heure_pointage': timezone.localtime(pointage.timestamp).strftime('%H:%M:%S'),
            'message': '✅ Pointage validé' if not est_fraude else f"⚠️ Anomalie détectée ({analyse['type_fraude']}) — alerte créée",
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'], url_path='stats')
    def stats(self, request):
        utilisateur_id = request.query_params.get('utilisateur_id')
        session_id     = request.query_params.get('session_id')
        qs = Pointage.objects.all()
        if utilisateur_id:
            qs = qs.filter(utilisateur_id=utilisateur_id)
        if session_id:
            qs = qs.filter(session_id=session_id)
        total     = qs.count()
        valides   = qs.filter(statut='VALIDE').count()
        hors_zone = qs.filter(statut='HORS_ZONE').count()
        rejetes   = qs.filter(statut='REJETE').count()
        taux      = round((valides / total * 100), 1) if total > 0 else 0
        return Response({'total': total, 'valides': valides, 'hors_zone': hors_zone, 'rejetes': rejetes, 'taux_presence': f'{taux}%'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='corriger')
    def corriger(self, request):
        """
        Correction manuelle d'une présence par l'enseignant (cas d'utilisation
        "Corriger une présence") : deux situations couvertes —
          1. Un pointage existe déjà (ex: HORS_ZONE à tort, GPS imprécis) : on change
             juste son statut.
          2. L'étudiant est absent (aucun pointage) mais était bien en cours : on crée
             un pointage manuel avec le statut demandé, aux coordonnées de la zone.
        """
        utilisateur_id  = request.data.get('utilisateur_id')
        session_id      = request.data.get('session_id')
        nouveau_statut  = request.data.get('statut')
        commentaire     = request.data.get('commentaire', '')

        statuts_valides = [Pointage.Statut.VALIDE, Pointage.Statut.REJETE]
        if nouveau_statut not in statuts_valides:
            return Response(
                {'error': f"Statut invalide. Choisir parmi : {statuts_valides}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not utilisateur_id or not session_id:
            return Response({'error': 'utilisateur_id et session_id sont requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            utilisateur = Utilisateur.objects.get(id=utilisateur_id)
            session     = Session.objects.select_related('zone').get(id=session_id)
        except (Utilisateur.DoesNotExist, Session.DoesNotExist):
            return Response({'error': 'Étudiant ou session introuvable'}, status=status.HTTP_404_NOT_FOUND)

        pointage = Pointage.objects.filter(utilisateur=utilisateur, session=session).first()
        cree = False
        if pointage:
            pointage.statut = nouveau_statut
            pointage.save(update_fields=['statut'])
        else:
            zone = session.zone
            pointage = Pointage.objects.create(
                utilisateur=utilisateur, session=session, timestamp=timezone.now(),
                latitude=zone.latitude, longitude=zone.longitude,
                precision_gps_m=None, distance_zone_m=0, statut=nouveau_statut,
            )
            cree = True

        return Response({
            'pointage_id': pointage.id,
            'statut': pointage.statut,
            'cree': cree,
            'commentaire': commentaire,
            'message': "Présence corrigée avec succès." if not cree else "Pointage créé manuellement par l'enseignant.",
        }, status=status.HTTP_200_OK)

    # ── POST /api/pointages/{id}/controle-periodique/ ──────────
    # Cas d'utilisation étudiant "Répondre aux contrôles périodiques" (inclut le
    # Service GPS) : pendant que la séance est EN_COURS, l'application mobile
    # redemande régulièrement la position de l'étudiant après son pointage initial,
    # pour vérifier qu'il est resté dans la zone et pas seulement au moment de pointer.
    @action(detail=True, methods=['POST'], url_path='controle-periodique')
    def controle_periodique(self, request, pk=None):
        pointage  = self.get_object()
        latitude  = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if latitude is None or longitude is None:
            return Response({'error': 'latitude et longitude sont requis'}, status=status.HTTP_400_BAD_REQUEST)
        if pointage.session.statut != 'EN_COURS':
            return Response(
                {'error': "La séance n'est plus en cours — le contrôle périodique est ignoré."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zone      = pointage.session.zone
        distance  = calculer_distance_metres(latitude, longitude, zone.latitude, zone.longitude)
        dans_zone = distance <= float(zone.rayon_m)
        statut_controle = ControleGPS.Statut.VALIDE if dans_zone else ControleGPS.Statut.HORS_ZONE

        controle = ControleGPS.objects.create(
            pointage=pointage, latitude=latitude, longitude=longitude,
            distance_zone_m=round(distance, 2), statut=statut_controle,
        )

        alerte_creee = False
        if not dans_zone:
            # AlerteFraude est en relation 1-à-1 avec Pointage : si une alerte existe
            # déjà sur ce pointage, on l'escalade plutôt que d'en créer une seconde.
            alerte = getattr(pointage, 'alerte_fraude', None)
            heure  = timezone.localtime(controle.timestamp).strftime('%H:%M')
            if alerte is None:
                AlerteFraude.objects.create(
                    pointage=pointage, type_fraude=AlerteFraude.TypeFraude.HORS_ZONE,
                    score_ia=90, niveau_severite=AlerteFraude.NiveauSeverite.CRITIQUE,
                    statut=AlerteFraude.Statut.NON_TRAITEE,
                    commentaire=(f"Contrôle périodique échoué à {heure} : étudiant à "
                                 f"{round(distance)}m de la zone autorisée alors que son pointage "
                                 f"initial était valide (départ probable en cours de séance)."),
                    analyse_ia={
                        'facteurs': [{'nom': 'Contrôle périodique GPS', 'valeur': f'{round(distance)}m hors zone', 'poids': 1.0}],
                        'recommendation': "Vérifier si l'étudiant a quitté la salle avant la fin de la séance.",
                        'modele': 'controle_periodique_v1',
                    },
                )
                alerte_creee = True
            elif alerte.statut in (AlerteFraude.Statut.NON_TRAITEE, AlerteFraude.Statut.EN_INVESTIGATION):
                alerte.niveau_severite = AlerteFraude.NiveauSeverite.CRITIQUE
                alerte.commentaire = (alerte.commentaire or '') + f"\nContrôle périodique échoué à {heure} ({round(distance)}m hors zone)."
                alerte.save(update_fields=['niveau_severite', 'commentaire'])

        return Response({
            'controle_id':  controle.id,
            'statut':       statut_controle,
            'dans_zone':    dans_zone,
            'distance_m':   round(distance, 2),
            'rayon_zone_m': float(zone.rayon_m),
            'alerte_creee': alerte_creee,
            'message': "✅ Position confirmée." if dans_zone else "⚠️ Vous n'êtes plus dans la zone autorisée.",
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'], url_path='par-session')
    def par_session(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'session_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        pointages = Pointage.objects.filter(session_id=session_id).select_related('utilisateur', 'session')
        data = []
        for p in pointages:
            data.append({'pointage_id': p.id, 'etudiant': {'id': str(p.utilisateur.id), 'matricule': p.utilisateur.matricule, 'nom': p.utilisateur.nom, 'prenom': p.utilisateur.prenom}, 'timestamp': p.timestamp, 'statut': p.statut, 'distance_m': p.distance_zone_m, 'latitude': str(p.latitude), 'longitude': str(p.longitude)})
        return Response({'session_id': session_id, 'total': len(data), 'pointages': data}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  TABLEAU DE BORD ADMINISTRATEUR
# ─────────────────────────────────────────────
RETARD_TOLERANCE_MIN = 10  # minutes après l'heure de début au-delà desquelles un pointage VALIDE est compté "en retard"


def _stats_du_jour(jour):
    """Calcule (présents, absents, en_retard) pour toutes les sessions d'une date donnée."""
    sessions_jour = Session.objects.filter(date=jour).select_related('module')
    presents, absents, en_retard = 0, 0, 0

    for s in sessions_jour:
        inscrits   = Inscription.objects.filter(module=s.module, is_active=True).count()
        pointages  = Pointage.objects.filter(session=s, statut='VALIDE')
        nb_pointes = pointages.count()
        limite_retard = (datetime.datetime.combine(jour, s.heure_debut) + datetime.timedelta(minutes=RETARD_TOLERANCE_MIN)).time()
        nb_retard  = pointages.filter(timestamp__time__gt=limite_retard).count()

        en_retard += nb_retard
        presents  += (nb_pointes - nb_retard)
        absents   += max(0, inscrits - nb_pointes)

    return presents, absents, en_retard


def _taux_presence_etudiant(etudiant, modules_ids):
    """Taux de présence global d'un étudiant sur l'ensemble de ses modules inscrits."""
    total_sessions = Session.objects.filter(module_id__in=modules_ids, statut='TERMINE').count()
    if total_sessions == 0:
        return 0
    total_presences = Pointage.objects.filter(
        utilisateur=etudiant, session__module_id__in=modules_ids, statut='VALIDE'
    ).count()
    return round((total_presences / total_sessions * 100), 1)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_admin(request):
    """GET /api/dashboard/admin/ — Agrège toutes les données du tableau de bord administrateur."""
    today = timezone.localdate()

    # ── Cartes principales ──────────────────────
    etudiants_inscrits = Utilisateur.objects.filter(role=Utilisateur.Role.STUDENT, is_active=True).count()
    cours_actifs        = Module.objects.count()
    fraudes_detectees   = AlerteFraude.objects.count()

    sessions_terminees = Session.objects.filter(statut='TERMINE').select_related('module')
    total_pointages_valides = Pointage.objects.filter(session__in=sessions_terminees, statut='VALIDE').count()
    total_places = sum(
        Inscription.objects.filter(module=s.module, is_active=True).count()
        for s in sessions_terminees
    )
    taux_moyen_presence = round((total_pointages_valides / total_places * 100), 1) if total_places > 0 else 0

    # ── Présence hebdomadaire (Lun → Ven de la semaine en cours) ──
    lundi        = today - datetime.timedelta(days=today.weekday())
    jours_labels = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven']
    presence_hebdo = []
    for i, label in enumerate(jours_labels):
        jour = lundi + datetime.timedelta(days=i)
        presents, absents, en_retard = _stats_du_jour(jour)
        presence_hebdo.append({
            'jour': label, 'date': str(jour),
            'presents': presents, 'absents': absents, 'en_retard': en_retard,
        })

    # ── Évolution du taux de présence (8 dernières semaines) ──
    evolution_taux = []
    for i in range(7, -1, -1):
        lundi_semaine    = lundi - datetime.timedelta(weeks=i)
        dimanche_semaine = lundi_semaine + datetime.timedelta(days=6)
        sessions_semaine = Session.objects.filter(
            statut='TERMINE', date__gte=lundi_semaine, date__lte=dimanche_semaine
        ).select_related('module')
        pointages_valides_semaine = Pointage.objects.filter(
            session__in=sessions_semaine, statut='VALIDE'
        ).count()
        places_semaine = sum(
            Inscription.objects.filter(module=s.module, is_active=True).count()
            for s in sessions_semaine
        )
        taux_semaine = round((pointages_valides_semaine / places_semaine * 100), 1) if places_semaine > 0 else 0
        evolution_taux.append({
            'semaine':       lundi_semaine.strftime('%d/%m'),
            'date_debut':    str(lundi_semaine),
            'taux_presence': taux_semaine,
        })

    # ── Aujourd'hui ──────────────────────────────
    presents_today, absents_today, en_retard_today = _stats_du_jour(today)
    alertes_en_attente = AlerteFraude.objects.filter(statut='NON_TRAITEE').count()

    # ── Dernières alertes de fraude ─────────────
    dernieres = AlerteFraude.objects.select_related(
        'pointage__utilisateur', 'pointage__session__module'
    ).order_by('-timestamp')[:5]
    dernieres_alertes = [{
        'id':              a.id,
        'etudiant_nom':    f'{a.pointage.utilisateur.prenom} {a.pointage.utilisateur.nom}',
        'type_fraude':     a.type_fraude,
        'niveau_severite': a.niveau_severite,
        'statut':          a.statut,
        'score_ia':        a.score_ia,
        'date':            str(a.pointage.session.date),
        'timestamp':       a.timestamp,
    } for a in dernieres]

    # ── Étudiants — taux de présence ────────────
    etudiants_qs = Utilisateur.objects.filter(
        role=Utilisateur.Role.STUDENT, is_active=True
    )
    etudiants_presence = []
    for e in etudiants_qs:
        modules_ids = Inscription.objects.filter(etudiant=e, is_active=True).values_list('module_id', flat=True)
        etudiants_presence.append({
            'id':             str(e.id),
            'nom_complet':    f'{e.prenom} {e.nom}',
            'matricule':      e.matricule,
            'taux_presence':  _taux_presence_etudiant(e, modules_ids),
        })
    etudiants_presence.sort(key=lambda x: x['taux_presence'], reverse=True)

    return Response({
        'etudiants_inscrits':   etudiants_inscrits,
        'taux_moyen_presence':  taux_moyen_presence,
        'fraudes_detectees':    fraudes_detectees,
        'cours_actifs':         cours_actifs,
        'presence_hebdomadaire': presence_hebdo,
        'evolution_taux_presence': evolution_taux,
        'aujourd_hui': {
            'presents':          presents_today,
            'absents':           absents_today,
            'en_retard':         en_retard_today,
            'alertes_en_attente': alertes_en_attente,
        },
        'dernieres_alertes':  dernieres_alertes,
        'etudiants_presence': etudiants_presence,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_cours(request):
    """GET /api/dashboard/cours/ — Données agrégées pour la page Gestion des cours."""
    JOURS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

    modules = Module.objects.select_related('enseignant').all()
    zones   = ZoneGPS.objects.all()

    cours_data = []
    for m in modules:
        session_ref = (
            Session.objects.filter(module=m, statut__in=['PLANIFIE', 'EN_COURS'])
            .select_related('zone').order_by('date', 'heure_debut').first()
            or Session.objects.filter(module=m).select_related('zone').order_by('-date', 'heure_debut').first()
        )

        inscriptions = Inscription.objects.filter(module=m, is_active=True)

        cours_data.append({
            'id':                 m.id,
            'code':               m.code,
            'intitule':           m.intitule,
            'enseignant_nom':     f'{m.enseignant.prenom} {m.enseignant.nom}',
            'seuil_presence_pct': m.seuil_presence_pct,
            'nb_etudiants':       inscriptions.count(),
            'zone': {
                'nom':       session_ref.zone.nom,
                'latitude':  str(session_ref.zone.latitude),
                'longitude': str(session_ref.zone.longitude),
                'rayon_m':   session_ref.zone.rayon_m,
            } if session_ref else None,
            'horaire': (
                f'{JOURS_FR[session_ref.date.weekday()]} '
                f'{str(session_ref.heure_debut)[:5]}-{str(session_ref.heure_fin)[:5]}'
            ) if session_ref else None,
        })

    return Response({
        'cours_configures':  modules.count(),
        'zones_gps_actives': zones.count(),
        'cours':             cours_data,
        'zones':             ZoneGPSSerializer(zones, many=True).data,
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  TABLEAU DE BORD ÉTUDIANT
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_etudiant(request):
    """GET /api/dashboard/etudiant/?utilisateur_id=... — Cours de l'étudiant (avec bouton de
    pointage quand une session est disponible aujourd'hui), stats et historique récent."""
    utilisateur_id = request.query_params.get('utilisateur_id')
    if not utilisateur_id:
        return Response({'error': 'utilisateur_id requis'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        etudiant = Utilisateur.objects.get(id=utilisateur_id, role=Utilisateur.Role.STUDENT)
    except Utilisateur.DoesNotExist:
        return Response({'error': 'Étudiant non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    today = timezone.localdate()

    inscriptions = Inscription.objects.filter(etudiant=etudiant, is_active=True).select_related(
        'module__enseignant'
    )

    cours_data = []
    for insc in inscriptions:
        m = insc.module
        session_today = (
            Session.objects.filter(module=m, date=today).select_related('zone').order_by('heure_debut').first()
        )
        session_info = None
        if session_today:
            deja_pointe = Pointage.objects.filter(utilisateur=etudiant, session=session_today).exists()
            session_info = {
                'id':           session_today.id,
                'statut':       session_today.statut,
                'heure_debut':  str(session_today.heure_debut),
                'heure_fin':    str(session_today.heure_fin),
                'zone': {
                    'nom': session_today.zone.nom,
                    'latitude': str(session_today.zone.latitude),
                    'longitude': str(session_today.zone.longitude),
                    'rayon_m': session_today.zone.rayon_m,
                },
                'deja_pointe':  deja_pointe,
                'peut_pointer': session_today.statut in ('PLANIFIE', 'EN_COURS') and not deja_pointe,
            }
        cours_data.append({
            'id':               m.id,
            'code':             m.code,
            'intitule':         m.intitule,
            'enseignant_nom':   f'{m.enseignant.prenom} {m.enseignant.nom}',
            'session_aujourdhui': session_info,
        })

    # ── Stats de présence globales ──────────────
    # Ne compte que les séances survenues à partir de la date d'inscription de l'étudiant
    # à CHAQUE module (colonne Inscription.date_inscription) : une séance terminée avant
    # son inscription ne doit pas devenir une absence "gratuite" qu'il n'a jamais pu éviter.
    modules_ids       = inscriptions.values_list('module_id', flat=True)
    date_inscription_par_module = {i.module_id: i.date_inscription for i in inscriptions}
    sessions_toutes   = Session.objects.filter(module_id__in=modules_ids, statut='TERMINE')
    ids_valables      = [
        s.id for s in sessions_toutes
        if s.date >= date_inscription_par_module.get(s.module_id, s.date)
    ]
    sessions_terminees = Session.objects.filter(id__in=ids_valables)
    total_sessions      = len(ids_valables)
    # Important : un étudiant peut avoir PLUSIEURS lignes Pointage pour la même séance
    # (ex. il retente après un échec "hors zone" pendant un contrôle périodique). On compte
    # donc des séances distinctes où il a au moins un pointage VALIDE, jamais des lignes brutes,
    # sinon total_present pourrait dépasser total_sessions.
    total_present = Pointage.objects.filter(
        utilisateur=etudiant, session__in=sessions_terminees, statut='VALIDE'
    ).values('session_id').distinct().count()
    total_absent = max(0, total_sessions - total_present)
    taux_presence = round((total_present / total_sessions * 100), 1) if total_sessions > 0 else 0

    # ── Historique récent ────────────────────────
    # On ne montre qu'une ligne par séance (la plus récente), même si l'étudiant a plusieurs
    # tentatives de pointage enregistrées pour cette séance (retries "hors zone") — sinon la
    # liste affiche plus d'entrées que de séances réellement comptées dans les stats ci-dessus.
    historique_brut = Pointage.objects.filter(utilisateur=etudiant).select_related(
        'session__module', 'session__zone'
    ).order_by('-timestamp')
    vues = set()
    historique = []
    for p in historique_brut:
        if p.session_id in vues:
            continue
        vues.add(p.session_id)
        historique.append({
            'id':         p.id,
            'date':       str(p.session.date),
            'cours':      p.session.module.code,
            'lieu':       p.session.zone.nom,
            'timestamp':  p.timestamp.isoformat(),
            'statut':     p.statut,
            'distance_m': p.distance_zone_m,
        })
        if len(historique) >= 10:
            break

    # ── Prochains cours (prochaine séance à venir, par module) ──
    prochains_cours = []
    for insc in inscriptions:
        m = insc.module
        prochaine = (
            Session.objects.filter(module=m, date__gte=today)
            .exclude(statut='ANNULEE')
            .select_related('zone')
            .order_by('date', 'heure_debut')
            .first()
        )
        if prochaine:
            prochains_cours.append({
                'module_id':      m.id,
                'code':           m.code,
                'intitule':       m.intitule,
                'enseignant_nom': f'{m.enseignant.prenom} {m.enseignant.nom}',
                'date':           str(prochaine.date),
                'heure_debut':    str(prochaine.heure_debut),
                'heure_fin':      str(prochaine.heure_fin),
                'lieu':           prochaine.zone.nom,
            })
    prochains_cours.sort(key=lambda c: (c['date'], c['heure_debut']))

    # ── Évolution du taux de présence (par semaine) ─────────────────
    # Regroupement hebdomadaire (année ISO + numéro de semaine), comme pour l'évolution
    # par module côté enseignant : avec seulement quelques jours/semaines de données de
    # démo, un regroupement par mois n'affichait presque jamais qu'un seul point.
    # On raisonne par SÉANCE (pas par ligne Pointage brute) pour rester cohérent avec
    # total_present/total_absent ci-dessus.
    sessions_valide_ids = set(
        Pointage.objects.filter(
            utilisateur=etudiant, session__in=sessions_terminees, statut='VALIDE'
        ).values_list('session_id', flat=True)
    )
    par_semaine = {}
    for s in sessions_terminees:
        annee, semaine, _ = s.date.isocalendar()
        cle = f'{annee}-S{semaine}'
        par_semaine.setdefault(cle, {'present': 0, 'total': 0})
        par_semaine[cle]['total'] += 1
        if s.id in sessions_valide_ids:
            par_semaine[cle]['present'] += 1
    evolution = [
        {'periode': cle, 'taux': round(v['present'] / v['total'] * 100, 1) if v['total'] else 0}
        for cle, v in sorted(par_semaine.items())
    ]

    return Response({
        'etudiant': {
            'nom': etudiant.nom, 'prenom': etudiant.prenom, 'matricule': etudiant.matricule,
        },
        'stats': {
            'taux_presence':  taux_presence,
            'total_present':  total_present,
            'total_absent':   total_absent,
            'total_sessions': total_sessions,
        },
        'cours':           cours_data,
        'prochains_cours': prochains_cours[:5],
        'historique':      historique,
        'evolution':       evolution,
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  TABLEAU DE BORD ENSEIGNANT
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_enseignant(request):
    """GET /api/dashboard/enseignant/?enseignant_id=... — Sessions du jour, absents,
    statistiques par module (taux, évolution, distribution) et étudiants inscrits,
    pour les modules de CET enseignant uniquement."""
    enseignant_id = request.query_params.get('enseignant_id')
    if not enseignant_id:
        return Response({'error': 'enseignant_id requis'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        enseignant = Utilisateur.objects.get(id=enseignant_id, role=Utilisateur.Role.TEACHER)
    except Utilisateur.DoesNotExist:
        return Response({'error': 'Enseignant non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    today   = timezone.localdate()
    modules = Module.objects.filter(enseignant=enseignant).select_related('enseignant')

    # ── Sessions du jour (pour les modules de cet enseignant) ────
    sessions_today = Session.objects.filter(module__in=modules, date=today).select_related('module', 'zone')
    sessions_du_jour = []
    total_presents_actifs, total_inscrits_actifs, nb_sessions_actives = 0, 0, 0

    for s in sessions_today:
        inscrits   = Inscription.objects.filter(module=s.module, is_active=True).count()
        pointages  = Pointage.objects.filter(session=s, statut='VALIDE')
        nb_presents = pointages.count()
        taux_pct    = round((nb_presents / inscrits * 100), 0) if inscrits > 0 else 0

        sessions_du_jour.append({
            'id': s.id, 'module_id': s.module.id, 'code': s.module.code, 'intitule': s.module.intitule,
            'statut': s.statut, 'heure_debut': str(s.heure_debut), 'heure_fin': str(s.heure_fin),
            'zone': s.zone.nom, 'nb_inscrits': inscrits, 'nb_presents': nb_presents, 'taux_pct': taux_pct,
        })

        if s.statut == Session.Statut.EN_COURS:
            nb_sessions_actives += 1
            total_presents_actifs += nb_presents
            total_inscrits_actifs += inscrits

    sessions_du_jour.sort(key=lambda x: x['heure_debut'])

    # ── Statistiques par module (taux, absents, évolution, distribution, étudiants) ──
    modules_data = []
    somme_taux_modules = 0
    for m in modules:
        inscriptions = Inscription.objects.filter(module=m, is_active=True).select_related('etudiant')
        sessions_terminees_m = Session.objects.filter(module=m, statut='TERMINE')
        nb_sessions_terminees = sessions_terminees_m.count()

        etudiants_data = []
        absents_aujourdhui = []
        somme_taux_etudiants = 0
        session_aujourdhui_m = next((s for s in sessions_today if s.module_id == m.id), None)
        pointes_aujourdhui_ids = set()
        if session_aujourdhui_m:
            pointes_aujourdhui_ids = set(
                Pointage.objects.filter(session=session_aujourdhui_m, statut='VALIDE')
                .values_list('utilisateur_id', flat=True)
            )

        for insc in inscriptions:
            e = insc.etudiant
            presences = Pointage.objects.filter(utilisateur=e, session__in=sessions_terminees_m, statut='VALIDE').count()
            taux = round((presences / nb_sessions_terminees * 100), 1) if nb_sessions_terminees > 0 else 0
            somme_taux_etudiants += taux
            etudiants_data.append({
                'id': str(e.id), 'matricule': e.matricule, 'nom': e.nom, 'prenom': e.prenom, 'email': e.email,
                'presences': presences, 'total_sessions': nb_sessions_terminees, 'taux_presence': taux,
                'statut': 'OK' if taux >= m.seuil_presence_pct else 'SOUS_SEUIL',
            })
            if session_aujourdhui_m and e.id not in pointes_aujourdhui_ids:
                absents_aujourdhui.append({
                    'id': str(e.id), 'matricule': e.matricule,
                    'nom_complet': f'{e.prenom} {e.nom}', 'email': e.email,
                    'total_absences': nb_sessions_terminees - presences,
                })

        taux_moyen_module = round(somme_taux_etudiants / len(etudiants_data), 1) if etudiants_data else 0
        somme_taux_modules += taux_moyen_module

        # Évolution du taux moyen du module, semaine par semaine (basé sur les séances réelles).
        par_semaine = {}
        pointages_module = Pointage.objects.filter(session__in=sessions_terminees_m).select_related('session')
        for p in pointages_module:
            annee, semaine, _ = p.session.date.isocalendar()
            cle = f'{annee}-S{semaine}'
            par_semaine.setdefault(cle, {'present': 0, 'total': 0})
            par_semaine[cle]['total'] += 1
            if p.statut == 'VALIDE':
                par_semaine[cle]['present'] += 1
        evolution_module = [
            {'semaine': cle, 'taux': round(v['present'] / v['total'] * 100, 1) if v['total'] else 0}
            for cle, v in sorted(par_semaine.items())
        ]

        # Distribution présent / en retard / absent, sur toutes les séances terminées du module.
        total_places = nb_sessions_terminees * len(etudiants_data)
        nb_present_ok, nb_retard = 0, 0
        for p in pointages_module:
            if p.statut != 'VALIDE':
                continue
            limite = (datetime.datetime.combine(p.session.date, p.session.heure_debut) + datetime.timedelta(minutes=RETARD_TOLERANCE_MIN)).time()
            if timezone.localtime(p.timestamp).time() > limite:
                nb_retard += 1
            else:
                nb_present_ok += 1
        nb_absent = max(0, total_places - nb_present_ok - nb_retard)
        distribution = {
            'present': round(nb_present_ok / total_places * 100, 1) if total_places else 0,
            'retard':  round(nb_retard / total_places * 100, 1) if total_places else 0,
            'absent':  round(nb_absent / total_places * 100, 1) if total_places else 0,
        }

        modules_data.append({
            'id': m.id, 'code': m.code, 'intitule': m.intitule, 'seuil_presence_pct': m.seuil_presence_pct,
            'taux_moyen': taux_moyen_module,
            'etudiants': etudiants_data,
            'absents_aujourdhui': absents_aujourdhui,
            'evolution': evolution_module,
            'distribution': distribution,
        })

    taux_moyen_global = round(somme_taux_modules / len(modules_data), 1) if modules_data else 0

    return Response({
        'enseignant': {'nom': enseignant.nom, 'prenom': enseignant.prenom},
        'stats': {
            'sessions_aujourdhui': len(sessions_du_jour),
            'session_active':      nb_sessions_actives,
            'presents_maintenant': f'{total_presents_actifs}/{total_inscrits_actifs}' if nb_sessions_actives else '0/0',
            'taux_moyen_global':   taux_moyen_global,
        },
        'sessions_du_jour': sessions_du_jour,
        'modules':          modules_data,
    }, status=status.HTTP_200_OK)