import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import { formatDistanceToNow } from 'date-fns'
import { Search, Filter } from 'lucide-react'

const STATUS_CLASSES = {
  pending: 'badge-pending', generated: 'badge-generated',
  approved: 'badge-approved', rejected: 'badge-rejected', error: 'badge-error'
}

export default function SubmissionsPage() {
  const { user } = useAuth()
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    api.get('/submissions/').then(r => setSubmissions(r.data)).finally(() => setLoading(false))
  }, [])

  const filtered = submissions.filter(s => {
    const matchSearch = !search ||
      s.template_name.toLowerCase().includes(search.toLowerCase()) ||
      s.submitted_by_name.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || s.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Submissions</h1>
          <p className="text-sm text-gray-500 mt-0.5">{submissions.length} total</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <input className="input pl-9 text-sm" placeholder="Search by template or user…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <select className="input pl-8 text-sm pr-8" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All statuses</option>
            <option value="generated">Generated</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-400 text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-gray-400 text-sm">No submissions found</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Template</th>
                {user.role !== 'staff' && <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Submitted by</th>}
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(s => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-gray-900">{s.template_name}</td>
                  {user.role !== 'staff' && <td className="px-5 py-3 text-gray-600">{s.submitted_by_name}</td>}
                  <td className="px-5 py-3 text-gray-500 text-xs">
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
