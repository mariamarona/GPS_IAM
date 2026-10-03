// ─────────────────────────────────────────────
//  Gestion de la session — IAMGPS
// ─────────────────────────────────────────────
const STORAGE_KEY = 'iamgps_session'

function readSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeSession(session) {
  if (session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export const auth = {
  /** Session actuelle : { access, refresh, utilisateur } ou null si non connecté. */
  getSession() {
    return readSession()
  },

  getAccessToken() {
    return readSession()?.access || null
  },

  getUtilisateur() {
    return readSession()?.utilisateur || null
  },

  isAuthenticated() {
    return !!readSession()?.access
  },

  /** Enregistre la session après un login réussi. */
  setSession(session) {
    writeSession(session)
  },

  /** Efface la session locale (à utiliser après l'appel API /auth/logout/). */
  clearSession() {
    writeSession(null)
  },
}

export default auth
