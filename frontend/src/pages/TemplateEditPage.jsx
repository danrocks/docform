import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Trash2, GripVertical, ChevronLeft, Save, ChevronDown, ChevronUp, Sparkles, RefreshCw } from 'lucide-react'

const FIELD_TYPES = [
  { value: 'string',         label: 'Text' },
  { value: 'number',         label: 'Number' },
  { value: 'date',           label: 'Date' },
  { value: 'multiplechoice', label: 'Multiple choice' },
]

const DEFAULT_CONFIGS = {
  string: { min_length: 0, max_length: null, multiline: false, pattern: null, pattern_description: null },
  number: { min: null, max: null, integer_only: false, decimal_places: null, step: null, unit: null },
  date: { format: 'YYYY-MM-DD', min_date: null, max_date: null, allow_future: true, allow_past: true, include_time: false },
  multiplechoice: { options: [], allow_multiple: false, min_selections: 0, max_selections: null, display_as: 'dropdown' },
}

function configSummary(type, config) {
  if (!config) return ''
  const parts = []
  if (type === 'string') {
    if (config.max_length) parts.push(`Max ${config.max_length} chars`)
    parts.push(config.multiline ? 'Multi-line' : 'Single line')
    if (config.pattern) parts.push('Has pattern')
  } else if (type === 'number') {
    if (config.integer_only) parts.push('Whole number')
    if (config.min != null) parts.push(`Min ${config.min}`)
    if (config.max != null) parts.push(`Max ${config.max}`)
    if (config.unit) parts.push(`Unit: ${config.unit}`)
  } else if (type === 'date') {
    if (!config.allow_past) parts.push('No past dates')
    if (!config.allow_future) parts.push('No future dates')
    if (config.include_time) parts.push('Includes time')
  } else if (type === 'multiplechoice') {
    parts.push(`${(config.options || []).length} options`)
    parts.push(config.display_as || 'dropdown')
    if (config.allow_multiple) parts.push('Multi-select')
  }
  return parts.join(', ')
}

function TypeConfig({ type, config, onChange }) {
  if (!config) return null
  const update = (key, value) => onChange({ ...config, [key]: value })

  if (type === 'string') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <div>
        <label className="label text-xs">Min length</label>
        <input type="number" className="input text-sm" value={config.min_length || 0}
          onChange={e => update('min_length', parseInt(e.target.value) || 0)} min={0} />
      </div>
      <div>
        <label className="label text-xs">Max length</label>
        <input type="number" className="input text-sm" value={config.max_length || ''}
          onChange={e => update('max_length', e.target.value ? parseInt(e.target.value) : null)}
          placeholder="No limit" />
      </div>
      <div className="col-span-2 flex items-center gap-2">
        <input type="checkbox" checked={!!config.multiline}
          onChange={e => update('multiline', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Allow multi-line text</span>
      </div>
      <div>
        <label className="label text-xs">Validation pattern (regex)</label>
        <input className="input text-sm font-mono" value={config.pattern || ''}
          onChange={e => update('pattern', e.target.value || null)}
          placeholder="e.g. ^[A-Z].*" />
      </div>
      <div>
        <label className="label text-xs">Pattern description</label>
        <input className="input text-sm" value={config.pattern_description || ''}
          onChange={e => update('pattern_description', e.target.value || null)}
          placeholder="e.g. Must start with uppercase" />
      </div>
    </div>
  )

  if (type === 'number') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <div>
        <label className="label text-xs">Min value</label>
        <input type="number" className="input text-sm" value={config.min ?? ''}
          onChange={e => update('min', e.target.value !== '' ? parseFloat(e.target.value) : null)}
          placeholder="No minimum" />
      </div>
      <div>
        <label className="label text-xs">Max value</label>
        <input type="number" className="input text-sm" value={config.max ?? ''}
          onChange={e => update('max', e.target.value !== '' ? parseFloat(e.target.value) : null)}
          placeholder="No maximum" />
      </div>
      <div className="col-span-2 flex items-center gap-2">
        <input type="checkbox" checked={!!config.integer_only}
          onChange={e => update('integer_only', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Must be a whole number</span>
      </div>
      <div>
        <label className="label text-xs">Decimal places</label>
        <input type="number" className="input text-sm" value={config.decimal_places ?? ''}
          onChange={e => update('decimal_places', e.target.value !== '' ? parseInt(e.target.value) : null)}
          placeholder="Any" disabled={config.integer_only} min={0} />
      </div>
      <div>
        <label className="label text-xs">Step</label>
        <input type="number" className="input text-sm" value={config.step ?? ''}
          onChange={e => update('step', e.target.value !== '' ? parseFloat(e.target.value) : null)}
          placeholder="Any" />
      </div>
      <div className="col-span-2">
        <label className="label text-xs">Display unit (e.g. pounds, %, kg)</label>
        <input className="input text-sm" value={config.unit || ''}
          onChange={e => update('unit', e.target.value || null)}
          placeholder="e.g. kg" />
      </div>
    </div>
  )

  if (type === 'date') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={config.allow_past !== false}
          onChange={e => update('allow_past', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Allow past dates</span>
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={config.allow_future !== false}
          onChange={e => update('allow_future', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Allow future dates</span>
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={!!config.include_time}
          onChange={e => update('include_time', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Include time</span>
      </div>
      <div />
      <div>
        <label className="label text-xs">Min date</label>
        <input type="date" className="input text-sm" value={config.min_date || ''}
          onChange={e => update('min_date', e.target.value || null)} />
      </div>
      <div>
        <label className="label text-xs">Max date</label>
        <input type="date" className="input text-sm" value={config.max_date || ''}
          onChange={e => update('max_date', e.target.value || null)} />
      </div>
    </div>
  )

  if (type === 'multiplechoice') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <div className="col-span-2">
        <label className="label text-xs">Options (comma-separated)</label>
        <input className="input text-sm"
          value={(config.options || []).join(', ')}
          onChange={e => update('options', e.target.value.split(',').map(o => o.trim()).filter(Boolean))}
          placeholder="Option 1, Option 2, Option 3" />
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={!!config.allow_multiple}
          onChange={e => update('allow_multiple', e.target.checked)}
          className="rounded border-gray-300 text-brand-600" />
        <span className="text-sm text-gray-600">Allow multiple selections</span>
      </div>
      <div>
        <label className="label text-xs">Display as</label>
        <select className="input text-sm" value={config.display_as || 'dropdown'}
          onChange={e => update('display_as', e.target.value)}>
          <option value="dropdown">Dropdown</option>
          <option value="radio">Radio buttons</option>
          <option value="checkboxes">Checkboxes</option>
        </select>
      </div>
      {config.allow_multiple && (
        <>
          <div>
            <label className="label text-xs">Min selections</label>
            <input type="number" className="input text-sm" value={config.min_selections || 0}
              onChange={e => update('min_selections', parseInt(e.target.value) || 0)} min={0} />
          </div>
          <div>
            <label className="label text-xs">Max selections</label>
            <input type="number" className="input text-sm" value={config.max_selections ?? ''}
              onChange={e => update('max_selections', e.target.value !== '' ? parseInt(e.target.value) : null)}
              placeholder="No limit" />
          </div>
        </>
      )}
    </div>
  )

  return null
}

function FieldRow({ field, index, onChange, onRemove }) {
  const [expanded, setExpanded] = useState(false)

  const handleTypeChange = (newType) => {
    onChange(index, 'type', newType)
    onChange(index, 'config', { ...DEFAULT_CONFIGS[newType] })
  }

  return (
    <div className="card p-4 flex gap-4 items-start group">
      <div className="mt-2 text-gray-300 cursor-grab">
        <GripVertical size={16}/>
      </div>
      <div className="flex-1 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label text-xs">Question key (placeholder)</label>
            <input className="input text-sm font-mono" value={field.key}
              onChange={e => onChange(index, 'key', e.target.value)}
              placeholder="e.g. client_name" />
          </div>
          <div>
            <label className="label text-xs">Question text</label>
            <input className="input text-sm" value={field.label}
              onChange={e => onChange(index, 'label', e.target.value)}
              placeholder="e.g. Client Name" />
          </div>
          <div>
            <label className="label text-xs">Answer type</label>
            <select className="input text-sm" value={field.type}
              onChange={e => handleTypeChange(e.target.value)}>
              {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs">Placeholder hint</label>
            <input className="input text-sm" value={field.placeholder || ''}
              onChange={e => onChange(index, 'placeholder', e.target.value)}
              placeholder="e.g. Enter client's full name" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs">Help text / guidance for interviewee</label>
            <input className="input text-sm" value={field.help_text || ''}
              onChange={e => onChange(index, 'help_text', e.target.value)}
              placeholder="e.g. Use the client's legal registered name" />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <input type="checkbox" id={`req-${index}`} checked={!!field.required}
              onChange={e => onChange(index, 'required', e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"/>
            <label htmlFor={`req-${index}`} className="text-sm text-gray-600 cursor-pointer">Required question</label>
          </div>
        </div>

        {/* Collapsible type settings */}
        <div className="border-t border-gray-100 pt-2">
          <button type="button" onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors">
            {expanded ? <ChevronUp size={13}/> : <ChevronDown size={13}/>}
            <span className="font-medium">Type settings</span>
            {!expanded && field.config && (
              <span className="text-gray-400 ml-1">
                {configSummary(field.type, field.config)}
              </span>
            )}
          </button>
          {expanded && (
            <TypeConfig type={field.type} config={field.config || DEFAULT_CONFIGS[field.type]}
              onChange={cfg => onChange(index, 'config', cfg)} />
          )}
        </div>
      </div>
      <button onClick={() => onRemove(index)}
        className="mt-1 text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">
        <Trash2 size={16}/>
      </button>
    </div>
  )
}

export default function TemplateEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [template, setTemplate] = useState(null)
  const [fields, setFields] = useState([])
  const [saving, setSaving] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)
  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenPrompt, setRegenPrompt] = useState('')
  const [regenerating, setRegenerating] = useState(false)

  useEffect(() => {
    api.get(`/templates/${id}`).then(r => {
      setTemplate(r.data)
      setFields(r.data.fields || [])
      if (r.data.original_prompt) setRegenPrompt(r.data.original_prompt)
    }).catch(() => toast.error('Template not found'))
  }, [id])

  const addField = () => {
    setFields(f => [...f, {
      key: '', label: '', type: 'string', required: false, placeholder: '', help_text: '',
      config: { min_length: 0, max_length: null, multiline: false, pattern: null, pattern_description: null }
    }])
  }

  const updateField = (index, key, value) => {
    setFields(f => f.map((field, i) => i === index ? { ...field, [key]: value } : field))
  }

  const removeField = index => {
    setFields(f => f.filter((_, i) => i !== index))
  }

  const save = async () => {
    const invalid = fields.find(f => !f.key.trim() || !f.label.trim())
    if (invalid) return toast.error('All questions need a key and label')
    setSaving(true)
    try {
      await api.put(`/templates/${id}`, { fields })
      toast.success('Interview saved')
      navigate('/templates')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed')
    }
    finally { setSaving(false) }
  }

  const handleRegenerate = async () => {
    if (!regenPrompt.trim()) return toast.error('Please enter a prompt')
    if (!confirm('This will overwrite the current document and all interview questions. Continue?')) return
    setRegenerating(true)
    try {
      const { data } = await api.post(`/templates/${id}/regenerate`, { prompt: regenPrompt })
      setTemplate(data)
      setFields(data.fields || [])
      setShowRegenModal(false)
      toast.success('Template regenerated with AI')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Regeneration failed')
    }
    finally { setRegenerating(false) }
  }

  if (!template) return <div className="text-center text-gray-400 py-16 text-sm">Loading...</div>

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate('/templates')}
          className="text-gray-400 hover:text-gray-600 transition-colors">
          <ChevronLeft size={20}/>
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Edit interview</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6 ml-8">
        {template.name} &middot; {template.original_filename}
      </p>

      {/* AI prompt info box */}
      {template.generation_method === 'ai' && template.original_prompt && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-3 text-sm text-purple-800 mb-4">
          <button onClick={() => setShowPrompt(!showPrompt)}
            className="flex items-center gap-2 font-medium w-full text-left">
            <Sparkles size={14}/>
            AI-generated template
            {showPrompt ? <ChevronUp size={14} className="ml-auto"/> : <ChevronDown size={14} className="ml-auto"/>}
          </button>
          {showPrompt && (
            <div className="mt-2 bg-white rounded p-3 text-gray-700 text-sm whitespace-pre-wrap border border-purple-100">
              {template.original_prompt}
            </div>
          )}
          <button onClick={() => setShowRegenModal(true)}
            className="mt-2 text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1">
            <RefreshCw size={12}/> Regenerate with AI
          </button>
        </div>
      )}

      <div className="bg-brand-50 border border-brand-200 rounded-lg px-4 py-3 text-sm text-brand-800 mb-6">
        <strong>Tip:</strong> Question keys must match your <code className="font-mono bg-brand-100 px-1 rounded">{'{{placeholders}}'}</code> exactly.
        Auto-detected placeholders are shown below &mdash; add more or adjust types as needed.
      </div>

      <div className="space-y-3 mb-4">
        {fields.map((field, i) => (
          <FieldRow key={i} field={field} index={i} onChange={updateField} onRemove={removeField} />
        ))}
      </div>

      {fields.length === 0 && (
        <div className="card p-8 text-center text-gray-400 text-sm mb-4">
          No interview questions yet. Add questions below or use {'{{placeholders}}'} in your .docx to auto-detect them.
        </div>
      )}

      <div className="flex items-center justify-between pt-2">
        <button onClick={addField} className="btn-secondary">
          <Plus size={16}/> Add question
        </button>
        <div className="flex gap-3">
          <button onClick={() => navigate('/templates')} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            <Save size={16}/> {saving ? 'Saving...' : 'Save interview'}
          </button>
        </div>
      </div>

      {/* Regenerate modal */}
      {showRegenModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="card w-full max-w-lg p-6">
            <h3 className="font-semibold text-gray-900 mb-1">Regenerate with AI</h3>
            <p className="text-sm text-gray-500 mb-4">
              This will overwrite the current document and all interview questions.
            </p>
            <textarea className="input resize-none mb-4" rows={6}
              value={regenPrompt} onChange={e => setRegenPrompt(e.target.value)}
              placeholder="Describe the document you need..." />
            <div className="flex gap-3">
              <button onClick={() => setShowRegenModal(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button onClick={handleRegenerate} disabled={regenerating}
                className="btn-primary flex-1 justify-center">
                <Sparkles size={14}/> {regenerating ? 'Generating...' : 'Regenerate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
