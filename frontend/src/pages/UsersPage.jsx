import { useEffect, useState } from 'react'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Pencil, Trash2, Users } from 'lucide-react'

function UserModal({ onClose, onSaved, user, roles }) {
  const editing = !!user
  const [name, setName] = useState(user?.name || '')
  const [username, setUsername] = useState(user?.username || '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(user?.role || (roles[0]?.name || ''))
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Name is required')
    if (!username.trim()) return toast.error('Username is required')
    if (!editing && !password) return toast.error('Password is required')
    setLoading(true)
    try {
      if (editing) {
        const body = { name, username, role }
        if (password) body.password = password
        const { data } = await api.put(`/users/${user.id}`, body)
        toast.success('User updated')
        onSaved(data)
      } else {
        const { data } = await api.post('/users', { name, username, password, role })
        toast.success('User created')
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
          {editing ? 'Edit user' : 'New user'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Full name" required />
          </div>
          <div>
            <label className="label">Username *</label>
            <input className="input" value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" required />
          </div>
          <div>
            <label className="label">Role *</label>
            <select className="input" value={role} onChange={e => setRole(e.target.value)} required>
              {roles.map(r => (
                <option key={r.name} value={r.name}>{r.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{editing ? 'Password (leave blank to keep current)' : 'Password *'}</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder={editing ? 'Leave blank to keep current' : 'Password'}
              required={!editing} />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
              {loading ? 'Saving...' : editing ? 'Save changes' : 'Create user'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalUser, setModalUser] = useState(null)
  const [showModal, setShowModal] = useState(false)

  const load = () => {
    Promise.all([
      api.get('/users'),
      api.get('/roles'),
    ]).then(([usersRes, rolesRes]) => {
      setUsers(usersRes.data.users)
      setRoles(rolesRes.data)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const openCreate = () => { setModalUser(null); setShowModal(true) }
  const openEdit = u => { setModalUser(u); setShowModal(true) }

  const handleSaved = data => {
    if (modalUser) {
      setUsers(us => us.map(u => u.id === data.id ? data : u))
    } else {
      setUsers(us => [data, ...us])
    }
  }

  const deleteUser = async u => {
    if (!confirm(`Delete user "${u.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/users/${u.id}`)
      setUsers(us => us.filter(x => x.id !== u.id))
      toast.success('User deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage user accounts and roles</p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus size={16} /> New user
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading...</div>
      ) : users.length === 0 ? (
        <div className="card p-12 text-center">
          <Users size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No users yet</p>
          <p className="text-sm text-gray-400 mt-1">Create a user account to get started</p>
          <button onClick={openCreate} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create user
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Username</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-5 py-3 font-medium text-gray-900">{u.name}</td>
                  <td className="px-5 py-3 text-gray-500">{u.username}</td>
                  <td className="px-5 py-3">
                    <span className="badge bg-brand-50 text-brand-700 capitalize">{u.role}</span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => openEdit(u)} className="btn-secondary !px-3 !py-1.5 text-xs">
                        <Pencil size={13} /> Edit
                      </button>
                      <button onClick={() => deleteUser(u)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
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
        <UserModal
          onClose={() => setShowModal(false)}
          onSaved={handleSaved}
          user={modalUser}
          roles={roles}
        />
      )}
    </div>
  )
}
