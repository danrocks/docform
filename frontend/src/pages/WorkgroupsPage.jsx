import { useEffect, useState } from 'react'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Pencil, Trash2, Users, FileText, ShieldCheck, X, Search } from 'lucide-react'

function WorkgroupModal({ onClose, onSaved, workgroup }) {
  const editing = !!workgroup
  const [tab, setTab] = useState('settings')

  const [name, setName] = useState(workgroup?.name || '')
  const [description, setDescription] = useState(workgroup?.description || '')
  const [requiresApproval, setRequiresApproval] = useState(workgroup?.requires_approval || false)
  const [saving, setSaving] = useState(false)

  const [members, setMembers] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [memberSearch, setMemberSearch] = useState('')
  const [addingUser, setAddingUser] = useState(null)

  const [templates, setTemplates] = useState([])
  const [allTemplates, setAllTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [templateSearch, setTemplateSearch] = useState('')
  const [addingTemplate, setAddingTemplate] = useState(null)

  useEffect(() => {
    if (!editing) return
    setMembersLoading(true)
    setTemplatesLoading(true)
    Promise.all([
      api.get(`/workgroups/${workgroup.id}/users`),
      api.get('/users'),
    ]).then(([linksRes, usersRes]) => {
      const links = Array.isArray(linksRes.data) ? linksRes.data : []
      const users = usersRes.data.users || usersRes.data || []
      setAllUsers(users)
      const memberIds = links.map(l => l.user_id)
      setMembers(users.filter(u => memberIds.includes(u.id)))
    }).catch(() => toast.error('Failed to load members')).finally(() => setMembersLoading(false))

    Promise.all([
      api.get(`/workgroups/${workgroup.id}/templates`),
      api.get('/templates/'),
    ]).then(([linksRes, tplRes]) => {
      const links = Array.isArray(linksRes.data) ? linksRes.data : []
      const tpls = Array.isArray(tplRes.data) ? tplRes.data : []
      setAllTemplates(tpls)
      const tplIds = links.map(l => l.template_id)
      setTemplates(tpls.filter(t => tplIds.includes(t.id)))
    }).catch(() => toast.error('Failed to load templates')).finally(() => setTemplatesLoading(false))
  }, [editing, workgroup?.id])

  const handleSaveSettings = async e => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name is required')
    setSaving(true)
    try {
      if (editing) {
        const { data } = await api.put(`/workgroups/${workgroup.id}`, { name, description, requires_approval: requiresApproval })
        toast.success('Workgroup updated')
        onSaved(data)
      } else {
        const { data } = await api.post('/workgroups', { name, description, requires_approval: requiresApproval })
        toast.success('Workgroup created')
        onSaved(data)
        onClose()
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || (editing ? 'Update failed' : 'Create failed'))
    } finally {
      setSaving(false)
    }
  }

  const addMember = async user => {
    setAddingUser(user.id)
    try {
      await api.post(`/workgroups/${workgroup.id}/users`, { user_id: user.id })
      setMembers(ms => [...ms, user])
      toast.success(`${user.name} added`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add user')
    } finally {
      setAddingUser(null)
    }
  }

  const removeMember = async user => {
    if (!confirm(`Remove ${user.name} from this workgroup?`)) return
    try {
      await api.delete(`/workgroups/${workgroup.id}/users/${user.id}`)
      setMembers(ms => ms.filter(m => m.id !== user.id))
      toast.success(`${user.name} removed`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove user')
    }
  }

  const addTemplate = async tpl => {
    setAddingTemplate(tpl.id)
    try {
      await api.post(`/workgroups/${workgroup.id}/templates`, { template_id: tpl.id })
      setTemplates(ts => [...ts, tpl])
      toast.success(`${tpl.name} added`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add template')
    } finally {
      setAddingTemplate(null)
    }
  }

  const removeTemplate = async tpl => {
    if (!confirm(`Remove ${tpl.name} from this workgroup?`)) return
    try {
      await api.delete(`/workgroups/${workgroup.id}/templates/${tpl.id}`)
      setTemplates(ts => ts.filter(t => t.id !== tpl.id))
      toast.success(`${tpl.name} removed`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove template')
    }
  }

  const memberIds = members.map(m => m.id)
  const availableUsers = allUsers.filter(u => !memberIds.includes(u.id)).filter(u =>
    u.name?.toLowerCase().includes(memberSearch.toLowerCase()) ||
    u.username?.toLowerCase().includes(memberSearch.toLowerCase())
  )
  const templateIds = templates.map(t => t.id)
  const availableTemplates = allTemplates.filter(t => !templateIds.includes(t.id)).filter(t =>
    t.name?.toLowerCase().includes(templateSearch.toLowerCase())
  )

  const tabs = editing
    ? [
        { id: 'settings', label: 'Settings' },
        { id: 'members', label: `Members (${members.length})` },
        { id: 'templates', label: `Templates (${templates.length})` },
      ]
    : [{ id: 'settings', label: 'Settings' }]

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg p-0 max-h-[85vh] flex flex-col">
        <div className="px-6 pt-5 pb-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {editing ? workgroup.name : 'New workgroup'}
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
              <X size={18} />
            </button>
          </div>
          {tabs.length > 1 && (
            <div className="flex gap-1 border-b border-gray-100 -mx-6 px-6">
              {tabs.map(t => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                    tab === t.id
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-gray-400 hover:text-gray-600'
                  }`}>
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0">
          {tab === 'settings' && (
            <form id="wg-settings-form" onSubmit={handleSaveSettings} className="space-y-4">
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
              {editing && workgroup.created_at && (
                <p className="text-xs text-gray-400">Created {new Date(workgroup.created_at).toLocaleDateString()}</p>
              )}
            </form>
          )}

          {tab === 'members' && (
            <div className="space-y-3">
              {members.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Current members</p>
                  <div className="space-y-1">
                    {members.map(u => (
                      <div key={u.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{u.name}</p>
                          <p className="text-xs text-gray-400">{u.username} &middot; {u.role}</p>
                        </div>
                        <button onClick={() => removeMember(u)} className="text-gray-400 hover:text-red-500 transition-colors p-1" title="Remove">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Add members</p>
                <div className="relative mb-2">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input className="input !pl-9 !py-1.5 text-sm" value={memberSearch} onChange={e => setMemberSearch(e.target.value)} placeholder="Search users..." />
                </div>
                {membersLoading ? (
                  <p className="text-sm text-gray-400 text-center py-4">Loading...</p>
                ) : availableUsers.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">
                    {allUsers.length <= members.length ? 'All users are already members' : 'No matching users'}
                  </p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {availableUsers.map(u => (
                      <div key={u.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{u.name}</p>
                          <p className="text-xs text-gray-400">{u.username} &middot; {u.role}</p>
                        </div>
                        <button onClick={() => addMember(u)} disabled={addingUser === u.id}
                          className="btn-primary !px-3 !py-1 text-xs">
                          {addingUser === u.id ? '...' : 'Add'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {tab === 'templates' && (
            <div className="space-y-3">
              {templates.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Assigned templates</p>
                  <div className="space-y-1">
                    {templates.map(tpl => (
                      <div key={tpl.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText size={14} className="text-brand-600 flex-shrink-0" />
                          <p className="text-sm font-medium text-gray-900 truncate">{tpl.name}</p>
                          <span className={`badge text-xs flex-shrink-0 ${tpl.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                            {tpl.active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <button onClick={() => removeTemplate(tpl)} className="text-gray-400 hover:text-red-500 transition-colors p-1 flex-shrink-0" title="Remove">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Add templates</p>
                <div className="relative mb-2">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input className="input !pl-9 !py-1.5 text-sm" value={templateSearch} onChange={e => setTemplateSearch(e.target.value)} placeholder="Search templates..." />
                </div>
                {templatesLoading ? (
                  <p className="text-sm text-gray-400 text-center py-4">Loading...</p>
                ) : availableTemplates.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">
                    {allTemplates.length <= templates.length ? 'All templates are already assigned' : 'No matching templates'}
                  </p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {availableTemplates.map(tpl => (
                      <div key={tpl.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText size={14} className="text-gray-400 flex-shrink-0" />
                          <p className="text-sm font-medium text-gray-900 truncate">{tpl.name}</p>
                        </div>
                        <button onClick={() => addTemplate(tpl)} disabled={addingTemplate === tpl.id}
                          className="btn-primary !px-3 !py-1 text-xs">
                          {addingTemplate === tpl.id ? '...' : 'Add'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">
            {editing ? 'Close' : 'Cancel'}
          </button>
          {tab === 'settings' && (
            <button type="submit" form="wg-settings-form" disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? 'Saving...' : editing ? 'Save changes' : 'Create workgroup'}
            </button>
          )}
        </div>
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
  const closeModal = () => { setShowModal(false); if (modalWorkgroup) load() }

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
          <p className="text-sm text-gray-400 mt-1 max-w-md mx-auto">
            Workgroups let you organize users into teams and control which templates each team can access.
            Create a workgroup, then add members and assign templates to it.
          </p>
          <button onClick={openCreate} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create workgroup
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {workgroups.map(wg => (
            <div key={wg.id} className="card p-5">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Users size={18} className="text-brand-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{wg.name}</span>
                    {wg.requires_approval && (
                      <span className="badge bg-amber-100 text-amber-700 flex items-center gap-0.5">
                        <ShieldCheck size={10} /> Approval
                      </span>
                    )}
                  </div>
                  {wg.description && <p className="text-sm text-gray-500 truncate mt-0.5">{wg.description}</p>}
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <Users size={11} /> {memberCounts[wg.id] ?? '...'} members
                    </span>
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <FileText size={11} /> {templateCounts[wg.id] ?? '...'} templates
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button onClick={() => openEdit(wg)} className="btn-secondary !px-3 !py-1.5 text-xs">
                    <Pencil size={13} /> Edit
                  </button>
                  <button onClick={() => deleteWorkgroup(wg)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <WorkgroupModal
          onClose={closeModal}
          onSaved={handleSaved}
          workgroup={modalWorkgroup}
        />
      )}
    </div>
  )
}
