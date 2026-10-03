// Libellés et couleurs partagés entre la page Alertes et le Tableau de bord.

export const TYPE_LABEL = {
  hors_zone: 'Hors zone GPS',
  doublon: 'Pointage en double',
  coords_fixes: 'Coordonnées GPS fixes',
  heure_invalide: 'Heure invalide',
  spoofing_gps: 'Spoofing GPS',
  autre: 'Autre',
}

export const STATUT_BADGE = {
  NON_TRAITEE: { label: 'Non traitée', bg: 'var(--red-light)', color: 'var(--red)' },
  EN_INVESTIGATION: { label: 'Investigation', bg: 'var(--orange-light)', color: 'var(--orange)' },
  FRAUDE_CONFIRMEE: { label: 'Confirmée', bg: '#dc2626', color: '#ffffff' },
  FAUSSE_ALERTE: { label: 'Fausse alerte', bg: 'var(--green-light)', color: 'var(--green)' },
}

export const NIVEAU_BADGE = {
  FAIBLE: { color: 'var(--text-secondary)', bg: '#f1f2f5' },
  MOYEN: { color: '#b45309', bg: '#fef3c7' },
  ELEVE: { color: '#c2410c', bg: '#ffedd5' },
  CRITIQUE: { color: 'var(--red)', bg: 'var(--red-light)' },
}

// Couleur de la barre "Score IA" selon le score (0-100)
export function scoreColor(score) {
  if (score >= 90) return '#dc2626'
  if (score >= 70) return '#f59e0b'
  if (score >= 40) return '#eab308'
  return '#3b82f6'
}

// Fiche descriptive du modèle IA affichée dans le panneau "Voir le modèle IA".
// Ces informations correspondent exactement à ce qui est implémenté dans
// backend/api/fraud_detection.py (FEATURE_NAMES, niveau_severite, MODEL_VERSION_LABEL).
// Le système passe automatiquement par 3 niveaux de détection selon les données
// disponibles : heuristique (règles pondérées) → IsolationForest (non supervisé,
// dès le premier pointage) → RandomForest (supervisé, dès qu'au moins 10 alertes
// ont été confirmées/rejetées par un admin, via `python manage.py train_fraud_model`).
// Il n'y a volontairement PAS de précision/rappel/F1 affichés ici : ces métriques
// supposeraient un jeu de test étiqueté déjà évalué, ce qui n'est pas encore le cas
// avec le volume de données actuel — les afficher inventerait des chiffres.
export const IA_MODEL_INFO = {
  name: 'IAMGPS-FraudNet',
  version: '1.0',
  levels: [
    { key: 'heuristique', label: 'Heuristique (règles pondérées)', detail: 'Utilisé tant qu\'aucun modèle ML n\'a été entraîné.' },
    { key: 'ml_non_supervise', label: 'IsolationForest (scikit-learn, non supervisé)', detail: 'Détection d\'anomalies, actif dès le premier lancement de l\'entraînement.' },
    { key: 'ml_supervise', label: 'RandomForest (scikit-learn, supervisé)', detail: 'Prend le relais dès que ≥ 10 alertes ont été confirmées ou rejetées par un admin.' },
  ],
  features: [
    'Distance à la zone autorisée (ratio)',
    'Précision GPS reportée par le téléphone',
    'Minutes de retard par rapport au début de séance',
    'Vitesse de déplacement depuis le pointage précédent',
    'Nombre de pointages récents à des coordonnées quasi identiques',
    'Doublon (pointage déjà validé sur la même séance)',
  ],
}