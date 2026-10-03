import { Outlet } from 'react-router-dom'
import { LayoutGrid, TriangleAlert } from 'lucide-react'
import Sidebar from './Sidebar'

const TEACHER_NAV_ITEMS = [
  { to: '/enseignant', label: 'Tableau de bord', icon: LayoutGrid, end: true },
  { to: '/enseignant/alertes', label: 'Alertes de fraude', icon: TriangleAlert },
]

export default function TeacherLayout() {
  return (
    <div className="app-shell">
      <Sidebar navItems={TEACHER_NAV_ITEMS} badgeLabel="Espace Enseignant" />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}