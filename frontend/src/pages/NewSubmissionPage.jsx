import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import toast from 'react-hot-toast'
import { FileText, ChevronRight, ChevronLeft, CheckCircle } from 'lucide-react'

// Step 1: pick a template
function PickTemplate({ templates, onSelect }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">Choose a template</h2>
      <p className="text-sm text-gray-500 mb-5">Select the document you want to fill out</p>
      <div className="space-y-2">
        {templates.map(tpl => (
          <button key={tpl.id} onClick={() => onSelect(tpl)}
            className="w-full text-left card p-4 hover:border-brand-300 hover:shadow transition-all flex items-center gap-4 group">
            <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-brand-100 transition-colors">
              <FileText size={18} className="text-brand-600"/>
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900">{tpl.name}</p>
              {tpl.description && <p className="text-sm text-gray-500">{tpl.description}</p>}
              <p className="text-xs text-gray-400 mt-0.5">{tpl.fields?.length || 0} fields</p>
            </div>
            <ChevronRight size={16} className="text-gray-300 group-hover:text-brand-500 transition-colors"/>
          </button>
        ))}
      </div>
    </div>
  )
}

// Step 2: fill form fields
function FillForm({ template, data, context, onDataChange, onContextChange, onBack, onSubmit, submitting }) {
  const [errors, setErrors] = useState({})

  const validate = () => {
    const errs = {}
    template.fields.filter(f => f.required).forEach(f => {
      if (!data[f.key] || String(data[f.key]).trim() === '') errs[f.key] = 'This field is required'
    })
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (validate()) onSubmit()
  }

  const renderField = field => {
    const commonProps = {
      id: field.key,
      value: data[field.key] || '',
      onChange: e => onDataChange(field.key, e.target.value),
      className: `input ${errors[field.key] ? 'border-red-400 focus:ring-red-400' : ''}`,
      placeholder: field.placeholder || '',
    }
    switch (field.type) {
      case 'textarea': return <textarea {...commonProps} rows={3} className={`${commonProps.className} resize-none`}/>
      case 'date':     return <input {...commonProps} type="date"/>
      case 'number':   return <input {...commonProps} type="number"/>
      case 'checkbox': return (
        <div className="flex items-center gap-2 mt-1">
          <input type="checkbox" id={field.key}
            checked={!!data[field.key]}
            onChange={e => onDataChange(field.key, e.target.checked)}
            className="rounded border-gray-300 text-brand-600"/>
          <label htmlFor={field.key} className="text-sm text-gray-700">{field.label}</label>
        </div>
      )
      case 'select': return (
        <select {...commonProps}>
          <option value="">Select…</option>
          {(field.options || []).map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      )
      default: return <input {...commonProps} type="text"/>
    }
  }

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
        <ChevronLeft size={15}/> Back
      </button>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{template.name}</h2>
      <p className="text-sm text-gray-500 mb-5">Fill in all required fields below</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {template.fields.map(field => (
          <div key={field.key}>
            {field.type !== 'checkbox' && (
              <label htmlFor={field.key} className="label">
                {field.label}
                {field.required && <span className="text-red-500 ml-0.5">*</span>}
              </label>
            )}
            {renderField(field)}
            {errors[field.key] && <p className="text-xs text-red-500 mt-1">{errors[field.key]}</p>}
          </div>
        ))}

        <div className="pt-2 border-t border-gray-100">
          <label className="label">Submission context / notes</label>
          <textarea className="input resize-none" rows={2} value={context}
            onChange={e => onContextChange(e.target.value)}
            placeholder="Optional: describe the purpose or context of this submission" />
        </div>

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onBack} className="btn-secondary flex-1 justify-center">Back</button>
          <button type="submit" disabled={submitting} className="btn-primary flex-1 justify-center">
            {submitting ? 'Generating documents…' : 'Submit & generate documents'}
          </button>
        </div>
      </form>
    </div>
  )
}

// Step 3: success
function Success({ submission, onNew }) {
  const navigate = useNavigate()
  return (
    <div className="text-center py-6">
      <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <CheckCircle size={28} className="text-green-600"/>
      </div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Submission complete</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your documents are ready. You can download them from the submission page.
      </p>
      <div className="flex gap-3 justify-center">
        <button onClick={onNew} className="btn-secondary">New submission</button>
        <button onClick={() => navigate(`/submissions/${submission.id}`)} className="btn-primary">
          View submission →
        </button>
      </div>
    </div>
  )
}

export default function NewSubmissionPage() {
  const [templates, setTemplates] = useState([])
  const [step, setStep] = useState(1)
  const [selected, setSelected] = useState(null)
  const [formData, setFormData] = useState({})
  const [context, setContext] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submission, setSubmission] = useState(null)

  useEffect(() => {
    api.get('/templates/').then(r => setTemplates(r.data.filter(t => t.active)))
      .catch(() => toast.error('Failed to load templates'))
  }, [])

  const reset = () => { setStep(1); setSelected(null); setFormData({}); setContext(''); setSubmission(null) }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const { data } = await api.post('/submissions/', {
        template_id: selected.id,
        data: formData,
        context,
      })
      setSubmission(data)
      setStep(3)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  const steps = ['Select template', 'Fill in form', 'Download documents']

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">New submission</h1>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {steps.map((label, i) => {
          const n = i + 1
          const done = step > n
          const active = step === n
          return (
            <div key={n} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 text-sm font-medium ${active ? 'text-brand-700' : done ? 'text-green-600' : 'text-gray-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  active ? 'bg-brand-600 text-white' : done ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
                }`}>
                  {done ? '✓' : n}
                </div>
                {label}
              </div>
              {i < steps.length - 1 && <div className="w-8 h-px bg-gray-200 mx-1"/>}
            </div>
          )
        })}
      </div>

      <div className="card p-6 max-w-2xl">
        {step === 1 && (
          templates.length === 0
            ? <div className="text-center py-8 text-gray-400 text-sm">No active templates available. Ask an admin to create one.</div>
            : <PickTemplate templates={templates} onSelect={t => { setSelected(t); setFormData({}); setStep(2) }} />
        )}
        {step === 2 && selected && (
          <FillForm
            template={selected}
            data={formData}
            context={context}
            onDataChange={(k, v) => setFormData(d => ({ ...d, [k]: v }))}
            onContextChange={setContext}
            onBack={() => setStep(1)}
            onSubmit={handleSubmit}
            submitting={submitting}
          />
        )}
        {step === 3 && submission && <Success submission={submission} onNew={reset} />}
      </div>
    </div>
  )
}
