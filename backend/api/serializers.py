from rest_framework import serializers
from .models import Utilisateur, Module, ZoneGPS, Session, Pointage, AlerteFraude, Inscription
import bcrypt
import datetime


# ─────────────────────────────────────────────
#  UTILISATEUR
# ─────────────────────────────────────────────
class UtilisateurSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Utilisateur
        fields = ['id', 'matricule', 'nom', 'prenom', 'email',
                  'mot_de_passe', 'role', 'is_active', 'created_at', 'last_login']
        extra_kwargs = {
            'mot_de_passe': {'write_only': True},   # jamais renvoyé en GET
            'id':           {'read_only': True},
            'created_at':   {'read_only': True},
            'last_login':   {'read_only': True},
        }

    def create(self, validated_data):
        # Hashage bcrypt avant sauvegarde
        raw_password = validated_data['mot_de_passe']
        hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
        validated_data['mot_de_passe'] = hashed.decode('utf-8')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'mot_de_passe' in validated_data:
            raw_password = validated_data['mot_de_passe']
            hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
            validated_data['mot_de_passe'] = hashed.decode('utf-8')
        return super().update(instance, validated_data)


# ─────────────────────────────────────────────
#  MODULE
# ─────────────────────────────────────────────
JOURS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']


class ModuleSerializer(serializers.ModelSerializer):
    enseignant_nom = serializers.SerializerMethodField(read_only=True)
    zone           = serializers.SerializerMethodField(read_only=True)
    planning       = serializers.SerializerMethodField(read_only=True)
    nb_etudiants   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Module
        fields = ['id', 'code', 'intitule', 'enseignant', 'enseignant_nom',
                  'seuil_presence_pct', 'created_at',
                  'zone', 'planning', 'nb_etudiants']
        extra_kwargs = {'created_at': {'read_only': True}}

    def get_enseignant_nom(self, obj):
        return f"{obj.enseignant.prenom} {obj.enseignant.nom}"

    def _session_reference(self, obj):
        # Session la plus proche/ancienne du module, utilisée comme "planning type" à afficher.
        return obj.sessions.select_related('zone').order_by('date', 'heure_debut').first()

    def get_zone(self, obj):
        s = self._session_reference(obj)
        if not s:
            return None
        return {
            'nom': s.zone.nom, 'latitude': str(s.zone.latitude),
            'longitude': str(s.zone.longitude), 'rayon_m': s.zone.rayon_m,
        }

    def get_planning(self, obj):
        s = self._session_reference(obj)
        if not s:
            return None
        return {
            'jour': JOURS_FR[s.date.weekday()],
            'heure_debut': str(s.heure_debut),
            'heure_fin': str(s.heure_fin),
        }

    def get_nb_etudiants(self, obj):
        return obj.inscriptions.filter(is_active=True).count()


# ─────────────────────────────────────────────
#  ZONE GPS
# ─────────────────────────────────────────────
class ZoneGPSSerializer(serializers.ModelSerializer):

    class Meta:
        model  = ZoneGPS
        fields = ['id', 'nom', 'latitude', 'longitude', 'rayon_m', 'created_at', 'updated_at']
        extra_kwargs = {
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }


# ─────────────────────────────────────────────
#  SESSION
# ─────────────────────────────────────────────
class SessionSerializer(serializers.ModelSerializer):
    module_code = serializers.SerializerMethodField(read_only=True)
    zone_nom    = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Session
        fields = ['id', 'module', 'module_code', 'zone', 'zone_nom',
                  'date', 'heure_debut', 'heure_fin', 'statut', 'created_by']

    def get_module_code(self, obj):
        return obj.module.code

    def get_zone_nom(self, obj):
        return obj.zone.nom

    def validate(self, data):
        heure_debut = data.get('heure_debut')
        heure_fin   = data.get('heure_fin')
        heure_min   = datetime.time(8, 0)
        heure_max   = datetime.time(18, 0)

        if heure_debut and heure_debut < heure_min:
            raise serializers.ValidationError(
                {'heure_debut': 'Les cours commencent au plus tôt à 08h00'}
            )
        if heure_fin and heure_fin > heure_max:
            raise serializers.ValidationError(
                {'heure_fin': 'Les cours se terminent au plus tard à 18h00'}
            )
        if heure_debut and heure_fin and heure_debut >= heure_fin:
            raise serializers.ValidationError(
                {'heure_fin': 'L\'heure de fin doit être après l\'heure de début'}
            )
        return data


# ─────────────────────────────────────────────
#  POINTAGE
# ─────────────────────────────────────────────
class PointageSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Pointage
        fields = ['id', 'utilisateur', 'session', 'timestamp',
                  'latitude', 'longitude', 'precision_gps_m',
                  'distance_zone_m', 'is_offline_sync', 'offline_sync_at', 'statut']
        extra_kwargs = {'timestamp': {'read_only': True}}


# ─────────────────────────────────────────────
#  ALERTE FRAUDE
# ─────────────────────────────────────────────
class AlerteFraudeSerializer(serializers.ModelSerializer):
    etudiant_nom       = serializers.SerializerMethodField(read_only=True)
    etudiant_matricule = serializers.SerializerMethodField(read_only=True)
    module_code        = serializers.SerializerMethodField(read_only=True)
    date_session       = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = AlerteFraude
        fields = ['id', 'pointage', 'type_fraude', 'score_ia',
                  'niveau_severite', 'statut', 'traite_par',
                  'commentaire', 'analyse_ia', 'timestamp', 'traite_at',
                  'etudiant_nom', 'etudiant_matricule', 'module_code', 'date_session']
        extra_kwargs = {'timestamp': {'read_only': True}}

    def get_etudiant_nom(self, obj):
        u = obj.pointage.utilisateur
        return f"{u.prenom} {u.nom}"

    def get_etudiant_matricule(self, obj):
        return obj.pointage.utilisateur.matricule

    def get_module_code(self, obj):
        return obj.pointage.session.module.code

    def get_date_session(self, obj):
        return str(obj.pointage.session.date)


# ─────────────────────────────────────────────
#  INSCRIPTION
# ─────────────────────────────────────────────
class InscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Inscription
        fields = ['id', 'etudiant', 'module', 'date_inscription', 'is_active']
