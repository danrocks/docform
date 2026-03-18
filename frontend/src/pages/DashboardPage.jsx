import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api'
import { FileText, ClipboardList, CheckCircle, Clock, FilePlus, ArrowRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  )
}

const STATUS_CLASSES = {
  pending: 'badge-pending', generated: 'badge-generated',
  approved: 'badge-approved', rejected: 'badge-rejected', error: 'badge-error'
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [submissions, setSubmissions] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/submissions').then(r => setSubmissions(r.data)),
      user.role === 'admin' ? api.get('/templates').then(r => setTemplates(r.data)) : Promise.resolve()
    ]).finally(() => setLoading(false))
  }, [user])

  const stats = {
    total: submissions.length,
    pending: submissions.filter(s => s.status === 'pending' || s.status === 'generated').length,
    approved: submissions.filter(s => s.status === 'approved').length,
    templates: templates.length,
  }

  const recent = submissions.slice(0, 6)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user.name.split(' ')[0]}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5 capitalize">{user.role} · DocForm</p>
        </div>
        {(user.role === 'admin' || user.role === 'staff') && (
          <Link to="/submissions/new" className="btn-primary">
            <FilePlus size={16} /> New submission
          </Link>
        )}
      </div>

      {/* Stats */}
      <div className={`grid gap-4 mb-8 ${user.role === 'admin' ? 'grid-cols-4' : 'grid-cols-3'}`}>
        <StatCard icon={ClipboardList} label="Total submissions" value={stats.total} color="bg-brand-600" />
        <StatCard icon={Clock} label="Awaiting review" value={stats.pending} color="bg-amber-500" />
        <StatCard icon={CheckCircle} label="Approved" value={stats.approved} color="bg-emerald-500" />
        {user.role === 'admin' && (
          <StatCard icon={FileText} label="Templates" value={stats.templates} color="bg-purple-500" />
        )}
      </div>

      {/* Recent submissions */}
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Recent submissions</h2>
          <Link to="/submissions" className="text-sm text-brand-600 hover:text-brand-700 flex items-center gap-1">
            View all <ArrowRight size={14} />
          </Link>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading…</div>
        ) : recent.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <ClipboardList size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm">No submissions yet</p>
            {(user.role === 'admin' || user.role === 'staff') && (
              <Link to="/submissions/new" className="text-sm text-brand-600 hover:underline mt-1 inline-block">
                Start your first interview →
              </Link>
            )}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Template</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Submitted by</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">When</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recent.map(s => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-gray-900">{s.template_name}</td>
                  <td className="px-5 py-3 text-gray-600">{s.submitted_by_name}</td>
                  <td className="px-5 py-3 text-gray-500">
                    {formatDistanceToNow(new Date(s.submitted_at + 'Z'), { addSuffix: true })}
                  </td>
                  <td className="px-5 py-3">
                    <span className={STATUS_CLASSES[s.status] || 'badge'}>{s.status}</span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Link to={`/submissions/${s.id}`}
                      className="text-brand-600 hover:text-brand-700 text-xs font-medium">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
