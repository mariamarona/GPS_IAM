import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Users, TrendingUp, TriangleAlert, BookOpen, CircleCheck, CircleX, Clock, BellRing, Download } from 'lucide-react'
import api from '../api'
import StatCard from '../components/StatCard'
import { TYPE_LABEL, NIVEAU_BADGE } from '../fraudeMeta'
import './Dashboard.css'

function initiales(nomComplet) {
  return nomComplet
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

function tauxColor(taux) {
  if (taux >= 85) return 'var(--green)'
  if (taux >= 70) return 'var(--orange)'
  return 'var(--red)'
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [telechargement, setTelechargement] = useState(false)
  const [erreurRapport, setErreurRapport] = useState(null)

  function telechargerRapport() {
    setTelechargement(true)
    setErreurRapport(null)
    api
      .telechargerRapport()
      .catch((err) => setErreurRapport(err.message))
      .finally(() => setTelechargement(false))
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .getDashboardAdmin()
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
  }, [])

  return (
    <>
      <div className="page-header page-header-row">
        <div>
          <h1>Tableau de bord administrateur</h1>
          <p>Vue d'ensemble du système de présence</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={telechargerRapport}
          disabled={telechargement}
        >
          <Download size={16} />
          {telechargement ? 'Génération…' : 'Télécharger le rapport'}
        </button>
      </div>
      {erreurRapport && (
        <div className="state-msg error" style={{ marginTop: -16, marginBottom: 16 }}>
          {erreurRapport}
        </div>
      )}

      {loading && <div className="state-msg">Chargement des données…</div>}
      {error && !loading && (
        <div className="state-msg error">
          Impossible de charger le tableau de bord ({error}). Vérifiez que l'API Django tourne bien
          sur {import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}.
        </div>
      )}

      {data && !loading && !error && (
        <>
          <div className="stat-grid">
            <StatCard label="Étudiants inscrits" value={data.etudiants_inscrits} icon={Users} tone="blue" />
            <StatCard
              label="Taux moyen présence"
              value={`${data.taux_moyen_presence}%`}
              icon={TrendingUp}
              tone="green"
              valueColor="var(--green)"
            />
            <StatCard label="Fraudes détectées" value={data.fraudes_detectees} icon={TriangleAlert} tone="orange" />
            <StatCard label="Cours actifs" value={data.cours_actifs} icon={BookOpen} tone="purple" />
          </div>

          <div className="dashboard-lower">
            <div className="card weekly-chart-card">
              <h2>Présence hebdomadaire</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.presence_hebdomadaire} barGap={6}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
                  <XAxis dataKey="jour" tick={{ fontSize: 13, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#9aa2b1' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 10, border: '1px solid #e7e9ee', fontSize: 13 }}
                    cursor={{ fill: 'rgba(71,85,105,0.06)' }}
                  />
                  <Legend
                    iconType="circle"
                    formatter={(value) => <span style={{ color: '#374151', fontSize: 13 }}>{value}</span>}
                  />
                  <Bar dataKey="presents" name="Présents" fill="#475569" radius={[4, 4, 0, 0]} maxBarSize={34} />
                  <Bar dataKey="absents" name="Absents" fill="#dc2626" radius={[4, 4, 0, 0]} maxBarSize={34} />
                  <Bar dataKey="en_retard" name="En retard" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={34} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card today-card">
              <h2>Aujourd'hui</h2>
              <div className="today-row today-green">
                <div className="today-row-label">
                  <CircleCheck size={18} />
                  <span>Présents</span>
                </div>
                <span className="today-row-value">{data.aujourd_hui.presents}</span>
              </div>
              <div className="today-row today-red">
                <div className="today-row-label">
                  <CircleX size={18} />
                  <span>Absents</span>
                </div>
                <span className="today-row-value">{data.aujourd_hui.absents}</span>
              </div>
              <div className="today-row today-orange">
                <div className="today-row-label">
                  <Clock size={18} />
                  <span>En retard</span>
                </div>
                <span className="today-row-value">{data.aujourd_hui.en_retard}</span>
              </div>
              <div className="today-row today-orange-strong">
                <div className="today-row-label">
                  <BellRing size={18} />
                  <span>Alertes en attente</span>
                </div>
                <span className="today-row-value">{data.aujourd_hui.alertes_en_attente}</span>
              </div>
            </div>
          </div>

          <div className="card evolution-chart-card">
            <h2>Évolution du taux de présence (8 dernières semaines)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.evolution_taux_presence} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
                <XAxis dataKey="semaine" tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                  tick={{ fontSize: 12, fill: '#9aa2b1' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value) => [`${value}%`, 'Taux de présence']}
                  labelFormatter={(label) => `Semaine du ${label}`}
                  contentStyle={{ borderRadius: 10, border: '1px solid #e7e9ee', fontSize: 13 }}
                />
                <Line
                  type="monotone"
                  dataKey="taux_presence"
                  name="Taux de présence"
                  stroke="#475569"
                  strokeWidth={2.5}
                  dot={{ r: 3.5, fill: '#475569' }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="dashboard-bottom">
            <div className="card recent-alerts-card">
              <div className="recent-alerts-header">
                <h2>Dernières alertes de fraude</h2>
                {data.aujourd_hui.alertes_en_attente > 0 && (
                  <span className="pending-pill">{data.aujourd_hui.alertes_en_attente} en attente</span>
                )}
              </div>

              {data.dernieres_alertes.length === 0 ? (
                <div className="state-msg">Aucune alerte enregistrée.</div>
              ) : (
                <div className="recent-alerts-list">
                  {data.dernieres_alertes.map((a) => {
                    const niveauInfo = NIVEAU_BADGE[a.niveau_severite] || { color: '#374151', bg: '#f1f2f5' }
                    return (
                      <div key={a.id} className="recent-alert-item">
                        <div className="recent-alert-top">
                          <span className="cell-strong">{a.etudiant_nom}</span>
                          <span className="badge" style={{ background: niveauInfo.bg, color: niveauInfo.color }}>
                            {a.niveau_severite || '—'}
                          </span>
                        </div>
                        <div className="cell-sub">
                          {(TYPE_LABEL[a.type_fraude] || a.type_fraude)} · {a.date}
                        </div>
                        {a.score_ia != null && <div className="recent-alert-score">Score IA : {a.score_ia}%</div>}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="card students-presence-card">
              <h2>Étudiants - Taux de présence</h2>
              {data.etudiants_presence.length === 0 ? (
                <div className="state-msg">Aucun étudiant actif.</div>
              ) : (
                <div className="students-presence-list">
                  {data.etudiants_presence.slice(0, 8).map((e) => (
                    <div key={e.id} className="student-presence-row">
                      <span className="student-avatar">{initiales(e.nom_complet)}</span>
                      <div className="student-presence-info">
                        <div className="cell-strong">{e.nom_complet}</div>
                        <div className="cell-sub">{e.matricule}</div>
                      </div>
                      <div className="student-presence-bar-wrap">
                        <div className="student-presence-bar-track">
                          <div
                            className="student-presence-bar-fill"
                            style={{ width: `${Math.min(100, e.taux_presence)}%`, background: tauxColor(e.taux_presence) }}
                          />
                        </div>
                        <span className="student-presence-pct" style={{ color: tauxColor(e.taux_presence) }}>
                          {e.taux_presence}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  )
}