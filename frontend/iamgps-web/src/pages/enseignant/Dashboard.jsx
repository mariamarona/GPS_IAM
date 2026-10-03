import { useCallback, useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  Calendar, PlayCircle, Users, TrendingUp, UserX, BookOpen, Clock, MapPin,
} from 'lucide-react'
import api from '../../api'
import auth from '../../auth'
import StatCard from '../../components/StatCard'
import './Dashboard.css'

const STATUT_LABEL = { PLANIFIE: 'Planifiée', EN_COURS: 'En cours', TERMINE: 'Terminée', ANNULEE: 'Annulée' }

export default function EnseignantDashboard() {
  const utilisateur = auth.getUtilisateur()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ongletModule, setOngletModule] = useState(0)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(() => {
    if (!utilisateur?.id) return
    setLoading(true)
    api
      .getDashboardEnseignant(utilisateur.id)
      .then((res) => {
        setData(res)
        setOngletModule((i) => (i < res.modules.length ? i : 0))
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [utilisateur?.id])

  useEffect(() => {
    load()
  }, [load])

  async function handleDemarrerSession(sessionId) {
    setBusyId(sessionId)
    try {
      await api.demarrerSession(sessionId)
      load()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function handleTerminerSession(sessionId) {
    setBusyId(sessionId)
    try {
      await api.terminerSession(sessionId)
      load()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function handleDemarrerModule(moduleId) {
    setBusyId(`module-${moduleId}`)
    try {
      await api.demarrerModule(moduleId)
      load()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Bonjour, Prof. {utilisateur ? `${utilisateur.prenom} ${utilisateur.nom}` : ''} 👋</h1>
        <p>Gérez vos sessions et suivez la présence de vos étudiants</p>
      </div>

      {loading && <div className="state-msg">Chargement…</div>}
      {error && !loading && <div className="state-msg error">{error}</div>}

      {data && !loading && !error && (
        <>
          <div className="stat-grid ens-stat-grid">
            <StatCard label="Sessions aujourd'hui" value={data.stats.sessions_aujourdhui} icon={Calendar} tone="blue" />
            <StatCard label="Session active" value={data.stats.session_active} icon={PlayCircle} tone="green" valueColor="var(--green)" />
            <StatCard label="Présents maintenant" value={data.stats.presents_maintenant} icon={Users} tone="blue" />
            <StatCard label="Taux moyen global" value={`${data.stats.taux_moyen_global}%`} icon={TrendingUp} tone="purple" />
          </div>

          <div className="ens-two-col">
            <SessionsDuJourCard
              sessions={data.sessions_du_jour}
              busyId={busyId}
              onDemarrer={handleDemarrerSession}
              onTerminer={handleTerminerSession}
            />
            <AbsentsCard modules={data.modules} ongletModule={ongletModule} />
          </div>

          {data.modules.length > 0 && (
            <>
              <ModuleTabs
                modules={data.modules}
                ongletModule={ongletModule}
                setOngletModule={setOngletModule}
                sessionsDuJour={data.sessions_du_jour}
                busyId={busyId}
                onDemarrerModule={handleDemarrerModule}
              />
              <ChartsRow modules={data.modules} ongletModule={ongletModule} />
              <EtudiantsInscritsCard modules={data.modules} ongletModule={ongletModule} />
            </>
          )}

          {data.modules.length === 0 && (
            <div className="card state-msg">Vous n'avez pas encore de module assigné.</div>
          )}
        </>
      )}
    </>
  )
}

function SessionsDuJourCard({ sessions, busyId, onDemarrer, onTerminer }) {
  return (
    <div className="card ens-card">
      <h2><Calendar size={17} /> Sessions du jour</h2>
      {sessions.length === 0 ? (
        <div className="state-msg">Aucune session programmée aujourd'hui.</div>
      ) : (
        <div className="ens-session-list">
          {sessions.map((s) => (
            <div key={s.id} className={`ens-session-item${s.statut === 'EN_COURS' ? ' active' : ''}`}>
              <div className="ens-session-top">
                <div className="ens-session-title">
                  <span className="cell-strong">{s.intitule}</span>
                  <span className="badge cours-code-badge">{s.code}</span>
                  <span className={`badge statut-${s.statut.toLowerCase()}`}>{STATUT_LABEL[s.statut] || s.statut}</span>
                </div>
                <span className="ens-session-count">{s.nb_presents}/{s.nb_inscrits}</span>
              </div>
              <div className="cell-sub ens-session-meta">
                <Clock size={12} /> {s.heure_debut.slice(0, 5)} - {s.heure_fin.slice(0, 5)}
                <MapPin size={12} style={{ marginLeft: 10 }} /> {s.zone}
              </div>
              {s.statut === 'EN_COURS' && (
                <button className="btn btn-danger ens-session-btn" disabled={busyId === s.id} onClick={() => onTerminer(s.id)}>
                  Terminer
                </button>
              )}
              {s.statut === 'PLANIFIE' && (
                <button className="btn btn-primary ens-session-btn" disabled={busyId === s.id} onClick={() => onDemarrer(s.id)}>
                  Démarrer
                </button>
              )}
              {(s.statut === 'TERMINE' || s.statut === 'ANNULEE') && (
                <button className="btn btn-primary ens-session-btn" disabled={busyId === s.id} onClick={() => onDemarrer(s.id)}>
                  Réactiver
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AbsentsCard({ modules, ongletModule }) {
  const module = modules[ongletModule]
  const absents = module?.absents_aujourdhui || []
  return (
    <div className="card ens-card">
      <h2>
        <UserX size={17} color="var(--red)" /> Absents
        {module && <span className="badge" style={{ background: 'var(--border)', color: 'var(--text-secondary)', marginLeft: 8 }}>{module.code}</span>}
        <span className="badge" style={{ background: 'var(--red-light)', color: 'var(--red)', marginLeft: 'auto' }}>
          {absents.length} absent(s)
        </span>
      </h2>
      {absents.length === 0 ? (
        <div className="state-msg">Aucun absent recensé pour la séance du jour de ce module.</div>
      ) : (
        <div className="ens-absents-list">
          {absents.map((a) => (
            <div key={a.id} className="ens-absent-item">
              <span className="ens-absent-avatar">{a.nom_complet.charAt(0)}</span>
              <div className="ens-absent-info">
                <div className="cell-strong">{a.nom_complet}</div>
                <div className="cell-sub">{a.matricule} · {a.email}</div>
              </div>
              <span className="badge" style={{ background: 'var(--red-light)', color: 'var(--red)' }}>{a.total_absences} abs.</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ModuleTabs({ modules, ongletModule, setOngletModule, sessionsDuJour, busyId, onDemarrerModule }) {
  const module = modules[ongletModule]
  const aUneSessionAujourdhui = sessionsDuJour.some((s) => s.module_id === module.id)

  return (
    <div className="ens-tabs-row">
      <div className="ens-tabs">
        {modules.map((m, i) => (
          <button
            key={m.id}
            className={`ens-tab${i === ongletModule ? ' active' : ''}`}
            onClick={() => setOngletModule(i)}
          >
            {m.code}
          </button>
        ))}
      </div>
      {!aUneSessionAujourdhui && (
        <button
          className="btn btn-primary"
          disabled={busyId === `module-${module.id}`}
          onClick={() => onDemarrerModule(module.id)}
        >
          Démarrer une séance maintenant
        </button>
      )}
    </div>
  )
}

const DONUT_COLORS = { present: 'var(--green)', retard: 'var(--orange)', absent: 'var(--red)' }

function ChartsRow({ modules, ongletModule }) {
  const module = modules[ongletModule]
  const tauxData = modules.map((m) => ({ code: m.code, taux: m.taux_moyen }))
  const evolutionData = (module?.evolution || []).map((e) => ({ semaine: e.semaine.split('-S')[1] ? `S${e.semaine.split('-S')[1]}` : e.semaine, taux: e.taux }))
  const distribution = module?.distribution || { present: 0, retard: 0, absent: 0 }
  const donutData = [
    { name: 'Présent', value: distribution.present, color: DONUT_COLORS.present },
    { name: 'Retard', value: distribution.retard, color: DONUT_COLORS.retard },
    { name: 'Absent', value: distribution.absent, color: DONUT_COLORS.absent },
  ].filter((d) => d.value > 0)

  return (
    <div className="ens-charts-row">
      <div className="card ens-chart-card">
        <h3>Taux par module</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={tauxData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
            <XAxis dataKey="code" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="taux" fill="var(--blue)" radius={[4, 4, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card ens-chart-card">
        <h3>Évolution — {module?.code}</h3>
        {evolutionData.length < 2 ? (
          <div className="state-msg" style={{ height: 180 }}>Pas encore assez de données.</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={evolutionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" vertical={false} />
              <XAxis dataKey="semaine" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="taux" stroke="var(--green)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card ens-chart-card">
        <h3>Distribution globale</h3>
        {donutData.length === 0 ? (
          <div className="state-msg" style={{ height: 180 }}>Pas encore de données.</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={donutData} dataKey="value" innerRadius={40} outerRadius={65} paddingAngle={2}>
                {donutData.map((d) => <Cell key={d.name} fill={d.color} />)}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

function EtudiantsInscritsCard({ modules, ongletModule }) {
  const module = modules[ongletModule]
  const etudiants = module?.etudiants || []

  return (
    <div className="card ens-card">
      <h2>
        <BookOpen size={17} /> Étudiants inscrits — {module?.intitule}
        <span className="badge" style={{ background: 'var(--blue-light)', color: 'var(--blue)', marginLeft: 'auto' }}>
          Seuil: {module?.seuil_presence_pct}%
        </span>
      </h2>
      {etudiants.length === 0 ? (
        <div className="state-msg">Aucun étudiant inscrit.</div>
      ) : (
        <table className="ens-etudiants-table">
          <thead>
            <tr><th>Matricule</th><th>Nom</th><th>Email</th><th>Présences</th><th>Taux</th><th>Statut</th></tr>
          </thead>
          <tbody>
            {etudiants.map((e) => {
              const ok = e.statut === 'OK'
              return (
                <tr key={e.id}>
                  <td className="cell-sub">{e.matricule}</td>
                  <td className="cell-strong">{e.prenom} {e.nom}</td>
                  <td className="cell-sub">{e.email}</td>
                  <td>{e.presences}/{e.total_sessions}</td>
                  <td style={{ color: ok ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>{e.taux_presence}%</td>
                  <td>
                    <span className="badge" style={{ background: ok ? 'var(--green-light)' : 'var(--red-light)', color: ok ? 'var(--green)' : 'var(--red)' }}>
                      {ok ? 'OK' : 'Sous seuil'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}