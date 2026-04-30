import { useEffect, useState } from 'react'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Pencil, Trash2, Shield } from 'lucide-react'

function RoleModal({ onClose, onSaved, role }) {
  const editing = !!role
  const [name, setName] = useState(role?.name || '')
  const [description, setDescription] = useState(role?.description || '')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!editing && !name.trim()) return toast.error('Name is required')
    setLoading(true)
    try {
      if (editing) {
        const { data } = await api.put(`/roles/${role.name}`, { description })
        toast.success('Role updated')
        onSaved(data, role.name)
      } else {
        const { data } = await api.post('/roles', { name, description })
        toast.success('Role created')
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
          {editing ? 'Edit role' : 'New role'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. editor" required disabled={editing} />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={description} onChange={e => setDescription(e.target.value)}
              placeholder="Optional description" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
              {loading ? 'Saving...' : editing ? 'Save changes' : 'Create role'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RolesPage() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalRole, setModalRole] = useState(null)
  const [showModal, setShowModal] = useState(false)

  const load = () => api.get('/roles').then(r => setRoles(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const openCreate = () => { setModalRole(null); setShowModal(true) }
  const openEdit = r => { setModalRole(r); setShowModal(true) }

  const handleSaved = (data, oldName) => {
    if (modalRole) {
      setRoles(rs => rs.map(r => r.name === oldName ? data : r))
    } else {
      setRoles(rs => [...rs, data])
    }
  }

  const deleteRole = async r => {
    if (!confirm(`Delete role "${r.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/roles/${r.name}`)
      setRoles(rs => rs.filter(x => x.name !== r.name))
      toast.success('Role deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Roles</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage roles and permissions</p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus size={16} /> New role
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading...</div>
      ) : roles.length === 0 ? (
        <div className="card p-12 text-center">
          <Shield size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No roles yet</p>
          <p className="text-sm text-gray-400 mt-1">Create a role to get started</p>
          <button onClick={openCreate} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create role
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {roles.map(r => (
                <tr key={r.name} className="border-b border-gray-50 last:border-0">
                  <td className="px-5 py-3 font-medium text-gray-900 capitalize">{r.name}</td>
                  <td className="px-5 py-3 text-gray-500">{r.description || '—'}</td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => openEdit(r)} className="btn-secondary !px-3 !py-1.5 text-xs">
                        <Pencil size={13} /> Edit
                      </button>
                      <button onClick={() => deleteRole(r)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <RoleModal
          onClose={() => setShowModal(false)}
          onSaved={handleSaved}
          role={modalRole}
        />
      )}
    </div>
  )
}
