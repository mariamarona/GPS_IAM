from django.contrib import admin
from .models import Utilisateur, Module, Session, ZoneGPS, Pointage, AlerteFraude, Inscription


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display  = ('matricule', 'prenom', 'nom', 'email', 'role', 'is_active', 'last_login')
    list_filter   = ('role', 'is_active')
    search_fields = ('matricule', 'email', 'nom', 'prenom')
    readonly_fields = ('id', 'created_at', 'last_login')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display  = ('code', 'intitule', 'enseignant', 'seuil_presence_pct')
    search_fields = ('code', 'intitule')


@admin.register(ZoneGPS)
class ZoneGPSAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'latitude', 'longitude', 'rayon_m', 'updated_at')
    search_fields = ('nom',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display  = ('module', 'zone', 'date', 'heure_debut', 'heure_fin', 'statut', 'created_by')
    list_filter   = ('statut',)
    search_fields = ('module__code',)
    date_hierarchy = 'date'


@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display   = ('utilisateur', 'session', 'timestamp', 'statut', 'distance_zone_m', 'is_offline_sync')
    list_filter    = ('statut', 'is_offline_sync')
    search_fields  = ('utilisateur__matricule',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)


@admin.register(AlerteFraude)
class AlerteFraudeAdmin(admin.ModelAdmin):
    list_display   = ('pointage', 'type_fraude', 'niveau_severite', 'score_ia', 'statut', 'traite_par', 'timestamp')
    list_filter    = ('type_fraude', 'niveau_severite', 'statut')
    search_fields  = ('pointage__utilisateur__matricule',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display  = ('etudiant', 'module', 'date_inscription', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('etudiant__matricule', 'module__code')