import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { MapPin, Loader2 } from 'lucide-react'
import api from '../api'
import auth from '../auth'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await api.login(email.trim(), motDePasse)
      const role = res.utilisateur.role
      if (!['ADMIN', 'SUPER_ADMIN', 'TEACHER'].includes(role)) {
        setError(
          "Ce compte existe mais son rôle n'est pas encore pris en charge par cette interface web "
          + "(les étudiants utilisent l'application mobile)."
        )
        return
      }
      auth.setSession(res)
      const defaultRoute = role === 'TEACHER' ? '/enseignant' : '/'
      const redirectTo = location.state?.from || defaultRoute
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err.message.includes('401') ? 'Email ou mot de passe incorrect.' : err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-brand-icon">
            <MapPin size={22} strokeWidth={2.4} />
          </span>
          <div>
            <div className="login-brand-title">IAMGPS</div>
            <div className="login-brand-subtitle">Présence &amp; Détection IA</div>
          </div>
        </div>

        <h1>Connexion</h1>
        <p className="login-subtitle">Espace Administrateur &amp; Enseignant</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label className="login-field">
            <span>Adresse email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder=""
              autoComplete="email"
              required
            />
          </label>

          <label className="login-field">
            <span>Mot de passe</span>
            <input
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              placeholder=""
              autoComplete="current-password"
              required
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? <Loader2 size={16} className="login-spinner" /> : null}
            {loading ? 'Connexion…' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  )
}
