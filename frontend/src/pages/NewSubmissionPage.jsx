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

  const isEmpty = v => v == null || (typeof v === 'string' && v.trim() === '')

  const validateComponent = (field, scope, errs, pathPrefix = '') => {
    const errKey = pathPrefix + field.id

    if (field.type === 'dialog') {
      ;(field.components || []).forEach(nested => validateComponent(nested, scope, errs, pathPrefix))
      return
    }

    if (field.type === 'repeat') {
      const items = Array.isArray(scope[field.id]) ? scope[field.id] : []
      if (field.required && items.length === 0) {
        errs[errKey] = 'This question is required'
        return
      }
      if (field.minItems && items.length < field.minItems)
        errs[errKey] = `At least ${field.minItems} item(s) required`
      if (field.maxItems != null && items.length > field.maxItems)
        errs[errKey] = `At most ${field.maxItems} item(s) allowed`
      items.forEach((item, idx) => {
        ;(field.components || []).forEach(nested =>
          validateComponent(nested, item || {}, errs, `${field.id}[${idx}].`)
        )
      })
      return
    }

    const val = scope[field.id]

    if (field.required) {
      if (field.type === 'choice' && field.allowMultiple) {
        if (!Array.isArray(val) || val.length === 0) {
          errs[errKey] = 'This question is required'
          return
        }
      } else if (isEmpty(val)) {
        errs[errKey] = 'This question is required'
        return
      }
    }

    if (isEmpty(val) && !(field.type === 'choice' && field.allowMultiple)) return

    if (field.type === 'string') {
      const s = String(val)
      if (field.minLength && s.length < field.minLength)
        errs[errKey] = `Must be at least ${field.minLength} characters`
      else if (field.maxLength && s.length > field.maxLength)
        errs[errKey] = `Must be at most ${field.maxLength} characters`
      else if (field.pattern) {
        try {
          if (!new RegExp(field.pattern).test(s))
            errs[errKey] = field.patternDescription || `Must match pattern ${field.pattern}`
        } catch { /* skip invalid regex */ }
      }
    } else if (field.type === 'number') {
      const n = parseFloat(val)
      if (isNaN(n)) errs[errKey] = 'Must be a valid number'
      else if (field.integerOnly && !Number.isInteger(n)) errs[errKey] = 'Must be a whole number'
      else if (field.min != null && n < field.min) errs[errKey] = `Must be at least ${field.min}`
      else if (field.max != null && n > field.max) errs[errKey] = `Must be at most ${field.max}`
    } else if (field.type === 'datetime') {
      const d = new Date(val)
      if (isNaN(d.getTime())) errs[errKey] = 'Must be a valid date'
      else {
        const today = new Date()
        today.setHours(0, 0, 0, 0)
        if (field.allowFuture === false && d > today) errs[errKey] = 'Date cannot be in the future'
        if (field.allowPast === false && d < today) errs[errKey] = 'Date cannot be in the past'
      }
    } else if (field.type === 'choice' && field.allowMultiple) {
      const vals = Array.isArray(val) ? val : [val]
      if (field.minSelections && vals.length < field.minSelections)
        errs[errKey] = `Select at least ${field.minSelections}`
      if (field.maxSelections != null && vals.length > field.maxSelections)
        errs[errKey] = `Select at most ${field.maxSelections}`
    }
  }

  const validate = () => {
    const errs = {}
    template.fields.forEach(f => validateComponent(f, data, errs))
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = e => {
    e.preventDefault()
    if (validate()) onSubmit()
  }

  const renderField = (field, value, onChange, errKeyPrefix = '') => {
    const errKey = errKeyPrefix + field.id
    const err = errors[errKey] ? 'border-red-400 focus:ring-red-400' : ''

    if (field.type === 'string') {
      if (field.multiline) {
        return (
          <div className="relative">
            <textarea id={field.id} value={value || ''}
              onChange={e => onChange(field.id, e.target.value)}
              className={`input resize-none ${err}`} rows={3}
              placeholder={field.placeholder || ''}
              maxLength={field.maxLength || undefined} />
            {field.maxLength && (
              <span className="text-xs text-gray-400 absolute bottom-2 right-3">
                {(value || '').length} / {field.maxLength}
              </span>
            )}
          </div>
        )
      }
      return (
        <div className="relative">
          <input type="text" id={field.id} value={value || ''}
            onChange={e => onChange(field.id, e.target.value)}
            className={`input ${err}`}
            placeholder={field.placeholder || ''}
            maxLength={field.maxLength || undefined} />
          {field.maxLength && (
            <span className="text-xs text-gray-400 absolute top-1/2 -translate-y-1/2 right-3">
              {(value || '').length} / {field.maxLength}
            </span>
          )}
        </div>
      )
    }

    if (field.type === 'number') {
      const step = field.step || (field.integerOnly ? 1 : field.decimalPlaces ? Math.pow(10, -field.decimalPlaces) : 'any')
      return (
        <div className="flex items-center gap-2">
          {field.prefix && <span className="text-sm text-gray-500 font-medium">{field.prefix}</span>}
          {field.unit && !field.prefix && <span className="text-sm text-gray-500 font-medium">{field.unit}</span>}
          <input type="number" id={field.id} value={value ?? ''}
            onChange={e => onChange(field.id, e.target.value)}
            className={`input flex-1 ${err}`}
            placeholder={field.placeholder || ''}
            min={field.min ?? undefined}
            max={field.max ?? undefined}
            step={step} />
          {field.suffix && <span className="text-sm text-gray-500 font-medium">{field.suffix}</span>}
        </div>
      )
    }

    if (field.type === 'datetime') {
      const inputType = field.includeTime ? 'datetime-local' : 'date'
      return (
        <input type={inputType} id={field.id} value={value || ''}
          onChange={e => onChange(field.id, e.target.value)}
          className={`input ${err}`}
          min={field.minDate || undefined}
          max={field.maxDate || undefined} />
      )
    }

    if (field.type === 'choice') {
      const options = field.options || []

      if (field.displayAs === 'radio') {
        return (
          <div className="space-y-1.5 mt-1">
            {options.map(opt => (
              <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name={field.id}
                  checked={value === opt.value}
                  onChange={() => onChange(field.id, opt.value)}
                  className="text-brand-600" />
                <span className="text-sm text-gray-700">{opt.label}</span>
              </label>
            ))}
          </div>
        )
      }

      if (field.displayAs === 'checkboxes' || (field.allowMultiple && field.displayAs !== 'dropdown')) {
        const selected = Array.isArray(value) ? value : []
        return (
          <div className="space-y-1.5 mt-1">
            {options.map(opt => (
              <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox"
                  checked={selected.includes(opt.value)}
                  onChange={e => {
                    const next = e.target.checked
                      ? [...selected, opt.value]
                      : selected.filter(s => s !== opt.value)
                    onChange(field.id, next)
                  }}
                  className="rounded border-gray-300 text-brand-600" />
                <span className="text-sm text-gray-700">{opt.label}</span>
              </label>
            ))}
          </div>
        )
      }

      // Default: dropdown
      if (field.allowMultiple) {
        const selected = Array.isArray(value) ? value : []
        return (
          <select multiple id={field.id} value={selected}
            onChange={e => {
              const opts = Array.from(e.target.selectedOptions, o => o.value)
              onChange(field.id, opts)
            }}
            className={`input ${err}`}>
            {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        )
      }
      return (
        <select id={field.id} value={value || ''}
          onChange={e => onChange(field.id, e.target.value)}
          className={`input ${err}`}>
          <option value="">Select...</option>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )
    }

    // Fallback
    return <input type="text" id={field.id} value={value || ''}
      onChange={e => onChange(field.id, e.target.value)}
      className={`input ${err}`} placeholder={field.placeholder || ''} />
  }

  const renderComponent = (field, scope, onScopeChange, errKeyPrefix = '') => {
    if (field.type === 'dialog') {
      return (
        <div key={field.id} className="border border-gray-200 rounded-lg p-4 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{field.title}</h3>
            {field.helpText && (
              <p className="text-xs text-gray-500 mt-0.5">{field.helpText}</p>
            )}
          </div>
          {(field.components || []).map(nested =>
            renderComponent(nested, scope, onScopeChange, errKeyPrefix)
          )}
        </div>
      )
    }

    if (field.type === 'repeat') {
      const items = Array.isArray(scope[field.id]) ? scope[field.id] : []
      const setItems = next => onScopeChange(field.id, next)
      const updateItem = (idx, key, v) => {
        const next = items.map((it, i) => (i === idx ? { ...it, [key]: v } : it))
        setItems(next)
      }
      const addItem = () => setItems([...items, {}])
      const removeItem = idx => setItems(items.filter((_, i) => i !== idx))
      const errKey = errKeyPrefix + field.id

      return (
        <div key={field.id}>
          <label className="label">
            {field.label}
            {field.required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
          {field.helpText && (
            <p className="text-xs text-gray-500 mt-0.5 mb-1">{field.helpText}</p>
          )}
          <div className="space-y-3">
            {items.map((item, idx) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-3 space-y-3 relative">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">#{idx + 1}</span>
                  <button type="button" onClick={() => removeItem(idx)}
                    className="text-xs text-red-500 hover:text-red-700">
                    Remove
                  </button>
                </div>
                {(field.components || []).map(nested =>
                  renderComponent(
                    nested,
                    item || {},
                    (k, v) => updateItem(idx, k, v),
                    `${field.id}[${idx}].`
                  )
                )}
              </div>
            ))}
            <button type="button" onClick={addItem}
              className="btn-secondary text-sm">
              + Add {field.label}
            </button>
          </div>
          {errors[errKey] && <p className="text-xs text-red-500 mt-1">{errors[errKey]}</p>}
        </div>
      )
    }

    const errKey = errKeyPrefix + field.id
    return (
      <div key={field.id}>
        <label htmlFor={field.id} className="label">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        {field.helpText && (
          <p className="text-xs text-gray-500 mt-0.5 mb-1">{field.helpText}</p>
        )}
        {renderField(field, scope[field.id], onScopeChange, errKeyPrefix)}
        {errors[errKey] && <p className="text-xs text-red-500 mt-1">{errors[errKey]}</p>}
      </div>
    )
  }

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
        <ChevronLeft size={15}/> Back
      </button>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{template.name}</h2>
      <p className="text-sm text-gray-500 mb-5">Complete the interview below</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {template.fields.map(field => renderComponent(field, data, onDataChange))}

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
