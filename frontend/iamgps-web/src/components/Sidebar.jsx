import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  MapPin,
  ShieldCheck,
  LayoutGrid,
  TriangleAlert,
  BookOpen,
  Users,
  User,
  LogOut,
  Loader2,
} from 'lucide-react'
import api from '../api'
import auth from '../auth'
import './Sidebar.css'

const ADMIN_NAV_ITEMS = [
  { to: '/', label: 'Tableau de bord', icon: LayoutGrid, end: true },
  { to: '/alertes', label: 'Alertes de fraude', icon: TriangleAlert },
  { to: '/cours', label: 'Gestion des cours', icon: BookOpen },
  { to: '/utilisateurs', label: 'Utilisateurs', icon: Users },
]

const ROLE_LABEL = {
  ADMIN: 'Administrateur',
  SUPER_ADMIN: 'Super Administrateur',
  TEACHER: 'Enseignant',
  STUDENT: 'Étudiant',
}

export default function Sidebar({ navItems = ADMIN_NAV_ITEMS, badgeLabel = 'Espace Administrateur' }) {
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const utilisateur = auth.getUtilisateur()
  const nomComplet = utilisateur ? `${utilisateur.prenom} ${utilisateur.nom}` : 'Utilisateur'
  const roleLabel = ROLE_LABEL[utilisateur?.role] || 'Administrateur'

  async function handleLogout() {
    setLoggingOut(true)
    const session = auth.getSession()
    try {
      if (session?.refresh) {
        await api.logout(session.refresh)
      }
    } catch {
      // On déconnecte localement même si l'appel réseau échoue (token déjà expiré, etc.)
    } finally {
      auth.clearSession()
      navigate('/login', { replace: true })
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <span className="sidebar-brand-icon">
            <MapPin size={20} strokeWidth={2.4} />
          </span>
          <div>
            <div className="sidebar-brand-title">IAMGPS</div>
            <div className="sidebar-brand-subtitle">Présence &amp; Détection IA</div>
          </div>
        </div>

        <div className="sidebar-role-badge">
          <ShieldCheck size={16} />
          <span>{badgeLabel}</span>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-user">
          <span className="sidebar-user-avatar">
            <User size={18} />
          </span>
          <div>
            <div className="sidebar-user-name">{nomComplet}</div>
            <div className="sidebar-user-role">{roleLabel}</div>
          </div>
        </div>
        <button type="button" className="sidebar-logout" onClick={handleLogout} disabled={loggingOut}>
          {loggingOut ? <Loader2 size={16} className="sidebar-logout-spinner" /> : <LogOut size={16} />}
          <span>Déconnexion</span>
        </button>
      </div>
    </aside>
  )
}