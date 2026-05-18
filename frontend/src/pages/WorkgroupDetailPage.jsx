import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Trash2, ChevronRight, X, Pencil, ClipboardList } from 'lucide-react'

function WorkitemModal({ onClose, onSaved, workgroupId, workitem }) {
  const editing = !!workitem
  const [name, setName] = useState(workitem?.name || '')
  const [description, setDescription] = useState(workitem?.description || '')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name is required')
    setSaving(true)
    try {
      if (editing) {
        const { data } = await api.put(`/workgroups/${workgroupId}/workitems/${workitem.id}`, { name, description })
        toast.success('Workitem updated')
        onSaved(data)
      } else {
        const { data } = await api.post(`/workgroups/${workgroupId}/workitems`, { name, description })
        toast.success('Workitem created')
        onSaved(data)
      }
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || (editing ? 'Update failed' : 'Create failed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-brand-900">{editing ? 'Edit workitem' : 'New workitem'}</h2>
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
              {saving ? 'Saving...' : editing ? 'Save changes' : 'Create workitem'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function WorkgroupDetailPage() {
  const { id } = useParams()
  const [workgroup, setWorkgroup] = useState(null)
  const [workitems, setWorkitems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showWorkitemModal, setShowWorkitemModal] = useState(false)
  const [editingWorkitem, setEditingWorkitem] = useState(null)

  const load = async () => {
    try {
      const [wgRes, workitemsRes] = await Promise.all([
        api.get(`/workgroups/${id}`),
        api.get(`/workgroups/${id}/workitems`).catch(() => ({ data: [] })),
      ])
      setWorkgroup(wgRes.data)
      setWorkitems(Array.isArray(workitemsRes.data) ? workitemsRes.data : [])
    } catch {
      toast.error('Failed to load workgroup')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const handleWorkitemSaved = wi => {
    setWorkitems(items => {
      const idx = items.findIndex(w => w.id === wi.id)
      if (idx >= 0) return items.map(w => w.id === wi.id ? wi : w)
      return [...items, wi]
    })
  }

  const removeWorkitem = async wi => {
    if (!confirm(`Delete workitem "${wi.name}"?`)) return
    try {
      await api.delete(`/workgroups/${id}/workitems/${wi.id}`)
      setWorkitems(items => items.filter(w => w.id !== wi.id))
      toast.success('Workitem deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete workitem')
    }
  }

  if (loading) {
    return <div className="text-center text-brand-400 py-16 text-sm">Loading...</div>
  }

  if (!workgroup) {
    return <div className="text-center text-brand-400 py-16 text-sm">Workgroup not found</div>
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-brand-400 mb-4">
        <Link to="/workgroups" className="hover:text-brand-600 transition-colors">Workgroups</Link>
        <ChevronRight size={14} />
        <span className="text-brand-700 font-medium">{workgroup.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-brand-900">{workgroup.name} — Workitems</h1>
          {workgroup.description && <p className="text-sm text-brand-500 mt-0.5">{workgroup.description}</p>}
        </div>
        <button onClick={() => { setEditingWorkitem(null); setShowWorkitemModal(true) }} className="btn-primary">
          <Plus size={16} /> New workitem
        </button>
      </div>

      {/* Workitems */}
      {workitems.length === 0 ? (
        <div className="card p-12 text-center">
          <ClipboardList size={40} className="mx-auto mb-3 text-brand-300" />
          <p className="text-brand-500 font-medium">No workitems yet</p>
          <p className="text-sm text-brand-400 mt-1 max-w-md mx-auto">
            Create a workitem to get started. Each workitem tracks the completion of templates assigned to this workgroup.
          </p>
          <button onClick={() => { setEditingWorkitem(null); setShowWorkitemModal(true) }} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create workitem
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-brand-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Created</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {workitems.map(wi => (
                <tr key={wi.id} className="border-b border-brand-50 last:border-0">
                  <td className="px-5 py-3">
                    <Link to={`/workgroups/${id}/workitems/${wi.id}`} className="font-medium text-brand-900 hover:text-brand-600 transition-colors">{wi.name}</Link>
                    {wi.description && <p className="text-xs text-brand-400 truncate max-w-[250px]">{wi.description}</p>}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`badge ${
                      wi.status === 'active' ? 'bg-accent-100 text-accent-700' :
                      wi.status === 'completed' ? 'bg-green-100 text-green-700' :
                      wi.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                      'bg-brand-100 text-brand-500'
                    } capitalize`}>{wi.status}</span>
                  </td>
                  <td className="px-5 py-3 text-brand-500">{new Date(wi.created_at).toLocaleDateString()}</td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => { setEditingWorkitem(wi); setShowWorkitemModal(true) }} className="text-brand-400 hover:text-brand-600 transition-colors p-1" title="Edit">
                      <Pencil size={16} />
                    </button>
                    <button onClick={() => removeWorkitem(wi)} className="text-brand-400 hover:text-red-500 transition-colors p-1" title="Delete">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showWorkitemModal && (
        <WorkitemModal
          onClose={() => { setShowWorkitemModal(false); setEditingWorkitem(null) }}
          onSaved={handleWorkitemSaved}
          workgroupId={id}
          workitem={editingWorkitem}
        />
      )}
    </div>
  )
}
