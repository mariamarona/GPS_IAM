import { useEffect, useState } from 'react'
import { BookOpen, Navigation, Users, User, MapPin, Clock, BrainCircuit, SlidersHorizontal, UserPlus, X } from 'lucide-react'
import api from '../api'
import StatCard from '../components/StatCard'
import './Cours.css'

export default function Cours() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [coursInscription, setCoursInscription] = useState(null)

  function load() {
    let cancelled = false
    setLoading(true)
    api
      .getDashboardCours()
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }

  useEffect(() => load(), [])

  return (
    <>
      <div className="page-header">
        <h1>Gestion des cours</h1>
        <p>Paramétrage des cours, périmètres GPS et groupes d'étudiants</p>
      </div>

      {loading && <div className="state-msg">Chargement…</div>}
      {error && !loading && <div className="state-msg error">{error}</div>}

      {data && !loading && !error && (
        <>
          <div className="stat-grid cours-stat-grid">
            <StatCard label="Cours configurés" value={data.cours_configures} icon={BookOpen} tone="blue" />
            <StatCard label="Zones GPS actives" value={data.zones_gps_actives} icon={Navigation} tone="green" />
          </div>

          <div className="card cours-list-card">
            <h2>Liste des cours</h2>

            {data.cours.length === 0 ? (
              <div className="state-msg">Aucun cours configuré.</div>
            ) : (
              <div className="cours-list">
                {data.cours.map((c) => (
                  <div key={c.id} className="cours-item">
                    <div className="cours-item-main">
                      <div className="cours-item-title">
                        <span className="cell-strong cours-item-name">{c.intitule}</span>
                        <span className="badge cours-code-badge">{c.code}</span>
                      </div>
                      <div className="cours-item-meta">
                        <span>
                          <User size={13} /> Prof. {c.enseignant_nom}
                        </span>
                        {c.zone && (
                          <span>
                            <MapPin size={13} /> {c.zone.nom}
                          </span>
                        )}
                        {c.horaire && (
                          <span>
                            <Clock size={13} /> {c.horaire}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="cours-item-side">
                      {c.zone && (
                        <div className="cours-item-coords">
                          <span className="cell-sub">Zone GPS</span>
                          <span className="cell-strong">
                            {c.zone.latitude}, {c.zone.longitude}
                          </span>
                        </div>
                      )}
                      {c.zone && <span className="badge rayon-badge">Rayon {c.zone.rayon_m}m</span>}
                      <div className="cours-item-etudiants">
                        <Users size={14} />
                        <span>{c.nb_etudiants} étudiants</span>
                      </div>
                      <button
                        className="btn btn-primary cours-inscrire-btn"
                        onClick={() => setCoursInscription(c)}
                      >
                        <UserPlus size={14} /> Inscrire un étudiant
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {coursInscription && (
            <InscrireEtudiantModal
              cours={coursInscription}
              onClose={() => setCoursInscription(null)}
              onInscrit={() => {
                setCoursInscription(null)
                load()
              }}
            />
          )}

          <div className="config-zones-header">
            <Navigation size={17} />
            <h2>Configuration des zones GPS</h2>
          </div>

          <div className="config-zones-grid">
            <div className="card config-zone-card tone-blue">
              <div className="config-zone-icon">
                <MapPin size={18} />
              </div>
              <h3>Périmètre autorisé</h3>
              <p>
                Chaque cours a un rayon GPS défini. L'étudiant doit être dans ce périmètre pour valider sa
                présence.
              </p>
            </div>
            <div className="card config-zone-card tone-orange">
              <div className="config-zone-icon">
                <BrainCircuit size={18} />
              </div>
              <h3>Détection de fraude</h3>
              <p>
                L'IA analyse les patterns GPS, la cohérence réseau et les anomalies d'appareil pour détecter les
                tentatives de fraude.
              </p>
            </div>
            <div className="card config-zone-card tone-green">
              <div className="config-zone-icon">
                <SlidersHorizontal size={18} />
              </div>
              <h3>Seuils configurables</h3>
              <p>
                Les rayons GPS et seuils de détection sont ajustables par cours selon la taille et la disposition
                des salles.
              </p>
            </div>
          </div>
        </>
      )}
    </>
  )
}

function InscrireEtudiantModal({ cours, onClose, onInscrit }) {
  const [etudiants, setEtudiants] = useState([])
  const [dejaInscrits, setDejaInscrits] = useState([])
  const [etudiantId, setEtudiantId] = useState('')
  const [loading, setLoading] = useState(true)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.getUtilisateurs({ role: 'STUDENT' }),
      api.getInscriptions({ module: cours.id }),
    ])
      .then(([tousLesEtudiants, inscriptions]) => {
        if (cancelled) return
        setEtudiants(tousLesEtudiants)
        setDejaInscrits(inscriptions.filter((i) => i.is_active).map((i) => i.etudiant))
      })
      .catch((err) => !cancelled && setErreur(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [cours.id])

  const disponibles = etudiants.filter((e) => !dejaInscrits.includes(e.id))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!etudiantId) return
    setEnvoi(true)
    setErreur(null)
    try {
      await api.createInscription({ etudiant: etudiantId, module: cours.id, is_active: true })
      onInscrit()
    } catch (err) {
      setErreur(err.message)
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <div className="users-modal-overlay" onClick={onClose}>
      <div className="users-modal" onClick={(e) => e.stopPropagation()}>
        <div className="users-modal-header">
          <h2>Inscrire un étudiant — {cours.code}</h2>
          <button type="button" className="users-icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div className="state-msg">Chargement…</div>
        ) : (
          <form onSubmit={handleSubmit} className="users-form">
            {erreur && <div className="state-msg error">{erreur}</div>}

            {disponibles.length === 0 ? (
              <div className="state-msg">
                Tous les étudiants sont déjà inscrits à ce cours (ou aucun étudiant n'existe encore).
              </div>
            ) : (
              <label>
                Étudiant
                <select value={etudiantId} onChange={(e) => setEtudiantId(e.target.value)} required>
                  <option value="">Sélectionner un étudiant…</option>
                  {disponibles.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.matricule} — {e.prenom} {e.nom}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="users-form-actions">
              <button type="button" className="btn" onClick={onClose}>
                Annuler
              </button>
              <button type="submit" className="btn btn-primary" disabled={envoi || disponibles.length === 0}>
                {envoi ? 'Inscription…' : 'Inscrire'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}