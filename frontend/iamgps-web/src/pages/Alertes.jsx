import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Brain, Activity, MapPin, Target, Clock, User, Zap, AlertCircle,
  Shield, Eye, CheckCircle, XCircle, TrendingUp,
} from 'lucide-react'
import api from '../api'
import StatCard from '../components/StatCard'
import { TYPE_LABEL, STATUT_BADGE, NIVEAU_BADGE, scoreColor, IA_MODEL_INFO } from '../fraudeMeta'
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

// Couleur de l'icône/badge alignée sur la sévérité (comme dans la maquette de référence).
const SEVERITE_TONE = {
  CRITIQUE: 'red',
  ELEVE: 'orange',
  MOYEN: 'yellow',
  FAIBLE: 'blue',
}

export default function Alertes() {
  const [stats, setStats] = useState(null)
  const [alertes, setAlertes] = useState([])
  const [tab, setTab] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [showModelInfo, setShowModelInfo] = useState(false)

  const loadAll = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([api.getAlertesDashboard(), api.getAlertes(tab ? { statut: tab } : {})])
      .then(([statsRes, listRes]) => {
        setStats(statsRes)
        const list = Array.isArray(listRes) ? listRes : listRes.results || []
        setAlertes(list.map(toRow).sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1)))
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [tab])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const selected = useMemo(() => alertes.find((a) => a.id === selectedId) || null, [alertes, selectedId])

  async function handleTraiter(id, statut) {
    setBusyId(id)
    try {
      await api.traiterAlerte(id, { statut })
      loadAll()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="page-header fraude-header">
        <div>
          <h1>
            <Brain className="fraude-header-icon" size={24} />
            Détection de Fraude IA
          </h1>
          <p>Modèle {IA_MODEL_INFO.name} v{IA_MODEL_INFO.version} — détection à 3 niveaux (heuristique / IsolationForest / RandomForest)</p>
        </div>
        <button type="button" className="btn" onClick={() => setShowModelInfo((v) => !v)}>
          <Activity size={15} />
          {showModelInfo ? 'Masquer le modèle' : 'Voir le modèle IA'}
        </button>
      </div>

      {showModelInfo && <ModelInfoPanel />}

      {stats && (
        <div className="stat-grid alertes-stat-grid">
          <StatCard label="Non traitées" value={stats.non_traitees} icon={AlertCircle} tone="red" />
          <StatCard label="En investigation" value={stats.en_investigation} icon={Eye} tone="orange" />
          <StatCard label="Confirmées" value={stats.confirmees} icon={Shield} tone="red" />
          <StatCard label="Fausses alertes" value={stats.fausses_alertes} icon={CheckCircle} tone="green" />
        </div>
      )}

      <div className="fraude-tabs">
        {TABS.map((t) => (
          <button
            key={t.key || 'toutes'}
            type="button"
            className={`fraude-tab${tab === t.key ? ' active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="fraude-layout">
        <div className="fraude-list">
          {loading && <div className="state-msg">Chargement…</div>}
          {error && !loading && <div className="state-msg error">{error}</div>}
          {!loading && !error && alertes.length === 0 && (
            <div className="card state-msg">Aucune alerte pour ce filtre.</div>
          )}

          {!loading &&
            !error &&
            alertes.map((a) => {
              const statutInfo = STATUT_BADGE[a.statut] || { label: a.statut, bg: '#f1f2f5', color: '#374151' }
              const niveauInfo = NIVEAU_BADGE[a.niveau_severite] || { color: '#374151', bg: '#f1f2f5' }
              const Icon = TYPE_ICON[a.type_fraude] || AlertCircle
              const tone = SEVERITE_TONE[a.niveau_severite] || 'blue'
              const score = a.score_ia != null ? Math.round(a.score_ia) : null

              return (
                <div
                  key={a.id}
                  className={`card alert-card${selectedId === a.id ? ' selected' : ''}`}
                  onClick={() => setSelectedId(a.id)}
                >
                  <div className="alert-card-top">
                    <span className={`alert-card-icon tone-${tone}`}>
                      <Icon size={18} />
                    </span>
                    <div className="alert-card-title">
                      <span className="cell-strong">{a.etudiant_nom}</span>
                      <span className="badge" style={{ background: statutInfo.bg, color: statutInfo.color }}>
                        {statutInfo.label}
                      </span>
                    </div>
                    <div className="alert-card-score">
                      {score != null && (
                        <>
                          <Brain size={13} />
                          <span>{score}%</span>
                        </>
                      )}
                      <span className="badge" style={{ background: niveauInfo.bg, color: niveauInfo.color }}>
                        {a.niveau_severite || '—'}
                      </span>
                    </div>
                  </div>

                  <div className="cell-sub alert-card-meta">
                    {(TYPE_LABEL[a.type_fraude] || a.type_fraude)} · {a.date}{a.heure ? ` à ${a.heure}` : ''}
                  </div>

                  {a.commentaire && <p className="alert-card-desc">{a.commentaire}</p>}

                  {score != null && (
                    <div className="alert-card-bar-wrap">
                      <div className="alert-card-bar-header">
                        <span>Score IA</span>
                        <span>{score}%</span>
                      </div>
                      <div className="alert-card-bar-track">
                        <div
                          className="alert-card-bar-fill"
                          style={{ width: `${score}%`, background: scoreColor(score) }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
        </div>

        <div className="fraude-side">
          {selected ? (
            <>
              <AnalyseIACard alerte={selected} />
              <ActionsCard alerte={selected} busy={busyId === selected.id} onTraiter={handleTraiter} />
            </>
          ) : (
            <div className="card fraude-side-card">
              <div className="fraude-side-empty">
                <AlertCircle size={30} />
                <p>Sélectionnez une alerte pour voir l'analyse IA détaillée</p>
              </div>
            </div>
          )}

          {stats && Object.keys(stats.par_type || {}).length > 0 && (
            <div className="card fraude-side-card">
              <h2>Alertes par type</h2>
              <div className="par-type-list">
                {Object.entries(stats.par_type).map(([type, count]) => {
                  const max = Math.max(...Object.values(stats.par_type))
                  return (
                    <div key={type} className="par-type-row">
                      <span className="par-type-label">{TYPE_LABEL[type] || type}</span>
                      <div className="par-type-track">
                        <div className="par-type-fill" style={{ width: `${(count / max) * 100}%` }} />
                      </div>
                      <span className="par-type-count">{count}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function ModelInfoPanel() {
  return (
    <div className="card model-info-card">
      <h2>
        <Brain size={16} />
        Modèle {IA_MODEL_INFO.name} v{IA_MODEL_INFO.version}
      </h2>
      <div className="model-info-levels">
        {IA_MODEL_INFO.levels.map((lvl) => (
          <div key={lvl.key} className="model-info-level">
            <span className="cell-sub">{lvl.label}</span>
            <span className="model-info-level-detail">{lvl.detail}</span>
          </div>
        ))}
      </div>

      <div className="model-info-columns">
        <div>
          <p className="model-info-subhead">Features d'entrée ({IA_MODEL_INFO.features.length})</p>
          <div className="model-info-features">
            {IA_MODEL_INFO.features.map((f) => (
              <div key={f} className="model-info-feature">
                <span className="model-info-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="model-info-subhead">Seuils de sévérité</p>
          <div className="model-info-thresholds">
            <div className="model-info-threshold tone-blue"><span>FAIBLE</span><span>Score 0 - 40</span></div>
            <div className="model-info-threshold tone-yellow"><span>MOYEN</span><span>Score 40 - 70</span></div>
            <div className="model-info-threshold tone-orange"><span>ÉLEVÉ</span><span>Score 70 - 90</span></div>
            <div className="model-info-threshold tone-red"><span>CRITIQUE</span><span>Score 90 - 100</span></div>
          </div>
        </div>
      </div>

      <p className="model-info-disclaimer">
        Le niveau de détection réellement actif (indiqué "Modèle :" sur chaque alerte ci-dessous)
        dépend du nombre d'alertes déjà confirmées ou rejetées par un administrateur — pas de
        métriques de précision/rappel ici, faute d'un jeu de test étiqueté suffisant pour les
        évaluer honnêtement.
      </p>
    </div>
  )
}

function AnalyseIACard({ alerte }) {
  const analyse = alerte.analyse_ia
  return (
    <div className="card fraude-side-card">
      <h2>
        <Brain size={16} className="tone-purple-icon" />
        Analyse IA détaillée
      </h2>

      {!analyse ? (
        <p className="state-msg" style={{ padding: '16px 0' }}>Analyse IA non disponible pour cette alerte.</p>
      ) : (
        <>
          <div className="risk-score-box">
            <div className="risk-score-row">
              <span className="cell-strong">Score de risque global</span>
              <span className="risk-score-value">{Math.round(analyse.risk_score * 100)}%</span>
            </div>
            <div className="risk-score-track">
              <div
                className="risk-score-fill"
                style={{
                  width: `${analyse.risk_score * 100}%`,
                  background: scoreColor(analyse.risk_score * 100),
                }}
              />
            </div>
          </div>

          <p className="model-info-subhead" style={{ marginTop: 16 }}>Facteurs d'analyse</p>
          <div className="factors-list">
            {analyse.factors.map((f) => (
              <div key={f.name} className="factor-item">
                <div className="factor-top">
                  <span className="factor-name">{f.name}</span>
                  <div className="factor-values">
                    <span className="cell-sub">Poids : {Math.round(f.weight * 100)}%</span>
                    <span
                      className="factor-value"
                      style={{ color: f.value >= 0.7 ? 'var(--red)' : f.value >= 0.4 ? '#b45309' : 'var(--green)' }}
                    >
                      {Math.round(f.value * 100)}%
                    </span>
                  </div>
                </div>
                <div className="factor-track">
                  <div
                    className="factor-fill"
                    style={{
                      width: `${f.value * 100}%`,
                      background: f.value >= 0.7 ? 'var(--red)' : f.value >= 0.4 ? '#eab308' : 'var(--green)',
                    }}
                  />
                </div>
                <p className="factor-desc">{f.description}</p>
              </div>
            ))}
          </div>

          <div className="recommendation-box">
            <TrendingUp size={16} />
            <div>
              <p className="recommendation-title">Recommandation IA</p>
              <p className="recommendation-text">{analyse.recommendation}</p>
            </div>
          </div>

          <p className="model-info-disclaimer" style={{ textAlign: 'right', marginTop: 10 }}>
            Modèle : {analyse.model_version}
          </p>
        </>
      )}
    </div>
  )
}

function ActionsCard({ alerte, busy, onTraiter }) {
  const traitee = alerte.statut === 'FRAUDE_CONFIRMEE' || alerte.statut === 'FAUSSE_ALERTE'
  return (
    <div className="card fraude-side-card">
      <h2>Actions</h2>
      {traitee ? (
        <div className="fraude-side-empty" style={{ padding: '12px 0' }}>
          <CheckCircle size={26} />
          <p>Alerte déjà traitée</p>
        </div>
      ) : (
        <div className="actions-list">
          {alerte.statut === 'NON_TRAITEE' && (
            <button className="btn" disabled={busy} onClick={() => onTraiter(alerte.id, 'EN_INVESTIGATION')}>
              <Eye size={15} /> Mettre en investigation
            </button>
          )}
          <button
            className="btn btn-danger"
            disabled={busy}
            onClick={() => onTraiter(alerte.id, 'FRAUDE_CONFIRMEE')}
          >
            <XCircle size={15} /> Confirmer la fraude
          </button>
          <button className="btn" disabled={busy} onClick={() => onTraiter(alerte.id, 'FAUSSE_ALERTE')}>
            <CheckCircle size={15} className="tone-green-icon" /> Classer fausse alerte
          </button>
        </div>
      )}
    </div>
  )
}

function toRow(a) {
  const ts = a.timestamp ? new Date(a.timestamp) : null
  return {
    id: a.id,
    type_fraude: a.type_fraude,
    niveau_severite: a.niveau_severite,
    score_ia: a.score_ia,
    statut: a.statut,
    timestamp: a.timestamp,
    commentaire: a.commentaire,
    analyse_ia: a.analyse_ia,
    etudiant_nom: a.etudiant_nom,
    etudiant_matricule: a.etudiant_matricule,
    module: a.module_code,
    date: a.date_session,
    heure: ts ? ts.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : null,
  }
}