import { useEffect, useMemo, useState } from 'react'
import { Users, UserPlus, Pencil, Trash2, Power, Search, X } from 'lucide-react'
import api from '../api'
import StatCard from '../components/StatCard'
import './Utilisateurs.css'

const ROLE_LABEL = {
  STUDENT: 'Étudiant',
  TEACHER: 'Enseignant',
  ADMIN: 'Administrateur',
  SUPER_ADMIN: 'Super Administrateur',
}

const ROLE_TONE = {
  STUDENT: 'blue',
  TEACHER: 'purple',
  ADMIN: 'orange',
  SUPER_ADMIN: 'orange',
}

const ONGLETS = [
  { valeur: 'TOUS', label: 'Tous' },
  { valeur: 'STUDENT', label: 'Étudiants' },
  { valeur: 'TEACHER', label: 'Enseignants' },
  { valeur: 'ADMIN', label: 'Administrateurs' },
]

const FORM_VIDE = {
  matricule: '',
  nom: '',
  prenom: '',
  email: '',
  role: 'STUDENT',
  mot_de_passe: '',
  is_active: true,
}

export default function Utilisateurs() {
  const [utilisateurs, setUtilisateurs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [onglet, setOnglet] = useState('TOUS')
  const [recherche, setRecherche] = useState('')

  const [modalOuvert, setModalOuvert] = useState(false)
  const [modeEdition, setModeEdition] = useState(false)
  const [idEnEdition, setIdEnEdition] = useState(null)
  const [form, setForm] = useState(FORM_VIDE)
  const [formErreur, setFormErreur] = useState(null)
  const [envoiEnCours, setEnvoiEnCours] = useState(false)

  function chargerUtilisateurs() {
    setLoading(true)
    api
      .getUtilisateurs()
      .then((res) => setUtilisateurs(res))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    chargerUtilisateurs()
  }, [])

  const stats = useMemo(() => {
    const total = utilisateurs.length
    const etudiants = utilisateurs.filter((u) => u.role === 'STUDENT').length
    const enseignants = utilisateurs.filter((u) => u.role === 'TEACHER').length
    const admins = utilisateurs.filter((u) => u.role === 'ADMIN' || u.role === 'SUPER_ADMIN').length
    return { total, etudiants, enseignants, admins }
  }, [utilisateurs])

  const listeAffichee = useMemo(() => {
    let liste = utilisateurs
    if (onglet !== 'TOUS') {
      liste = liste.filter((u) => u.role === onglet)
    }
    const q = recherche.trim().toLowerCase()
    if (q) {
      liste = liste.filter(
        (u) =>
          u.matricule.toLowerCase().includes(q) ||
          u.nom.toLowerCase().includes(q) ||
          u.prenom.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q)
      )
    }
    return liste
  }, [utilisateurs, onglet, recherche])

  function ouvrirAjout() {
    setModeEdition(false)
    setIdEnEdition(null)
    setFormErreur(null)
    setForm(FORM_VIDE)
    setModalOuvert(true)
    api
      .getProchainMatricule()
      .then((res) => setForm((f) => ({ ...f, matricule: res.matricule })))
      .catch(() => {
        /* pas bloquant : l'admin peut saisir le matricule à la main */
      })
  }

  function ouvrirEdition(u) {
    setModeEdition(true)
    setIdEnEdition(u.id)
    setFormErreur(null)
    setForm({
      matricule: u.matricule,
      nom: u.nom,
      prenom: u.prenom,
      email: u.email,
      role: u.role,
      mot_de_passe: '',
      is_active: u.is_active,
    })
    setModalOuvert(true)
  }

  function fermerModal() {
    setModalOuvert(false)
  }

  function handleChange(champ, valeur) {
    setForm((f) => ({ ...f, [champ]: valeur }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setFormErreur(null)
    setEnvoiEnCours(true)

    const payload = {
      matricule: form.matricule.trim(),
      nom: form.nom.trim(),
      prenom: form.prenom.trim(),
      email: form.email.trim(),
      role: form.role,
    }
    if (!modeEdition) {
      payload.mot_de_passe = form.mot_de_passe
    } else {
      payload.is_active = form.is_active
      if (form.mot_de_passe) {
        payload.mot_de_passe = form.mot_de_passe
      }
    }

    const requete = modeEdition
      ? api.updateUtilisateur(idEnEdition, payload)
      : api.createUtilisateur(payload)

    requete
      .then(() => {
        setModalOuvert(false)
        chargerUtilisateurs()
      })
      .catch((err) => setFormErreur(err.message))
      .finally(() => setEnvoiEnCours(false))
  }

  function toggleActivation(u) {
    api
      .updateUtilisateur(u.id, { is_active: !u.is_active })
      .then(() =>
        setUtilisateurs((liste) =>
          liste.map((x) => (x.id === u.id ? { ...x, is_active: !u.is_active } : x))
        )
      )
      .catch((err) => alert(err.message))
  }

  function supprimer(u) {
    const nomComplet = `${u.prenom} ${u.nom}`
    if (!window.confirm(`Supprimer définitivement ${nomComplet} (${u.matricule}) ? Cette action est irréversible.`)) {
      return
    }
    api
      .deleteUtilisateur(u.id)
      .then(() => setUtilisateurs((liste) => liste.filter((x) => x.id !== u.id)))
      .catch((err) => alert(err.message))
  }

  return (
    <>
      <div className="page-header">
        <h1>Gestion des utilisateurs</h1>
        <p>Créer, modifier, désactiver ou supprimer les comptes étudiants, enseignants et administrateurs</p>
      </div>

      <div className="stat-grid">
        <StatCard label="Utilisateurs" value={stats.total} icon={Users} tone="blue" />
        <StatCard label="Étudiants" value={stats.etudiants} icon={Users} tone="blue" />
        <StatCard label="Enseignants" value={stats.enseignants} icon={Users} tone="purple" />
        <StatCard label="Administrateurs" value={stats.admins} icon={Users} tone="orange" />
      </div>

      {error && <div className="state-msg error">Impossible de charger les utilisateurs ({error}).</div>}

      <div className="card users-card">
        <div className="users-toolbar">
          <div className="users-tabs">
            {ONGLETS.map((o) => (
              <button
                key={o.valeur}
                type="button"
                className={`users-tab${onglet === o.valeur ? ' active' : ''}`}
                onClick={() => setOnglet(o.valeur)}
              >
                {o.label}
              </button>
            ))}
          </div>

          <div className="users-toolbar-right">
            <div className="users-search">
              <Search size={16} />
              <input
                type="text"
                placeholder="Rechercher (nom, matricule, email)…"
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
              />
            </div>
            <button type="button" className="btn btn-primary" onClick={ouvrirAjout}>
              <UserPlus size={16} />
              Ajouter un utilisateur
            </button>
          </div>
        </div>

        {loading ? (
          <div className="state-msg">Chargement…</div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>Matricule</th>
                <th>Nom</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th className="users-col-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {listeAffichee.map((u) => (
                <tr key={u.id}>
                  <td className="users-matricule">{u.matricule}</td>
                  <td>{u.prenom} {u.nom}</td>
                  <td className="users-email">{u.email}</td>
                  <td>
                    <span className={`badge badge-${ROLE_TONE[u.role]}`}>{ROLE_LABEL[u.role] || u.role}</span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? 'badge-green' : 'badge-red'}`}>
                      {u.is_active ? 'Actif' : 'Désactivé'}
                    </span>
                  </td>
                  <td className="users-col-actions">
                    <button type="button" className="users-icon-btn" title="Modifier" onClick={() => ouvrirEdition(u)}>
                      <Pencil size={16} />
                    </button>
                    <button
                      type="button"
                      className="users-icon-btn"
                      title={u.is_active ? 'Désactiver' : 'Réactiver'}
                      onClick={() => toggleActivation(u)}
                    >
                      <Power size={16} />
                    </button>
                    <button
                      type="button"
                      className="users-icon-btn users-icon-btn-danger"
                      title="Supprimer"
                      onClick={() => supprimer(u)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {listeAffichee.length === 0 && (
                <tr>
                  <td colSpan={6} className="state-msg">
                    Aucun utilisateur ne correspond à ce filtre.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {modalOuvert && (
        <div className="users-modal-overlay" onClick={fermerModal}>
          <div className="users-modal" onClick={(e) => e.stopPropagation()}>
            <div className="users-modal-header">
              <h2>{modeEdition ? 'Modifier un utilisateur' : 'Ajouter un utilisateur'}</h2>
              <button type="button" className="users-icon-btn" onClick={fermerModal}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="users-form">
              <div className="users-form-row">
                <label>
                  Matricule
                  <input
                    type="text"
                    required
                    value={form.matricule}
                    onChange={(e) => handleChange('matricule', e.target.value)}
                  />
                </label>
                <label>
                  Rôle
                  <select value={form.role} onChange={(e) => handleChange('role', e.target.value)}>
                    <option value="STUDENT">Étudiant</option>
                    <option value="TEACHER">Enseignant</option>
                    <option value="ADMIN">Administrateur</option>
                    <option value="SUPER_ADMIN">Super Administrateur</option>
                  </select>
                </label>
              </div>

              <div className="users-form-row">
                <label>
                  Prénom
                  <input
                    type="text"
                    required
                    value={form.prenom}
                    onChange={(e) => handleChange('prenom', e.target.value)}
                  />
                </label>
                <label>
                  Nom
                  <input
                    type="text"
                    required
                    value={form.nom}
                    onChange={(e) => handleChange('nom', e.target.value)}
                  />
                </label>
              </div>

              <label>
                Adresse email
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                />
              </label>

              <label>
                {modeEdition ? 'Nouveau mot de passe (laisser vide pour ne pas changer)' : 'Mot de passe'}
                <input
                  type="password"
                  required={!modeEdition}
                  value={form.mot_de_passe}
                  onChange={(e) => handleChange('mot_de_passe', e.target.value)}
                />
              </label>

              {modeEdition && (
                <label className="users-checkbox">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => handleChange('is_active', e.target.checked)}
                  />
                  Compte actif
                </label>
              )}

              {formErreur && <div className="state-msg error users-form-error">{formErreur}</div>}

              <div className="users-form-actions">
                <button type="button" className="btn" onClick={fermerModal}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary" disabled={envoiEnCours}>
                  {envoiEnCours ? 'Enregistrement…' : modeEdition ? 'Enregistrer' : 'Créer le compte'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}