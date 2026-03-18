import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Upload, FileText, Pencil, Trash2, ToggleLeft, ToggleRight, ClipboardList } from 'lucide-react'

function UploadModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)

  const onDrop = useCallback(accepted => { if (accepted[0]) setFile(accepted[0]) }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] }, maxFiles: 1
  })

  const handleSubmit = async e => {
    e.preventDefault()
    if (!file) return toast.error('Please select a .docx file')
    if (!name.trim()) return toast.error('Please enter a template name')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('name', name)
      fd.append('description', description)
      fd.append('file', file)
      const { data } = await api.post('/templates/', fd)
      toast.success(`Template created — ${data.fields.length} field(s) detected`)
      onCreated(data)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload template</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Template name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Service Agreement" required />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
          </div>
          <div>
            <label className="label">Word document (.docx) *</label>
            <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-brand-400 bg-brand-50' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input {...getInputProps()} />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-sm text-gray-700">
                  <FileText size={16} className="text-brand-600" />
                  {file.name}
                </div>
              ) : (
                <div>
                  <Upload size={20} className="mx-auto mb-2 text-gray-400" />
                  <p className="text-sm text-gray-500">Drop a .docx file here or <span className="text-brand-600">browse</span></p>
                  <p className="text-xs text-gray-400 mt-1">Use {'{{field_name}}'} placeholders in your document</p>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
              {loading ? 'Uploading…' : 'Upload & detect fields'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)

  const load = () => api.get('/templates/').then(r => setTemplates(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const toggleActive = async tpl => {
    try {
      const { data } = await api.put(`/templates/${tpl.id}`, { active: !tpl.active })
      setTemplates(ts => ts.map(t => t.id === tpl.id ? data : t))
      toast.success(data.active ? 'Template activated' : 'Template deactivated')
    } catch { toast.error('Failed to update') }
  }

  const deleteTemplate = async tpl => {
    if (!confirm(`Delete "${tpl.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/templates/${tpl.id}`)
      setTemplates(ts => ts.filter(t => t.id !== tpl.id))
      toast.success('Template deleted')
    } catch { toast.error('Failed to delete') }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Templates</h1>
          <p className="text-sm text-gray-500 mt-0.5">Upload Word documents and configure form fields</p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn-primary">
          <Plus size={16} /> New template
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading…</div>
      ) : templates.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No templates yet</p>
          <p className="text-sm text-gray-400 mt-1">Upload a Word document to get started</p>
          <button onClick={() => setShowUpload(true)} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Upload template
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map(tpl => (
            <div key={tpl.id} className="card p-5 flex items-center gap-4">
              <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText size={18} className="text-brand-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{tpl.name}</p>
                  <span className={`badge ${tpl.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {tpl.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {tpl.description && <p className="text-sm text-gray-500 truncate mt-0.5">{tpl.description}</p>}
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><ClipboardList size={11}/> {tpl.fields?.length || 0} fields</span>
                  <span>{tpl.submission_count || 0} submissions</span>
                  <span>{tpl.original_filename}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button onClick={() => toggleActive(tpl)} title={tpl.active ? 'Deactivate' : 'Activate'}
                  className="text-gray-400 hover:text-brand-600 transition-colors">
                  {tpl.active ? <ToggleRight size={22} className="text-brand-600"/> : <ToggleLeft size={22}/>}
                </button>
                <Link to={`/templates/${tpl.id}/edit`}
                  className="btn-secondary !px-3 !py-1.5 text-xs">
                  <Pencil size={13}/> Edit fields
                </Link>
                <button onClick={() => deleteTemplate(tpl)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
                  <Trash2 size={16}/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onCreated={t => setTemplates(ts => [t, ...ts])}
        />
      )}
    </div>
  )
}
