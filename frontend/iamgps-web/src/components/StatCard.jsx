import './StatCard.css'

export default function StatCard({ label, value, icon: Icon, tone = 'blue', valueColor }) {
  return (
    <div className="card stat-card">
      <div className="stat-card-text">
        <div className="stat-card-label">{label}</div>
        <div className="stat-card-value" style={valueColor ? { color: valueColor } : undefined}>
          {value}
        </div>
      </div>
      <div className={`stat-card-icon tone-${tone}`}>
        <Icon size={20} />
      </div>
    </div>
  )
}
