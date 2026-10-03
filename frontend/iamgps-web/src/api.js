// ─────────────────────────────────────────────
//  Client API — IAMGPS (backend Django REST)
// ─────────────────────────────────────────────
import auth from './auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const token = auth.getAccessToken()
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/login/') {
      auth.clearSession()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    let detail = ''
    try {
      const body = await res.json()
      detail = body.error || JSON.stringify(body)
    } catch {
      detail = res.statusText
    }
    throw new Error(`Erreur API (${res.status}) sur ${path} : ${detail}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Authentification
  login: (email, mot_de_passe) =>
    request('/auth/login/', { method: 'POST', body: JSON.stringify({ email, mot_de_passe }) }),
  logout: (refresh) =>
    request('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh }) }),

  // Tableau de bord
  getDashboardAdmin: () => request('/dashboard/admin/'),
  getDashboardEtudiant: (utilisateurId) => request(`/dashboard/etudiant/?utilisateur_id=${utilisateurId}`),
  getDashboardEnseignant: (enseignantId) => request(`/dashboard/enseignant/?enseignant_id=${enseignantId}`),

  // Sessions (démarrer / terminer une séance — espace enseignant)
  demarrerSession: (sessionId) => request(`/sessions/${sessionId}/demarrer/`, { method: 'POST' }),
  terminerSession: (sessionId) => request(`/sessions/${sessionId}/terminer/`, { method: 'POST' }),
  demarrerModule: (moduleId) => request(`/modules/${moduleId}/demarrer-session/`, { method: 'POST' }),

  // Alertes de fraude
  getAlertesDashboard: () => request('/alertes/dashboard/'),
  getAlertesNonTraitees: () => request('/alertes/non-traitees/'),
  getAlertes: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/alertes/${qs ? `?${qs}` : ''}`)
  },
  traiterAlerte: (id, payload) =>
    request(`/alertes/${id}/traiter/`, { method: 'PATCH', body: JSON.stringify(payload) }),

  // Corriger une présence — cas simple : un pointage existe déjà (lié à une alerte),
  // on change juste son statut (ex: HORS_ZONE -> VALIDE après vérification manuelle).
  corrigerPointage: (pointageId, statut) =>
    request(`/pointages/${pointageId}/`, { method: 'PATCH', body: JSON.stringify({ statut }) }),
  // Cas général (utilisé pour un étudiant absent, sans aucun pointage) : voir
  // POST /api/pointages/corriger/ côté backend.
  corrigerPresenceAbsente: (payload) =>
    request('/pointages/corriger/', { method: 'POST', body: JSON.stringify(payload) }),

  // Cours / Modules
  getModules: () => request('/modules/'),
  getModuleStats: (id) => request(`/modules/${id}/stats/`),
  getDashboardCours: () => request('/dashboard/cours/'),
  createModule: (payload) => request('/modules/', { method: 'POST', body: JSON.stringify(payload) }),
  updateModule: (id, payload) => request(`/modules/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteModule: (id) => request(`/modules/${id}/`, { method: 'DELETE' }),

  // Sessions
  getSessionsAujourdhui: () => request('/sessions/aujourd-hui/'),
  getSessions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/sessions/${qs ? `?${qs}` : ''}`)
  },

  // Pointage GPS (espace étudiant)
  validerPointage: (payload) =>
    request('/pointages/valider/', { method: 'POST', body: JSON.stringify(payload) }),

  // Utilisateurs (gestion admin + liste des enseignants ailleurs dans l'appli)
  getUtilisateurs: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/utilisateurs/${qs ? `?${qs}` : ''}`)
  },
  getProchainMatricule: () => request('/utilisateurs/prochain-matricule/'),
  createUtilisateur: (payload) =>
    request('/utilisateurs/', { method: 'POST', body: JSON.stringify(payload) }),
  updateUtilisateur: (id, payload) =>
    request(`/utilisateurs/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteUtilisateur: (id) => request(`/utilisateurs/${id}/`, { method: 'DELETE' }),

  // Inscriptions (inscrire un étudiant à un cours — espace admin)
  getInscriptions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/inscriptions/${qs ? `?${qs}` : ''}`)
  },
  createInscription: (payload) =>
    request('/inscriptions/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteInscription: (id) => request(`/inscriptions/${id}/`, { method: 'DELETE' }),

  // Rapports (espace admin) — télécharge le classeur Excel et déclenche
  // l'enregistrement côté navigateur. `params` accepte : module, date_debut, date_fin.
  telechargerRapport: async (params = {}) => {
    const token = auth.getAccessToken()
    const qs = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/rapports/export/${qs ? `?${qs}` : ''}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (!res.ok) {
      throw new Error(`Impossible de générer le rapport (${res.status})`)
    }
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const lien = document.createElement('a')
    lien.href = url
    const dispo = res.headers.get('Content-Disposition') || ''
    const match = dispo.match(/filename="?([^"]+)"?/)
    lien.download = match ? match[1] : 'rapport_iamgps.xlsx'
    document.body.appendChild(lien)
    lien.click()
    lien.remove()
    window.URL.revokeObjectURL(url)
  },
}

export default api