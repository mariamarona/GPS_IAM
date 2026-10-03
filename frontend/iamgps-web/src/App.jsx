import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import TeacherLayout from './components/TeacherLayout'
import RequireAuth from './components/RequireAuth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Alertes from './pages/Alertes'
import Cours from './pages/Cours'
import Utilisateurs from './pages/Utilisateurs'
import EnseignantDashboard from './pages/enseignant/Dashboard'
import EnseignantAlertes from './pages/enseignant/Alertes'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<Login />} />

        <Route
          element={
            <RequireAuth allowedRoles={['ADMIN', 'SUPER_ADMIN']}>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="alertes" element={<Alertes />} />
          <Route path="cours" element={<Cours />} />
          <Route path="utilisateurs" element={<Utilisateurs />} />
        </Route>

        <Route
          element={
            <RequireAuth allowedRoles={['TEACHER']}>
              <TeacherLayout />
            </RequireAuth>
          }
        >
          <Route path="enseignant" element={<EnseignantDashboard />} />
          <Route path="enseignant/alertes" element={<EnseignantAlertes />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App