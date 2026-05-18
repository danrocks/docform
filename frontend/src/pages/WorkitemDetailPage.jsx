import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { ChevronRight, ClipboardList, Pencil, Trash2, X } from 'lucide-react'

const STATUS_OPTIONS = ['draft', 'active', 'completed', 'cancelled']

const STATUS_STYLES = {
  draft: 'bg-brand-100 text-brand-500',
  active: 'bg-accent-100 text-accent-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

function EditWorkitemModal({ onClose, onSaved, workgroupId, workitem }) {
  const [name, setName] = useState(workitem.name)
  const [description, setDescription] = useState(workitem.description || '')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name is required')
    setSaving(true)
    try {
      const { data } = await api.put(`/workgroups/${workgroupId}/workitems/${workitem.id}`, { name, description })
      toast.success('Workitem updated')
      onSaved(data)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-brand-900">Edit workitem</h2>
          <button onClick={onClose} className="text-brand-400 hover:text-brand-600 transition-colors">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Q1 Report" required />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function WorkitemDetailPage() {
  const { workgroupId, workitemId } = useParams()
  const navigate = useNavigate()
  const [workitem, setWorkitem] = useState(null)
  const [workgroup, setWorkgroup] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [changingStatus, setChangingStatus] = useState(false)

  const load = async () => {
    try {
      const [wiRes, wgRes] = await Promise.all([
        api.get(`/workgroups/${workgroupId}/workitems/${workitemId}`),
        api.get(`/workgroups/${workgroupId}`),
      ])
      setWorkitem(wiRes.data)
      setWorkgroup(wgRes.data)
    } catch {
      toast.error('Failed to load workitem')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [workgroupId, workitemId])

  const changeStatus = async newStatus => {
    setChangingStatus(true)
    try {
      const { data } = await api.put(`/workgroups/${workgroupId}/workitems/${workitemId}`, { status: newStatus })
      setWorkitem(data)
      toast.success(`Status changed to ${newStatus}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update status')
    } finally {
      setChangingStatus(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Delete workitem "${workitem.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/workgroups/${workgroupId}/workitems/${workitemId}`)
      toast.success('Workitem deleted')
      navigate(`/workgroups/${workgroupId}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    }
  }

  if (loading) {
    return <div className="text-center text-brand-400 py-16 text-sm">Loading...</div>
  }

  if (!workitem) {
    return <div className="text-center text-brand-400 py-16 text-sm">Workitem not found</div>
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-brand-400 mb-4">
        <Link to="/workgroups" className="hover:text-brand-600 transition-colors">Workgroups</Link>
        <ChevronRight size={14} />
        <Link to={`/workgroups/${workgroupId}`} className="hover:text-brand-600 transition-colors">
          {workgroup?.name || 'Workgroup'}
        </Link>
        <ChevronRight size={14} />
        <span className="text-brand-700 font-medium">{workitem.name}</span>
      </div>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <ClipboardList size={20} className="text-brand-600" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-brand-900">{workitem.name}</h1>
            {workitem.description && <p className="text-sm text-brand-500 mt-0.5">{workitem.description}</p>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button onClick={() => setShowEdit(true)} className="btn-secondary !px-3 !py-1.5 text-xs">
              <Pencil size={13} /> Edit
            </button>
            <button onClick={handleDelete} className="text-brand-400 hover:text-red-500 transition-colors p-1" title="Delete workitem">
              <Trash2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Details card */}
      <div className="card p-6 mb-6">
        <h2 className="text-sm font-medium text-brand-500 uppercase tracking-wider mb-4">Details</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-brand-400 mb-1">Status</p>
            <span className={`badge ${STATUS_STYLES[workitem.status] || STATUS_STYLES.draft} capitalize`}>
              {workitem.status}
            </span>
          </div>
          <div>
            <p className="text-xs text-brand-400 mb-1">Created</p>
            <p className="text-sm text-brand-900">{new Date(workitem.created_at).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-brand-400 mb-1">Workgroup</p>
            <Link to={`/workgroups/${workgroupId}`} className="text-sm text-brand-600 hover:text-brand-800 transition-colors">
              {workgroup?.name || workgroupId}
            </Link>
          </div>
          <div>
            <p className="text-xs text-brand-400 mb-1">Created by</p>
            <p className="text-sm text-brand-900">{workitem.created_by}</p>
          </div>
        </div>
      </div>

      {/* Status transitions */}
      <div className="card p-6 mb-6">
        <h2 className="text-sm font-medium text-brand-500 uppercase tracking-wider mb-4">Change status</h2>
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => changeStatus(s)}
              disabled={changingStatus || workitem.status === s}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                workitem.status === s
                  ? 'bg-brand-100 text-brand-400 cursor-default'
                  : 'bg-brand-50 text-brand-700 hover:bg-brand-100'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {workitem.status === s && ' (current)'}
            </button>
          ))}
        </div>
      </div>

      {/* Interviews placeholder */}
      <div className="card p-6">
        <h2 className="text-sm font-medium text-brand-500 uppercase tracking-wider mb-4">Interviews</h2>
        <div className="text-center py-8">
          <ClipboardList size={32} className="mx-auto mb-2 text-brand-300" />
          <p className="text-sm text-brand-400">Interviews for this workitem will appear here.</p>
        </div>
      </div>

      {showEdit && (
        <EditWorkitemModal
          onClose={() => setShowEdit(false)}
          onSaved={setWorkitem}
          workgroupId={workgroupId}
          workitem={workitem}
        />
      )}
    </div>
  )
}
