import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import { formatDistanceToNow } from 'date-fns'
import { Search, Filter, ChevronLeft, ChevronRight, Copy, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

const STATUS_CLASSES = {
  pending: 'badge-pending', generated: 'badge-generated',
  approved: 'badge-approved', rejected: 'badge-rejected', error: 'badge-error'
}

export default function AnswersetsPage() {
  const { user } = useAuth()
  const [answersets, setAnswersets] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit] = useState(20)

  const fetchAnswersets = useCallback(() => {
    setLoading(true)
    api.get('/answersets/', { params: { skip, limit } })
      .then(r => {
        setAnswersets(r.data.answersets || [])
        setTotal(r.data.total || 0)
      })
      .catch(() => {
        // Fallback to legacy submissions endpoint
        api.get('/submissions/').then(r => {
          setAnswersets(Array.isArray(r.data) ? r.data : [])
          setTotal(Array.isArray(r.data) ? r.data.length : 0)
        })
      })
      .finally(() => setLoading(false))
  }, [skip, limit])

  useEffect(() => { fetchAnswersets() }, [fetchAnswersets])

  const handleClone = async (e, id) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await api.post(`/answersets/${id}/clone`)
      toast.success('Answerset cloned')
      fetchAnswersets()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Clone failed')
    }
  }

  const handleDelete = async (e, id) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this answerset?')) return
    try {
      await api.delete(`/answersets/${id}`)
      toast.success('Answerset deleted')
      fetchAnswersets()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed')
    }
  }

  const filtered = answersets.filter(s => {
    const matchSearch = !search ||
      (s.template_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (s.submitted_by_name || '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || s.status === statusFilter
    return matchSearch && matchStatus
  })

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(skip / limit) + 1

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">Answersets</h1>
          <p className="text-sm text-brand-500 mt-0.5">{total} total</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400"/>
          <input className="input pl-9 text-sm" placeholder="Search by template or user…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400"/>
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
          <div className="p-10 text-center text-brand-400 text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-brand-400 text-sm">No answersets found</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-brand-100 bg-brand-50">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Template</th>
                {user.role !== 'staff' && <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Submitted by</th>}
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Date</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-50">
              {filtered.map(s => (
                <tr key={s.id} className="hover:bg-brand-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-brand-900">{s.template_name}</td>
                  {user.role !== 'staff' && <td className="px-5 py-3 text-brand-600">{s.submitted_by_name}</td>}
                  <td className="px-5 py-3 text-brand-500 text-xs">
                    {s.submitted_at ? formatDistanceToNow(new Date(s.submitted_at), { addSuffix: true }) : '—'}
                  </td>
                  <td className="px-5 py-3">
                    <span className={STATUS_CLASSES[s.status] || 'badge'}>{s.status}</span>
                  </td>
                  <td className="px-5 py-3 text-right flex items-center justify-end gap-2">
                    <button onClick={e => handleClone(e, s.id)} title="Clone"
                      className="text-brand-400 hover:text-brand-600 transition-colors">
                      <Copy size={14} />
                    </button>
                    {(user.role === 'admin' || s.submitted_by === user.id) && (
                      <button onClick={e => handleDelete(e, s.id)} title="Delete"
                        className="text-brand-400 hover:text-red-600 transition-colors">
                        <Trash2 size={14} />
                      </button>
                    )}
                    <Link to={`/answersets/${s.id}`}
                      className="text-brand-600 hover:text-brand-700 text-xs font-medium ml-2">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-brand-500">
            Showing {skip + 1}–{Math.min(skip + limit, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-sm btn-secondary"
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - limit))}
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <span className="text-sm text-brand-600">Page {currentPage} of {totalPages}</span>
            <button
              className="btn btn-sm btn-secondary"
              disabled={skip + limit >= total}
              onClick={() => setSkip(skip + limit)}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
