import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { Plus, Trash2, GripVertical, ChevronLeft, Save } from 'lucide-react'

const FIELD_TYPES = [
  { value: 'text',     label: 'Short text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'date',     label: 'Date' },
  { value: 'number',   label: 'Number' },
  { value: 'select',   label: 'Dropdown' },
  { value: 'checkbox', label: 'Checkbox' },
]

function FieldRow({ field, index, onChange, onRemove }) {
  return (
    <div className="card p-4 flex gap-4 items-start group">
      <div className="mt-2 text-gray-300 cursor-grab">
        <GripVertical size={16}/>
      </div>
      <div className="flex-1 grid grid-cols-2 gap-3">
        <div>
          <label className="label text-xs">Field key (placeholder)</label>
          <input className="input text-sm font-mono" value={field.key}
            onChange={e => onChange(index, 'key', e.target.value)}
            placeholder="e.g. client_name" />
        </div>
        <div>
          <label className="label text-xs">Display label</label>
          <input className="input text-sm" value={field.label}
            onChange={e => onChange(index, 'label', e.target.value)}
            placeholder="e.g. Client Name" />
        </div>
        <div>
          <label className="label text-xs">Field type</label>
          <select className="input text-sm" value={field.type}
            onChange={e => onChange(index, 'type', e.target.value)}>
            {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label text-xs">Placeholder hint</label>
          <input className="input text-sm" value={field.placeholder || ''}
            onChange={e => onChange(index, 'placeholder', e.target.value)}
            placeholder="e.g. Enter client's full name" />
        </div>
        {field.type === 'select' && (
          <div className="col-span-2">
            <label className="label text-xs">Options (comma-separated)</label>
            <input className="input text-sm"
              value={(field.options || []).join(', ')}
              onChange={e => onChange(index, 'options', e.target.value.split(',').map(o => o.trim()).filter(Boolean))}
              placeholder="Option 1, Option 2, Option 3" />
          </div>
        )}
        <div className="col-span-2 flex items-center gap-2">
          <input type="checkbox" id={`req-${index}`} checked={!!field.required}
            onChange={e => onChange(index, 'required', e.target.checked)}
            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"/>
          <label htmlFor={`req-${index}`} className="text-sm text-gray-600 cursor-pointer">Required field</label>
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

  useEffect(() => {
    api.get(`/templates/${id}`).then(r => {
      setTemplate(r.data)
      setFields(r.data.fields || [])
    }).catch(() => toast.error('Template not found'))
  }, [id])

  const addField = () => {
    setFields(f => [...f, {
      key: '', label: '', type: 'text', required: false, placeholder: '', options: []
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
    if (invalid) return toast.error('All fields need a key and label')
    setSaving(true)
    try {
      await api.put(`/templates/${id}`, { fields })
      toast.success('Template saved')
      navigate('/templates')
    } catch { toast.error('Save failed') }
    finally { setSaving(false) }
  }

  if (!template) return <div className="text-center text-gray-400 py-16 text-sm">Loading…</div>

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate('/templates')}
          className="text-gray-400 hover:text-gray-600 transition-colors">
          <ChevronLeft size={20}/>
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Edit fields</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6 ml-8">
        {template.name} · {template.original_filename}
      </p>

      <div className="bg-brand-50 border border-brand-200 rounded-lg px-4 py-3 text-sm text-brand-800 mb-6">
        <strong>Tip:</strong> Field keys must match your <code className="font-mono bg-brand-100 px-1 rounded">{'{{placeholders}}'}</code> exactly.
        Auto-detected placeholders are shown below — add more or adjust types as needed.
      </div>

      <div className="space-y-3 mb-4">
        {fields.map((field, i) => (
          <FieldRow key={i} field={field} index={i} onChange={updateField} onRemove={removeField} />
        ))}
      </div>

      {fields.length === 0 && (
        <div className="card p-8 text-center text-gray-400 text-sm mb-4">
          No fields yet. Add fields below or use {'{{placeholders}}'} in your .docx to auto-detect them.
        </div>
      )}

      <div className="flex items-center justify-between pt-2">
        <button onClick={addField} className="btn-secondary">
          <Plus size={16}/> Add field
        </button>
        <div className="flex gap-3">
          <button onClick={() => navigate('/templates')} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            <Save size={16}/> {saving ? 'Saving…' : 'Save fields'}
          </button>
        </div>
      </div>
    </div>
  )
}
