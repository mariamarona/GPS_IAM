from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    UtilisateurViewSet, ModuleViewSet, ZoneGPSViewSet,
    SessionViewSet, PointageViewSet, AlerteFraudeViewSet, InscriptionViewSet,
    dashboard_admin, dashboard_cours, dashboard_etudiant, dashboard_enseignant,
)
from .auth_views import login, logout, refresh_token, change_password
from .reports import export_rapport_excel

router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet)
router.register(r'modules',      ModuleViewSet)
router.register(r'zones',        ZoneGPSViewSet)
router.register(r'sessions',     SessionViewSet)
router.register(r'pointages',    PointageViewSet)
router.register(r'alertes',      AlerteFraudeViewSet)
router.register(r'inscriptions', InscriptionViewSet)

urlpatterns = [
    # ── Auth ────────────────────────────────────
    path('auth/login/',           login,           name='login'),
    path('auth/logout/',          logout,          name='logout'),
    path('auth/refresh/',         refresh_token,   name='refresh'),
    path('auth/change-password/', change_password, name='change-password'),

    # ── Tableau de bord ─────────────────────────
    path('dashboard/admin/',     dashboard_admin,     name='dashboard-admin'),
    path('dashboard/cours/',     dashboard_cours,     name='dashboard-cours'),
    path('dashboard/etudiant/',  dashboard_etudiant,  name='dashboard-etudiant'),
    path('dashboard/enseignant/', dashboard_enseignant, name='dashboard-enseignant'),

    # ── Rapports ────────────────────────────────
    path('rapports/export/', export_rapport_excel, name='export-rapport'),

    # ── Entités ─────────────────────────────────
    path('', include(router.urls)),
]