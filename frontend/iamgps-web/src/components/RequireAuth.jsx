import { Navigate, useLocation } from 'react-router-dom'
import auth from '../auth'

/**
 * Protège une branche de routes : redirige vers /login si non connecté.
 * Si `allowedRoles` est fourni, redirige aussi les utilisateurs connectés mais dont le
 * rôle ne correspond pas vers leur propre espace (évite qu'un étudiant connecté tape
 * l'URL admin dans la barre d'adresse, et inversement).
 */
export default function RequireAuth({ children, allowedRoles }) {
  const location = useLocation()

  if (!auth.isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (allowedRoles) {
    const role = auth.getUtilisateur()?.role
    if (!allowedRoles.includes(role)) {
      const fallback = role === 'TEACHER' ? '/enseignant' : '/'
      return <Navigate to={fallback} replace />
    }
  }

  return children
}
