import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/shared/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import TemplatesPage from './pages/TemplatesPage'
import TemplateEditPage from './pages/TemplateEditPage'
import NewSubmissionPage from './pages/NewSubmissionPage'
import SubmissionsPage from './pages/SubmissionsPage'
import SubmissionDetailPage from './pages/SubmissionDetailPage'
import AnswersetsPage from './pages/AnswersetsPage'
import AnswersetDetailPage from './pages/AnswersetDetailPage'
import UsersPage from './pages/UsersPage'
import RolesPage from './pages/RolesPage'
import WorkgroupsPage from './pages/WorkgroupsPage'
import WorkgroupDetailPage from './pages/WorkgroupDetailPage'
import WorkitemDetailPage from './pages/WorkitemDetailPage'
import ChangePasswordPage from './pages/ChangePasswordPage'

function PrivateRoute({ children, roles }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-brand-400">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="templates" element={<PrivateRoute roles={['admin']}><TemplatesPage /></PrivateRoute>} />
          <Route path="templates/:id/edit" element={<PrivateRoute roles={['admin']}><TemplateEditPage /></PrivateRoute>} />
          <Route path="submissions/new" element={<NewSubmissionPage />} />
          <Route path="submissions" element={<SubmissionsPage />} />
          <Route path="submissions/:id" element={<SubmissionDetailPage />} />
          <Route path="answersets" element={<AnswersetsPage />} />
          <Route path="answersets/:id" element={<AnswersetDetailPage />} />
          <Route path="users" element={<PrivateRoute roles={['admin']}><UsersPage /></PrivateRoute>} />
          <Route path="roles" element={<PrivateRoute roles={['admin']}><RolesPage /></PrivateRoute>} />
          <Route path="workgroups" element={<PrivateRoute roles={['admin']}><WorkgroupsPage /></PrivateRoute>} />
          <Route path="workgroups/:id" element={<PrivateRoute roles={['admin']}><WorkgroupDetailPage /></PrivateRoute>} />
          <Route path="workgroups/:workgroupId/workitems/:workitemId" element={<PrivateRoute><WorkitemDetailPage /></PrivateRoute>} />
          <Route path="change-password" element={<ChangePasswordPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
