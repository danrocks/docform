import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Upload, FileText, Pencil, Trash2, ToggleLeft, ToggleRight, ClipboardList, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'

function CreateModal({ onClose, onCreated, aiAvailable }) {
  const [tab, setTab] = useState('upload')
  // Upload state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState(null)
  const [interviewJson, setInterviewJson] = useState('')
  const [showJsonExample, setShowJsonExample] = useState(false)
  const [loading, setLoading] = useState(false)
  // AI state
  const [aiName, setAiName] = useState('')
  const [aiDescription, setAiDescription] = useState('')
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiLoading, setAiLoading] = useState(false)

  const onDrop = useCallback(accepted => { if (accepted[0]) setFile(accepted[0]) }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] }, maxFiles: 1
  })

  const handleUpload = async e => {
    e.preventDefault()
    if (!file) return toast.error('Please select a .docx file')
    if (!name.trim()) return toast.error('Please enter a template name')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('name', name)
      fd.append('description', description)
      fd.append('file', file)
      if (interviewJson.trim()) fd.append('interview_json', interviewJson.trim())
      const { data } = await api.post('/templates/', fd)
      toast.success(`Template created \u2014 ${data.fields.length} interview question(s) detected`)
      onCreated(data)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleAiGenerate = async e => {
    e.preventDefault()
    if (!aiName.trim()) return toast.error('Please enter a template name')
    if (!aiPrompt.trim()) return toast.error('Please enter a prompt')
    setAiLoading(true)
    try {
      const { data } = await api.post('/templates/generate', {
        name: aiName,
        description: aiDescription,
        prompt: aiPrompt,
      })
      toast.success(`Template generated \u2014 ${data.fields.length} interview question(s)`)
      onCreated(data)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed')
    } finally {
      setAiLoading(false)
    }
  }

  const jsonExample = `[
  {
    "key": "client_name",
    "label": "Client Name",
    "type": "string",
    "required": true,
    "placeholder": "Enter client name",
    "help_text": "Legal registered name",
    "config": { "max_length": 200 }
  },
  {
    "key": "contract_value",
    "label": "Contract Value",
    "type": "number",
    "required": true,
    "config": { "min": 0, "decimal_places": 2, "unit": "\u00a3" }
  },
  {
    "key": "start_date",
    "label": "Start Date",
    "type": "date",
    "required": true,
    "config": { "allow_past": false }
  },
  {
    "key": "payment_terms",
    "label": "Payment Terms",
    "type": "multiplechoice",
    "required": true,
    "config": { "options": ["Net 30", "Net 60", "Net 90"], "display_as": "radio" }
  }
]`

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Create template</h2>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-gray-100 rounded-lg p-0.5">
          <button onClick={() => setTab('upload')}
            className={`flex-1 text-sm font-medium py-2 px-3 rounded-md transition-colors ${tab === 'upload' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            <Upload size={14} className="inline mr-1.5 -mt-0.5"/> Upload
          </button>
          {aiAvailable && (
            <button onClick={() => setTab('ai')}
              className={`flex-1 text-sm font-medium py-2 px-3 rounded-md transition-colors ${tab === 'ai' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
              <Sparkles size={14} className="inline mr-1.5 -mt-0.5"/> AI Generate
            </button>
          )}
        </div>

        {tab === 'upload' && (
          <form onSubmit={handleUpload} className="space-y-4">
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
            <div>
              <div className="flex items-center justify-between">
                <label className="label">Interview definition (JSON)</label>
                <button type="button" onClick={() => setShowJsonExample(!showJsonExample)}
                  className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-0.5">
                  {showJsonExample ? <ChevronUp size={12}/> : <ChevronDown size={12}/>} Example
                </button>
              </div>
              {showJsonExample && (
                <pre className="text-xs bg-gray-50 border rounded p-3 mb-2 overflow-x-auto max-h-48 overflow-y-auto">{jsonExample}</pre>
              )}
              <textarea className="input resize-none font-mono text-xs" rows={4} value={interviewJson}
                onChange={e => setInterviewJson(e.target.value)}
                placeholder="Optional: paste a JSON array of interview questions" />
              <p className="text-xs text-gray-400 mt-1">Leave blank to auto-detect questions from {'{{placeholders}}'} &mdash; you can configure types and settings on the next screen.</p>
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center">
                {loading ? 'Uploading...' : 'Upload & detect questions'}
              </button>
            </div>
          </form>
        )}

        {tab === 'ai' && (
          <form onSubmit={handleAiGenerate} className="space-y-4">
            <div>
              <label className="label">Template name *</label>
              <input className="input" value={aiName} onChange={e => setAiName(e.target.value)} placeholder="e.g. Service Agreement" required />
            </div>
            <div>
              <label className="label">Description</label>
              <input className="input" value={aiDescription} onChange={e => setAiDescription(e.target.value)} placeholder="Optional description" />
            </div>
            <div>
              <label className="label">Prompt *</label>
              <textarea className="input resize-none" rows={5} value={aiPrompt}
                onChange={e => setAiPrompt(e.target.value)}
                placeholder="Describe the document you need. For example: Create a professional employment offer letter that includes position details, salary, benefits, start date, and standard terms and conditions." required />
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={aiLoading} className="btn-primary flex-1 justify-center">
                <Sparkles size={14}/> {aiLoading ? 'Generating...' : 'Generate with AI'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [aiAvailable, setAiAvailable] = useState(false)

  const load = () => api.get('/templates/').then(r => setTemplates(r.data)).finally(() => setLoading(false))
  useEffect(() => {
    load()
    api.get('/templates/ai-status').then(r => setAiAvailable(r.data.available)).catch(() => {})
  }, [])

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
          <p className="text-sm text-gray-500 mt-0.5">Create templates and configure interview questions</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus size={16} /> New template
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading...</div>
      ) : templates.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No templates yet</p>
          <p className="text-sm text-gray-400 mt-1">Upload a Word document or generate one with AI to get started</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mt-4 mx-auto">
            <Plus size={16} /> Create template
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
                  {tpl.generation_method === 'ai' && (
                    <span className="badge bg-purple-100 text-purple-700 flex items-center gap-0.5">
                      <Sparkles size={10}/> AI
                    </span>
                  )}
                </div>
                {tpl.description && <p className="text-sm text-gray-500 truncate mt-0.5">{tpl.description}</p>}
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><ClipboardList size={11}/> {tpl.fields?.length || 0} interview questions</span>
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
                  <Pencil size={13}/> Edit interview
                </Link>
                <button onClick={() => deleteTemplate(tpl)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
                  <Trash2 size={16}/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={t => { setTemplates(ts => [t, ...ts]); }}
          aiAvailable={aiAvailable}
        />
      )}
    </div>
  )
}
