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
      <p className="text-sm text-gray-500 mb-5">Select the document you want to complete</p>
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
              <p className="text-xs text-gray-400 mt-0.5">{tpl.fields?.length || 0} interview questions</p>
            </div>
            <ChevronRight size={16} className="text-gray-300 group-hover:text-brand-500 transition-colors"/>
          </button>
        ))}
      </div>
    </div>
  )
}

// Step 2: complete interview
function FillForm({ template, data, context, onDataChange, onContextChange, onBack, onSubmit, submitting }) {
  const [errors, setErrors] = useState({})

  const validate = () => {
    const errs = {}
    template.fields.forEach(f => {
      const val = data[f.key]
      const config = f.config || {}

      // Required check
      if (f.required) {
        if (f.type === 'multiplechoice' && config.allow_multiple) {
          if (!val || !Array.isArray(val) || val.length === 0) {
            errs[f.key] = 'This question is required'
            return
          }
        } else if (!val || String(val).trim() === '') {
          errs[f.key] = 'This question is required'
          return
        }
      }

      if (!val || (typeof val === 'string' && val.trim() === '')) return

      // Type-specific validation
      if (f.type === 'string') {
        const s = String(val)
        if (config.min_length && s.length < config.min_length)
          errs[f.key] = `Must be at least ${config.min_length} characters`
        else if (config.max_length && s.length > config.max_length)
          errs[f.key] = `Must be at most ${config.max_length} characters`
        else if (config.pattern) {
          try {
            if (!new RegExp(config.pattern).test(s))
              errs[f.key] = config.pattern_description || `Must match pattern ${config.pattern}`
          } catch { /* skip invalid regex */ }
        }
      } else if (f.type === 'number') {
        const n = parseFloat(val)
        if (isNaN(n)) errs[f.key] = 'Must be a valid number'
        else if (config.integer_only && !Number.isInteger(n)) errs[f.key] = 'Must be a whole number'
        else if (config.min != null && n < config.min) errs[f.key] = `Must be at least ${config.min}`
        else if (config.max != null && n > config.max) errs[f.key] = `Must be at most ${config.max}`
      } else if (f.type === 'date') {
        const d = new Date(val)
        if (isNaN(d.getTime())) errs[f.key] = 'Must be a valid date'
        else {
          const today = new Date()
          today.setHours(0, 0, 0, 0)
          if (config.allow_future === false && d > today) errs[f.key] = 'Date cannot be in the future'
          if (config.allow_past === false && d < today) errs[f.key] = 'Date cannot be in the past'
        }
      } else if (f.type === 'multiplechoice' && config.allow_multiple) {
        const vals = Array.isArray(val) ? val : [val]
        if (config.min_selections && vals.length < config.min_selections)
          errs[f.key] = `Select at least ${config.min_selections}`
        if (config.max_selections != null && vals.length > config.max_selections)
          errs[f.key] = `Select at most ${config.max_selections}`
      }
    })
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (validate()) onSubmit()
  }

  const renderField = field => {
    const config = field.config || {}
    const err = errors[field.key] ? 'border-red-400 focus:ring-red-400' : ''

    if (field.type === 'string') {
      if (config.multiline) {
        return (
          <div className="relative">
            <textarea id={field.key} value={data[field.key] || ''}
              onChange={e => onDataChange(field.key, e.target.value)}
              className={`input resize-none ${err}`} rows={3}
              placeholder={field.placeholder || ''}
              maxLength={config.max_length || undefined} />
            {config.max_length && (
              <span className="text-xs text-gray-400 absolute bottom-2 right-3">
                {(data[field.key] || '').length} / {config.max_length}
              </span>
            )}
          </div>
        )
      }
      return (
        <div className="relative">
          <input type="text" id={field.key} value={data[field.key] || ''}
            onChange={e => onDataChange(field.key, e.target.value)}
            className={`input ${err}`}
            placeholder={field.placeholder || ''}
            maxLength={config.max_length || undefined} />
          {config.max_length && (
            <span className="text-xs text-gray-400 absolute top-1/2 -translate-y-1/2 right-3">
              {(data[field.key] || '').length} / {config.max_length}
            </span>
          )}
        </div>
      )
    }

    if (field.type === 'number') {
      const step = config.step || (config.integer_only ? 1 : config.decimal_places ? Math.pow(10, -config.decimal_places) : 'any')
      return (
        <div className="flex items-center gap-2">
          {config.unit && <span className="text-sm text-gray-500 font-medium">{config.unit}</span>}
          <input type="number" id={field.key} value={data[field.key] ?? ''}
            onChange={e => onDataChange(field.key, e.target.value)}
            className={`input flex-1 ${err}`}
            placeholder={field.placeholder || ''}
            min={config.min ?? undefined}
            max={config.max ?? undefined}
            step={step} />
        </div>
      )
    }

    if (field.type === 'date') {
      const inputType = config.include_time ? 'datetime-local' : 'date'
      return (
        <input type={inputType} id={field.key} value={data[field.key] || ''}
          onChange={e => onDataChange(field.key, e.target.value)}
          className={`input ${err}`}
          min={config.min_date || undefined}
          max={config.max_date || undefined} />
      )
    }

    if (field.type === 'multiplechoice') {
      const options = config.options || []

      if (config.display_as === 'radio') {
        return (
          <div className="space-y-1.5 mt-1">
            {options.map(opt => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name={field.key}
                  checked={data[field.key] === opt}
                  onChange={() => onDataChange(field.key, opt)}
                  className="text-brand-600" />
                <span className="text-sm text-gray-700">{opt}</span>
              </label>
            ))}
          </div>
        )
      }

      if (config.display_as === 'checkboxes' || (config.allow_multiple && config.display_as !== 'dropdown')) {
        const selected = Array.isArray(data[field.key]) ? data[field.key] : []
        return (
          <div className="space-y-1.5 mt-1">
            {options.map(opt => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={e => {
                    const next = e.target.checked
                      ? [...selected, opt]
                      : selected.filter(s => s !== opt)
                    onDataChange(field.key, next)
                  }}
                  className="rounded border-gray-300 text-brand-600" />
                <span className="text-sm text-gray-700">{opt}</span>
              </label>
            ))}
          </div>
        )
      }

      // Default: dropdown
      if (config.allow_multiple) {
        const selected = Array.isArray(data[field.key]) ? data[field.key] : []
        return (
          <select multiple id={field.key} value={selected}
            onChange={e => {
              const opts = Array.from(e.target.selectedOptions, o => o.value)
              onDataChange(field.key, opts)
            }}
            className={`input ${err}`}>
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        )
      }
      return (
        <select id={field.key} value={data[field.key] || ''}
          onChange={e => onDataChange(field.key, e.target.value)}
          className={`input ${err}`}>
          <option value="">Select...</option>
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      )
    }

    // Fallback
    return <input type="text" id={field.key} value={data[field.key] || ''}
      onChange={e => onDataChange(field.key, e.target.value)}
      className={`input ${err}`} placeholder={field.placeholder || ''} />
  }

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
        <ChevronLeft size={15}/> Back
      </button>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{template.name}</h2>
      <p className="text-sm text-gray-500 mb-5">Complete the interview below</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {template.fields.map(field => (
          <div key={field.key}>
            <label htmlFor={field.key} className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-0.5">*</span>}
            </label>
            {field.help_text && (
              <p className="text-xs text-gray-500 mt-0.5 mb-1">{field.help_text}</p>
            )}
            {renderField(field)}
            {errors[field.key] && <p className="text-xs text-red-500 mt-1">{errors[field.key]}</p>}
          </div>
        ))}

        <div className="pt-2 border-t border-gray-100">
          <label className="label">Interview context / notes</label>
          <textarea className="input resize-none" rows={2} value={context}
            onChange={e => onContextChange(e.target.value)}
            placeholder="Optional: describe the purpose or context of this interview" />
        </div>

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onBack} className="btn-secondary flex-1 justify-center">Back</button>
          <button type="submit" disabled={submitting} className="btn-primary flex-1 justify-center">
            {submitting ? 'Generating documents...' : 'Complete interview & generate documents'}
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
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Interview complete</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your documents are ready. You can download them from the submission page.
      </p>
      <div className="flex gap-3 justify-center">
        <button onClick={onNew} className="btn-secondary">New submission</button>
        <button onClick={() => navigate(`/submissions/${submission.id}`)} className="btn-primary">
          View submission &rarr;
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

  const steps = ['Choose template', 'Complete interview', 'Documents ready']

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
                  {done ? '\u2713' : n}
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
