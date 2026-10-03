import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  TriangleAlert, Eye, ShieldCheck, ShieldX, MapPin, Target, Clock, User, Zap, AlertCircle,
} from 'lucide-react'
import api from '../../api'
import auth from '../../auth'
import StatCard from '../../components/StatCard'
import { TYPE_LABEL, NIVEAU_BADGE, scoreColor } from '../../fraudeMeta'
import './Alertes.css'

const TABS = [
  { key: '', label: 'Toutes' },
  { key: 'NON_TRAITEE', label: 'Non traitées' },
  { key: 'EN_INVESTIGATION', label: 'Investigation' },
  { key: 'FRAUDE_CONFIRMEE', label: 'Confirmées' },
  { key: 'FAUSSE_ALERTE', label: 'Fausses alertes' },
]

const TYPE_ICON = {
  hors_zone: MapPin,
  coords_fixes: Target,
  heure_invalide: Clock,
  doublon: User,
  spoofing_gps: Zap,
  autre: AlertCircle,
}

const STATUT_LABEL = {
  NON_TRAITEE: 'Non traitée',
  EN_INVESTIGATION: 'Investigation',
  FRAUDE_CONFIRMEE: 'Fraude confirmée',
  FAUSSE_ALERTE: 'Fausse alerte',
}

export default function EnseignantAlertes() {
  const utilisateur = auth.getUtilisateur()
  const [alertes, setAlertes] = useState([])
  const [tab, setTab] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(() => {
    if (!utilisateur?.id) return
    setLoading(true)
    setError(null)
    api
      .getAlertes({ enseignant_id: utilisateur.id, ...(tab ? { statut: tab } : {}) })
      .then((res) => setAlertes(Array.isArray(res) ? res : res.results || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [utilisateur?.id, tab])

  useEffect(() => {
    load()
  }, [load])

  const stats = useMemo(() => {
    const parStatut = (s) => alertes.filter((a) => a.statut === s).length
    return {
      non_traitees: parStatut('NON_TRAITEE'),
      investigation: parStatut('EN_INVESTIGATION'),
      confirmees: parStatut('FRAUDE_CONFIRMEE'),
      fausses: parStatut('FAUSSE_ALERTE'),
    }
  }, [alertes])

  function traiter(alerte, statut) {
    setBusyId(alerte.id)
    api
      .traiterAlerte(alerte.id, { statut, traite_par: utilisateur.id })
      .then(load)
      .catch((err) => alert(err.message))
      .finally(() => setBusyId(null))
  }

  function corrigerPresence(alerte) {
    if (
      !window.confirm(
        `Marquer la présence de ${alerte.etudiant_nom} comme VALIDE pour ${alerte.module_code} du ${alerte.date_session} ?\n\n` +
          `Pensez à traiter l'alerte séparément (ex : "Fausse alerte") si cette correction la clôt.`
      )
    ) {
      return
    }
    setBusyId(alerte.id)
    api
      .corrigerPointage(alerte.pointage, 'VALIDE')
      .then(load)
      .catch((err) => alert(err.message))
      .finally(() => setBusyId(null))
  }

  return (
    <>
      <div className="page-header">
        <h1>Alertes de fraude</h1>
        <p>Alertes détectées sur vos modules uniquement</p>
      </div>

      <div className="stat-grid">
        <StatCard label="Non traitées" value={stats.non_traitees} icon={TriangleAlert} tone="orange" />
        <StatCard label="En investigation" value={stats.investigation} icon={Eye} tone="blue" />
        <StatCard label="Confirmées" value={stats.confirmees} icon={ShieldX} tone="orange" valueColor="var(--red)" />
        <StatCard label="Fausses alertes" value={stats.fausses} icon={ShieldCheck} tone="green" />
      </div>

      {error && <div className="state-msg error">Impossible de charger les alertes ({error}).</div>}

      <div className="card ens-alertes-card">
        <div className="ens-alertes-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              className={`ens-alertes-tab${tab === t.key ? ' active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="state-msg">Chargement…</div>
        ) : alertes.length === 0 ? (
          <div className="state-msg">Aucune alerte sur vos modules pour ce filtre.</div>
        ) : (
          <div className="ens-alertes-list">
            {alertes.map((a) => {
              const Icon = TYPE_ICON[a.type_fraude] || AlertCircle
              const niveau = NIVEAU_BADGE[a.niveau_severite] || NIVEAU_BADGE.FAIBLE
              const traitee = a.statut === 'FRAUDE_CONFIRMEE' || a.statut === 'FAUSSE_ALERTE'
              return (
                <div key={a.id} className="ens-alerte-row">
                  <div className="ens-alerte-icon" style={{ background: niveau.bg, color: niveau.color }}>
                    <Icon size={18} />
                  </div>

                  <div className="ens-alerte-main">
                    <div className="ens-alerte-top">
                      <span className="ens-alerte-etudiant">{a.etudiant_nom}</span>
                      <span className="ens-alerte-matricule">{a.etudiant_matricule}</span>
                      <span className="ens-alerte-statut" style={{ background: niveau.bg, color: niveau.color }}>
                        {STATUT_LABEL[a.statut]}
                      </span>
                    </div>
                    <div className="ens-alerte-desc">
                      {TYPE_LABEL[a.type_fraude] || a.type_fraude} · {a.module_code} · {a.date_session}
                    </div>
                    {a.analyse_ia?.recommendation && (
                      <div className="ens-alerte-reco">{a.analyse_ia.recommendation}</div>
                    )}
                    {a.commentaire && !a.analyse_ia?.recommendation && (
                      <div className="ens-alerte-reco">{a.commentaire}</div>
                    )}
                    {a.score_ia != null && (
                      <div className="ens-alerte-score">
                        <div className="ens-alerte-score-bar">
                          <div
                            className="ens-alerte-score-fill"
                            style={{ width: `${a.score_ia}%`, background: scoreColor(a.score_ia) }}
                          />
                        </div>
                        <span>{a.score_ia}%</span>
                      </div>
                    )}
                  </div>

                  <div className="ens-alerte-actions">
                    {!traitee && a.statut === 'NON_TRAITEE' && (
                      <button
                        type="button"
                        className="btn"
                        disabled={busyId === a.id}
                        onClick={() => traiter(a, 'EN_INVESTIGATION')}
                      >
                        Investiguer
                      </button>
                    )}
                    {!traitee && (
                      <>
                        <button
                          type="button"
                          className="btn"
                          disabled={busyId === a.id}
                          onClick={() => traiter(a, 'FAUSSE_ALERTE')}
                        >
                          Fausse alerte
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          disabled={busyId === a.id}
                          onClick={() => traiter(a, 'FRAUDE_CONFIRMEE')}
                        >
                          Confirmer
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary"
                          disabled={busyId === a.id}
                          onClick={() => corrigerPresence(a)}
                        >
                          Corriger la présence
                        </button>
                      </>
                    )}
                    {traitee && <span className="ens-alerte-traitee">Traitée</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}