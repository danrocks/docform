import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Pencil, Trash2, Users, FileText, ShieldCheck, ChevronRight } from 'lucide-react'

function WorkgroupModal({ onClose, onSaved, workgroup }) {
  const editing = !!workgroup
  const [name, setName] = useState(workgroup?.name || '')
  const [description, setDescription] = useState(workgroup?.description || '')
  const [requiresApproval, setRequiresApproval] = useState(workgroup?.requires_approval || false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name is required')
    setLoading(true)
    try {
      if (editing) {
        const { data } = await api.put(`/workgroups/${workgroup.id}`, { name, description, requires_approval: requiresApproval })
        toast.success('Workgroup updated')
        onSaved(data)
      } else {
        const { data } = await api.post('/workgroups', { name, description, requires_approval: requiresApproval })
        toast.success('Workgroup created')
        onSaved(data)
      }
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || (editing ? 'Update failed' : 'Create failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {editing ? 'Edit workgroup' : 'New workgroup'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Finance Team" required />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
          </div>
          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={requiresApproval} onChange={e => setRequiresApproval(e.target.checked)} className="sr-only peer" />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brand-600"></div>
            </label>
            <div>
              <p className="text-sm font-medium text-gray-700">Requires approval</p>
              <p className="text-xs text-gray-400">Submissions from this workgroup need approval before finalizing</p>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
              {loading ? 'Saving...' : editing ? 'Save changes' : 'Create workgroup'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function WorkgroupsPage() {
  const [workgroups, setWorkgroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalWorkgroup, setModalWorkgroup] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [memberCounts, setMemberCounts] = useState({})
  const [templateCounts, setTemplateCounts] = useState({})

  const load = async () => {
    try {
      const { data } = await api.get('/workgroups')
      const wgs = Array.isArray(data) ? data : []
      setWorkgroups(wgs)

      const counts = {}
      const tCounts = {}
      await Promise.all(wgs.map(async wg => {
        try {
          const [usersRes, templatesRes] = await Promise.all([
            api.get(`/workgroups/${wg.id}/users`),
            api.get(`/workgroups/${wg.id}/templates`),
          ])
          counts[wg.id] = Array.isArray(usersRes.data) ? usersRes.data.length : 0
          tCounts[wg.id] = Array.isArray(templatesRes.data) ? templatesRes.data.length : 0
        } catch {
          counts[wg.id] = 0
          tCounts[wg.id] = 0
        }
      }))
      setMemberCounts(counts)
      setTemplateCounts(tCounts)
    } catch (err) {
      toast.error('Failed to load workgroups')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openCreate = () => { setModalWorkgroup(null); setShowModal(true) }
  const openEdit = wg => { setModalWorkgroup(wg); setShowModal(true) }

  const handleSaved = data => {
    if (modalWorkgroup) {
      setWorkgroups(wgs => wgs.map(w => w.id === data.id ? data : w))
    } else {
      setWorkgroups(wgs => [data, ...wgs])
      setMemberCounts(c => ({ ...c, [data.id]: 0 }))
      setTemplateCounts(c => ({ ...c, [data.id]: 0 }))
    }
  }

  const deleteWorkgroup = async wg => {
    if (!confirm(`Delete workgroup "${wg.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/workgroups/${wg.id}`)
      setWorkgroups(wgs => wgs.filter(w => w.id !== wg.id))
      toast.success('Workgroup deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workgroups</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage workgroups, members, and template access</p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus size={16} /> New workgroup
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading...</div>
      ) : workgroups.length === 0 ? (
        <div className="card p-12 text-center">
          <Users size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No workgroups yet</p>
          <p className="text-sm text-gray-400 mt-1">Create a workgroup to organize users and control template access</p>
          <button onClick={openCreate} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create workgroup
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {workgroups.map(wg => (
            <div key={wg.id} className="card p-5 flex items-center gap-4">
              <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
                <Users size={18} className="text-brand-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{wg.name}</p>
                  {wg.requires_approval && (
                    <span className="badge bg-amber-100 text-amber-700 flex items-center gap-0.5">
                      <ShieldCheck size={10} /> Approval
                    </span>
                  )}
                </div>
                {wg.description && <p className="text-sm text-gray-500 truncate mt-0.5">{wg.description}</p>}
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><Users size={11} /> {memberCounts[wg.id] ?? '...'} members</span>
                  <span className="flex items-center gap-1"><FileText size={11} /> {templateCounts[wg.id] ?? '...'} templates</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Link to={`/workgroups/${wg.id}`} className="btn-secondary !px-3 !py-1.5 text-xs">
                  View <ChevronRight size={13} />
                </Link>
                <button onClick={() => openEdit(wg)} className="btn-secondary !px-3 !py-1.5 text-xs">
                  <Pencil size={13} /> Edit
                </button>
                <button onClick={() => deleteWorkgroup(wg)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <WorkgroupModal
          onClose={() => setShowModal(false)}
          onSaved={handleSaved}
          workgroup={modalWorkgroup}
        />
      )}
    </div>
  )
}
