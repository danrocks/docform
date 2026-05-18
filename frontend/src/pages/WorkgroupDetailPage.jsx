import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Users, FileText, Plus, Trash2, ShieldCheck, ChevronRight, X, Search, Pencil, ClipboardList } from 'lucide-react'

function AddMemberModal({ onClose, onAdded, workgroupId, existingUserIds }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState(null)

  useEffect(() => {
    api.get('/users').then(r => {
      const allUsers = r.data.users || r.data || []
      setUsers(allUsers.filter(u => !existingUserIds.includes(u.id)))
    }).catch(() => toast.error('Failed to load users')).finally(() => setLoading(false))
  }, [existingUserIds])

  const filtered = users.filter(u =>
    u.name?.toLowerCase().includes(search.toLowerCase()) ||
    u.username?.toLowerCase().includes(search.toLowerCase())
  )

  const addUser = async user => {
    setAdding(user.id)
    try {
      await api.post(`/workgroups/${workgroupId}/users`, { user_id: user.id })
      toast.success(`${user.name} added to workgroup`)
      onAdded(user)
      setUsers(us => us.filter(u => u.id !== user.id))
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add user')
    } finally {
      setAdding(null)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-brand-900">Add members</h2>
          <button onClick={onClose} className="text-brand-400 hover:text-brand-600 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="relative mb-3">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400" />
          <input className="input !pl-9" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users..." />
        </div>
        <div className="flex-1 overflow-y-auto space-y-1 min-h-0">
          {loading ? (
            <p className="text-sm text-brand-400 text-center py-8">Loading...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-brand-400 text-center py-8">
              {users.length === 0 ? 'All users are already members' : 'No matching users'}
            </p>
          ) : (
            filtered.map(u => (
              <div key={u.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-brand-50">
                <div>
                  <p className="text-sm font-medium text-brand-900">{u.name}</p>
                  <p className="text-xs text-brand-400">{u.username} &middot; {u.role}</p>
                </div>
                <button onClick={() => addUser(u)} disabled={adding === u.id}
                  className="btn-primary !px-3 !py-1 text-xs">
                  {adding === u.id ? 'Adding...' : 'Add'}
                </button>
              </div>
            ))
          )}
        </div>
        <div className="pt-3 mt-3 border-t border-brand-100">
          <button onClick={onClose} className="btn-secondary w-full justify-center">Done</button>
        </div>
      </div>
    </div>
  )
}

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

function AddTemplateModal({ onClose, onAdded, workgroupId, existingTemplateIds }) {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState(null)

  useEffect(() => {
    api.get('/templates/').then(r => {
      const allTemplates = Array.isArray(r.data) ? r.data : []
      setTemplates(allTemplates.filter(t => !existingTemplateIds.includes(t.id)))
    }).catch(() => toast.error('Failed to load templates')).finally(() => setLoading(false))
  }, [existingTemplateIds])

  const filtered = templates.filter(t =>
    t.name?.toLowerCase().includes(search.toLowerCase())
  )

  const addTemplate = async tpl => {
    setAdding(tpl.id)
    try {
      await api.post(`/workgroups/${workgroupId}/templates`, { template_id: tpl.id })
      toast.success(`${tpl.name} added to workgroup`)
      onAdded(tpl)
      setTemplates(ts => ts.filter(t => t.id !== tpl.id))
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add template')
    } finally {
      setAdding(null)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-brand-900">Add templates</h2>
          <button onClick={onClose} className="text-brand-400 hover:text-brand-600 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="relative mb-3">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400" />
          <input className="input !pl-9" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search templates..." />
        </div>
        <div className="flex-1 overflow-y-auto space-y-1 min-h-0">
          {loading ? (
            <p className="text-sm text-brand-400 text-center py-8">Loading...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-brand-400 text-center py-8">
              {templates.length === 0 ? 'All templates are already assigned' : 'No matching templates'}
            </p>
          ) : (
            filtered.map(t => (
              <div key={t.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-brand-50">
                <div>
                  <p className="text-sm font-medium text-brand-900">{t.name}</p>
                  {t.description && <p className="text-xs text-brand-400 truncate max-w-[250px]">{t.description}</p>}
                </div>
                <button onClick={() => addTemplate(t)} disabled={adding === t.id}
                  className="btn-primary !px-3 !py-1 text-xs">
                  {adding === t.id ? 'Adding...' : 'Add'}
                </button>
              </div>
            ))
          )}
        </div>
        <div className="pt-3 mt-3 border-t border-brand-100">
          <button onClick={onClose} className="btn-secondary w-full justify-center">Done</button>
        </div>
      </div>
    </div>
  )
}

export default function WorkgroupDetailPage() {
  const { id } = useParams()
  const [workgroup, setWorkgroup] = useState(null)
  const [members, setMembers] = useState([])
  const [templates, setTemplates] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [allTemplates, setAllTemplates] = useState([])
  const [workitems, setWorkitems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddMember, setShowAddMember] = useState(false)
  const [showAddTemplate, setShowAddTemplate] = useState(false)
  const [showWorkitemModal, setShowWorkitemModal] = useState(false)
  const [editingWorkitem, setEditingWorkitem] = useState(null)

  const load = async () => {
    try {
      const [wgRes, membersRes, templatesRes, usersRes, tplRes, workitemsRes] = await Promise.all([
        api.get(`/workgroups/${id}`),
        api.get(`/workgroups/${id}/users`),
        api.get(`/workgroups/${id}/templates`),
        api.get('/users'),
        api.get('/templates/'),
        api.get(`/workgroups/${id}/workitems`).catch(() => ({ data: [] })),
      ])
      setWorkgroup(wgRes.data)
      const memberLinks = Array.isArray(membersRes.data) ? membersRes.data : []
      const templateLinks = Array.isArray(templatesRes.data) ? templatesRes.data : []
      const usersArr = usersRes.data.users || usersRes.data || []
      const tplArr = Array.isArray(tplRes.data) ? tplRes.data : []
      setAllUsers(usersArr)
      setAllTemplates(tplArr)

      const memberUserIds = memberLinks.map(m => m.user_id)
      setMembers(usersArr.filter(u => memberUserIds.includes(u.id)))

      const templateIds = templateLinks.map(t => t.template_id)
      setTemplates(tplArr.filter(t => templateIds.includes(t.id)))

      setWorkitems(Array.isArray(workitemsRes.data) ? workitemsRes.data : [])
    } catch {
      toast.error('Failed to load workgroup')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const removeMember = async user => {
    if (!confirm(`Remove ${user.name} from this workgroup?`)) return
    try {
      await api.delete(`/workgroups/${id}/users/${user.id}`)
      setMembers(ms => ms.filter(m => m.id !== user.id))
      toast.success(`${user.name} removed`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove user')
    }
  }

  const removeTemplate = async tpl => {
    if (!confirm(`Remove ${tpl.name} from this workgroup?`)) return
    try {
      await api.delete(`/workgroups/${id}/templates/${tpl.id}`)
      setTemplates(ts => ts.filter(t => t.id !== tpl.id))
      toast.success(`${tpl.name} removed`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove template')
    }
  }

  const handleMemberAdded = user => {
    setMembers(ms => [...ms, user])
  }

  const handleTemplateAdded = tpl => {
    setTemplates(ts => [...ts, tpl])
  }

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
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-brand-900">{workgroup.name}</h1>
          {workgroup.requires_approval && (
            <span className="badge bg-amber-100 text-amber-700 flex items-center gap-0.5">
              <ShieldCheck size={10} /> Requires approval
            </span>
          )}
        </div>
        {workgroup.description && <p className="text-sm text-brand-500 mt-1">{workgroup.description}</p>}
        <p className="text-xs text-brand-400 mt-1">
          Created {new Date(workgroup.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Members Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-brand-900 flex items-center gap-2">
            <Users size={18} className="text-brand-400" /> Members
            <span className="text-sm font-normal text-brand-400">({members.length})</span>
          </h2>
          <button onClick={() => setShowAddMember(true)} className="btn-primary !py-1.5 text-xs">
            <Plus size={14} /> Add member
          </button>
        </div>
        {members.length === 0 ? (
          <div className="card p-8 text-center">
            <Users size={32} className="mx-auto mb-2 text-brand-300" />
            <p className="text-sm text-brand-400">No members yet. Add users to this workgroup.</p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-brand-100">
                  <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Name</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Username</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Role</th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-brand-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map(u => (
                  <tr key={u.id} className="border-b border-brand-50 last:border-0">
                    <td className="px-5 py-3 font-medium text-brand-900">{u.name}</td>
                    <td className="px-5 py-3 text-brand-500">{u.username}</td>
                    <td className="px-5 py-3">
                      <span className="badge bg-brand-50 text-brand-700 capitalize">{u.role}</span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => removeMember(u)} className="text-brand-400 hover:text-red-500 transition-colors p-1" title="Remove from workgroup">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Workitems Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-brand-900 flex items-center gap-2">
            <ClipboardList size={18} className="text-brand-400" /> Workitems
            <span className="text-sm font-normal text-brand-400">({workitems.length})</span>
          </h2>
          <button onClick={() => { setEditingWorkitem(null); setShowWorkitemModal(true) }} className="btn-primary !py-1.5 text-xs">
            <Plus size={14} /> New workitem
          </button>
        </div>
        {workitems.length === 0 ? (
          <div className="card p-8 text-center">
            <ClipboardList size={32} className="mx-auto mb-2 text-brand-300" />
            <p className="text-sm text-brand-400">No workitems yet. Create a workitem to get started.</p>
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
      </div>

      {/* Templates Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-brand-900 flex items-center gap-2">
            <FileText size={18} className="text-brand-400" /> Templates
            <span className="text-sm font-normal text-brand-400">({templates.length})</span>
          </h2>
          <button onClick={() => setShowAddTemplate(true)} className="btn-primary !py-1.5 text-xs">
            <Plus size={14} /> Add template
          </button>
        </div>
        {templates.length === 0 ? (
          <div className="card p-8 text-center">
            <FileText size={32} className="mx-auto mb-2 text-brand-300" />
            <p className="text-sm text-brand-400">No templates yet. Add templates to this workgroup.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {templates.map(tpl => (
              <div key={tpl.id} className="card p-4 flex items-center gap-3">
                <div className="w-8 h-8 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText size={15} className="text-brand-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-brand-900">{tpl.name}</p>
                  {tpl.description && <p className="text-xs text-brand-400 truncate">{tpl.description}</p>}
                </div>
                <span className={`badge ${tpl.active ? 'bg-accent-100 text-accent-700' : 'bg-brand-100 text-brand-500'}`}>
                  {tpl.active ? 'Active' : 'Inactive'}
                </span>
                <button onClick={() => removeTemplate(tpl)} className="text-brand-400 hover:text-red-500 transition-colors p-1" title="Remove from workgroup">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAddMember && (
        <AddMemberModal
          onClose={() => setShowAddMember(false)}
          onAdded={handleMemberAdded}
          workgroupId={id}
          existingUserIds={members.map(m => m.id)}
        />
      )}

      {showAddTemplate && (
        <AddTemplateModal
          onClose={() => setShowAddTemplate(false)}
          onAdded={handleTemplateAdded}
          workgroupId={id}
          existingTemplateIds={templates.map(t => t.id)}
        />
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
