import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import api from '../api'
import toast from 'react-hot-toast'
import {
  Plus, Trash2, GripVertical, ChevronLeft, Save, ChevronDown, ChevronUp,
  Sparkles, RefreshCw, Type, Hash, Calendar, ListChecks, Repeat, FolderTree,
  FileText, Clock
} from 'lucide-react'

const COMPONENT_TYPES = [
  { value: 'string',   label: 'Text',          icon: Type },
  { value: 'number',   label: 'Number',        icon: Hash },
  { value: 'datetime', label: 'Date / time',   icon: Calendar },
  { value: 'choice',   label: 'Choice',        icon: ListChecks },
  { value: 'repeat',   label: 'Repeat group',  icon: Repeat },
  { value: 'dialog',   label: 'Dialog (group)', icon: FolderTree },
]

const TYPE_LABEL = Object.fromEntries(COMPONENT_TYPES.map(t => [t.value, t.label]))
const TYPE_ICON = Object.fromEntries(COMPONENT_TYPES.map(t => [t.value, t.icon]))

// Default per-type body — only includes the discriminator + minimum required
// fields. Optional fields are added when the user toggles them on.
function defaultComponent(type) {
  switch (type) {
    case 'string':
      return { type, id: '', label: '', required: false }
    case 'number':
      return { type, id: '', label: '', required: false }
    case 'datetime':
      return { type, id: '', label: '', required: false }
    case 'choice':
      return { type, id: '', label: '', required: false, options: [{ value: '', label: '' }] }
    case 'repeat':
      return { type, id: '', label: '', components: [{ type: 'string', id: '', label: '' }] }
    case 'dialog':
      return { type, id: '', title: '', components: [{ type: 'string', id: '', label: '' }] }
    default:
      return { type, id: '', label: '' }
  }
}

// When the user switches a component's type, preserve fields that still make
// sense (id, label/title, required, helpText) and reset the rest to that
// type's defaults.
function convertComponent(prev, newType) {
  const next = defaultComponent(newType)
  if (prev.id) next.id = prev.id
  if (prev.helpText) next.helpText = prev.helpText
  if (newType === 'dialog') {
    next.title = prev.title || prev.label || ''
  } else if (prev.label != null) {
    next.label = prev.label
  } else if (prev.title) {
    next.label = prev.title
  }
  if (newType !== 'repeat' && newType !== 'dialog' && prev.required != null) {
    next.required = !!prev.required
  }
  return next
}

function configSummary(c) {
  if (!c) return ''
  const parts = []
  if (c.type === 'string') {
    if (c.maxLength) parts.push(`Max ${c.maxLength} chars`)
    parts.push(c.multiline ? 'Multi-line' : 'Single line')
    if (c.pattern) parts.push('Has pattern')
    if (c.format && c.format !== 'text') parts.push(c.format)
  } else if (c.type === 'number') {
    if (c.integerOnly) parts.push('Whole number')
    if (c.min != null) parts.push(`Min ${c.min}`)
    if (c.max != null) parts.push(`Max ${c.max}`)
    if (c.unit) parts.push(`Unit: ${c.unit}`)
    if (c.expression) parts.push('Computed')
  } else if (c.type === 'datetime') {
    if (c.includeTime) parts.push('Includes time')
    if (c.allowPast === false) parts.push('No past dates')
    if (c.allowFuture === false) parts.push('No future dates')
  } else if (c.type === 'choice') {
    parts.push(`${(c.options || []).length} options`)
    parts.push(c.displayAs || 'dropdown')
    if (c.allowMultiple) parts.push('Multi-select')
  } else if (c.type === 'repeat') {
    parts.push(`${(c.components || []).length} sub-fields`)
    if (c.displayAs) parts.push(c.displayAs)
    if (c.minItems != null) parts.push(`Min ${c.minItems} items`)
    if (c.maxItems != null) parts.push(`Max ${c.maxItems} items`)
  } else if (c.type === 'dialog') {
    parts.push(`${(c.components || []).length} sub-fields`)
  }
  return parts.join(', ')
}

// Update or remove a single property without mutating the input. Empty strings
// and null values delete the property so we don't end up writing things like
// `"pattern": ""` to the interview JSON.
function setProp(comp, key, value) {
  const next = { ...comp }
  if (value === '' || value === null || value === undefined) {
    delete next[key]
  } else {
    next[key] = value
  }
  return next
}

function TextInput({ label, value, onChange, placeholder, mono, ...rest }) {
  return (
    <div>
      <label className="label text-xs">{label}</label>
      <input
        className={`input text-sm ${mono ? 'font-mono' : ''}`}
        value={value ?? ''}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        {...rest}
      />
    </div>
  )
}

function NumberInput({ label, value, onChange, placeholder, integer, ...rest }) {
  return (
    <div>
      <label className="label text-xs">{label}</label>
      <input
        type="number"
        className="input text-sm"
        value={value ?? ''}
        onChange={e => {
          if (e.target.value === '') return onChange(null)
          const n = integer ? parseInt(e.target.value, 10) : parseFloat(e.target.value)
          onChange(Number.isNaN(n) ? null : n)
        }}
        placeholder={placeholder}
        {...rest}
      />
    </div>
  )
}

function Checkbox({ label, checked, onChange, className = '' }) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${className}`}>
      <input
        type="checkbox"
        checked={!!checked}
        onChange={e => onChange(e.target.checked)}
        className="rounded border-gray-300 text-brand-600"
      />
      <span className="text-sm text-gray-600">{label}</span>
    </label>
  )
}

function Select({ label, value, onChange, options }) {
  return (
    <div>
      <label className="label text-xs">{label}</label>
      <select
        className="input text-sm"
        value={value ?? ''}
        onChange={e => onChange(e.target.value)}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

// Type-specific settings panel. `update(key, value)` writes one prop on the
// component (empty/null deletes it).
function TypeSettings({ component, update }) {
  const c = component

  if (c.type === 'string') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <NumberInput label="Min length" value={c.minLength} onChange={v => update('minLength', v)} integer min={0} placeholder="0" />
      <NumberInput label="Max length" value={c.maxLength} onChange={v => update('maxLength', v)} integer min={1} placeholder="No limit" />
      <Checkbox className="col-span-2" label="Allow multi-line text" checked={c.multiline} onChange={v => update('multiline', v || null)} />
      <Select
        label="Format"
        value={c.format || 'text'}
        onChange={v => update('format', v === 'text' ? null : v)}
        options={[
          { value: 'text', label: 'Text' },
          { value: 'email', label: 'Email' },
          { value: 'phone', label: 'Phone' },
          { value: 'url', label: 'URL' },
        ]}
      />
      <TextInput label="Placeholder" value={c.placeholder} onChange={v => update('placeholder', v)} placeholder="e.g. Enter name" />
      <TextInput label="Validation pattern (regex)" mono value={c.pattern} onChange={v => update('pattern', v)} placeholder="e.g. ^[A-Z].*" />
      <TextInput label="Pattern description" value={c.patternDescription} onChange={v => update('patternDescription', v)} placeholder="e.g. Must start with uppercase" />
      <TextInput label="Default value" value={c.defaultValue} onChange={v => update('defaultValue', v)} placeholder="(optional)" />
    </div>
  )

  if (c.type === 'number') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <NumberInput label="Min value" value={c.min} onChange={v => update('min', v)} placeholder="No minimum" />
      <NumberInput label="Max value" value={c.max} onChange={v => update('max', v)} placeholder="No maximum" />
      <Checkbox className="col-span-2" label="Must be a whole number" checked={c.integerOnly} onChange={v => update('integerOnly', v || null)} />
      <NumberInput label="Decimal places" value={c.decimalPlaces} onChange={v => update('decimalPlaces', v)} integer min={0} placeholder="Any" />
      <NumberInput label="Step" value={c.step} onChange={v => update('step', v)} placeholder="Any" />
      <TextInput label="Unit" value={c.unit} onChange={v => update('unit', v)} placeholder="e.g. kg" />
      <TextInput label="Prefix" value={c.prefix} onChange={v => update('prefix', v)} placeholder="e.g. £" />
      <TextInput label="Suffix" value={c.suffix} onChange={v => update('suffix', v)} placeholder="e.g. %" />
      <div className="col-span-2">
        <label className="label text-xs">Expression (auto-calculated)</label>
        <input
          className="input text-sm font-mono"
          value={c.expression ?? ''}
          onChange={e => update('expression', e.target.value)}
          placeholder="e.g. subtotal + vat"
        />
        <p className="text-xs text-gray-400 mt-1">
          When set, this field is computed from other fields and is not editable in the form.
        </p>
      </div>
    </div>
  )

  if (c.type === 'datetime') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <Checkbox label="Include time" checked={c.includeTime} onChange={v => update('includeTime', v || null)} />
      <div />
      <Checkbox label="Allow past dates" checked={c.allowPast !== false} onChange={v => update('allowPast', v ? null : false)} />
      <Checkbox label="Allow future dates" checked={c.allowFuture !== false} onChange={v => update('allowFuture', v ? null : false)} />
      <div>
        <label className="label text-xs">Min date</label>
        <input type="date" className="input text-sm" value={c.minDate || ''}
          onChange={e => update('minDate', e.target.value || null)} />
      </div>
      <div>
        <label className="label text-xs">Max date</label>
        <input type="date" className="input text-sm" value={c.maxDate || ''}
          onChange={e => update('maxDate', e.target.value || null)} />
      </div>
      <TextInput label="Default value" value={c.defaultValue} onChange={v => update('defaultValue', v)} placeholder='e.g. "today" or 2024-01-01' />
    </div>
  )

  if (c.type === 'choice') {
    const options = c.options || []
    const setOption = (i, key, value) => {
      const next = options.map((o, idx) => idx === i ? { ...o, [key]: value } : o)
      update('options', next)
    }
    const addOption = () => update('options', [...options, { value: '', label: '' }])
    const removeOption = i => update('options', options.filter((_, idx) => idx !== i))

    return (
      <div className="grid grid-cols-2 gap-3 mt-2">
        <div className="col-span-2">
          <label className="label text-xs">Options</label>
          <div className="space-y-1.5">
            {options.map((opt, i) => (
              <div key={i} className="flex gap-2">
                <input className="input text-sm font-mono flex-1" placeholder="value"
                  value={opt.value || ''} onChange={e => setOption(i, 'value', e.target.value)} />
                <input className="input text-sm flex-1" placeholder="Label shown to user"
                  value={opt.label || ''} onChange={e => setOption(i, 'label', e.target.value)} />
                <button type="button" onClick={() => removeOption(i)}
                  className="text-gray-300 hover:text-red-500 px-1" title="Remove option">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
          <button type="button" onClick={addOption}
            className="mt-2 text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
            <Plus size={12} /> Add option
          </button>
        </div>
        <Select
          label="Display as"
          value={c.displayAs || 'dropdown'}
          onChange={v => update('displayAs', v === 'dropdown' ? null : v)}
          options={[
            { value: 'dropdown', label: 'Dropdown' },
            { value: 'radio', label: 'Radio buttons' },
            { value: 'checkboxes', label: 'Checkboxes' },
            { value: 'toggle', label: 'Toggle' },
          ]}
        />
        <Checkbox label="Allow multiple selections" checked={c.allowMultiple} onChange={v => update('allowMultiple', v || null)} />
        {c.allowMultiple && (
          <>
            <NumberInput label="Min selections" value={c.minSelections} onChange={v => update('minSelections', v)} integer min={0} placeholder="0" />
            <NumberInput label="Max selections" value={c.maxSelections} onChange={v => update('maxSelections', v)} integer min={1} placeholder="No limit" />
          </>
        )}
        <Checkbox label="Allow 'other' free-text option" checked={c.allowOther} onChange={v => update('allowOther', v || null)} />
      </div>
    )
  }

  if (c.type === 'repeat') return (
    <div className="grid grid-cols-2 gap-3 mt-2">
      <NumberInput label="Min items" value={c.minItems} onChange={v => update('minItems', v)} integer min={0} placeholder="0" />
      <NumberInput label="Max items" value={c.maxItems} onChange={v => update('maxItems', v)} integer min={1} placeholder="No limit" />
      <Select
        label="Display as"
        value={c.displayAs || 'form'}
        onChange={v => update('displayAs', v === 'form' ? null : v)}
        options={[
          { value: 'form', label: 'Form (one item at a time)' },
          { value: 'spreadsheet', label: 'Spreadsheet (table)' },
        ]}
      />
    </div>
  )

  // dialog has no extra type-specific settings beyond title and children
  return null
}

function ComponentCard({ component, index, total, onChange, onRemove, onMove, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth === 0)
  const [showSettings, setShowSettings] = useState(false)

  const Icon = TYPE_ICON[component.type] || Type
  const isContainer = component.type === 'repeat' || component.type === 'dialog'
  const labelKey = component.type === 'dialog' ? 'title' : 'label'

  const update = (key, value) => onChange(setProp(component, key, value))

  const handleTypeChange = newType => {
    onChange(convertComponent(component, newType))
    setShowSettings(false)
  }

  const updateChild = (childIdx, newChild) => {
    const nextChildren = (component.components || []).map((c, i) => i === childIdx ? newChild : c)
    onChange({ ...component, components: nextChildren })
  }
  const removeChild = childIdx => {
    const nextChildren = (component.components || []).filter((_, i) => i !== childIdx)
    onChange({ ...component, components: nextChildren })
  }
  const addChild = () => {
    onChange({ ...component, components: [...(component.components || []), defaultComponent('string')] })
  }
  const moveChild = (childIdx, delta) => {
    const list = component.components || []
    const target = childIdx + delta
    if (target < 0 || target >= list.length) return
    const next = [...list]
    ;[next[childIdx], next[target]] = [next[target], next[childIdx]]
    onChange({ ...component, components: next })
  }

  return (
    <div className="card p-4">
      <div className="flex gap-3 items-start group">
        <div className="flex flex-col items-center gap-0.5 mt-1 text-gray-300">
          <button type="button" onClick={() => onMove(index, -1)} disabled={index === 0}
            className="hover:text-gray-500 disabled:opacity-30 disabled:cursor-not-allowed">
            <ChevronUp size={14} />
          </button>
          <GripVertical size={14} className="cursor-grab" />
          <button type="button" onClick={() => onMove(index, 1)} disabled={index === total - 1}
            className="hover:text-gray-500 disabled:opacity-30 disabled:cursor-not-allowed">
            <ChevronDown size={14} />
          </button>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <button type="button" onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700">
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              <Icon size={14} className="text-brand-500" />
              <span className="text-sm font-medium text-gray-700">
                {component[labelKey] || <span className="italic text-gray-400">Untitled</span>}
              </span>
              {component.id && (
                <span className="font-mono text-xs text-gray-400">#{component.id}</span>
              )}
            </button>
            <span className="text-xs text-gray-400 ml-auto">{TYPE_LABEL[component.type] || component.type}</span>
          </div>

          {expanded && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <TextInput label="ID (placeholder key)" mono value={component.id}
                  onChange={v => update('id', v)} placeholder="e.g. client_name" />
                <TextInput label={component.type === 'dialog' ? 'Title' : 'Label'} value={component[labelKey]}
                  onChange={v => update(labelKey, v)} placeholder={component.type === 'dialog' ? 'e.g. Billing details' : 'e.g. Client name'} />
                <Select
                  label="Type"
                  value={component.type}
                  onChange={handleTypeChange}
                  options={COMPONENT_TYPES.map(t => ({ value: t.value, label: t.label }))}
                />
                {!isContainer && (
                  <Checkbox label="Required question" checked={component.required}
                    onChange={v => update('required', v || null)} className="mt-6" />
                )}
                <div className="col-span-2">
                  <label className="label text-xs">Help text / guidance</label>
                  <input className="input text-sm" value={component.helpText ?? ''}
                    onChange={e => update('helpText', e.target.value)}
                    placeholder="Shown beneath the question" />
                </div>
              </div>

              {component.type !== 'dialog' && (
                <div className="border-t border-gray-100 pt-2">
                  <button type="button" onClick={() => setShowSettings(!showSettings)}
                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors">
                    {showSettings ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    <span className="font-medium">Type settings</span>
                    {!showSettings && (
                      <span className="text-gray-400 ml-1">{configSummary(component)}</span>
                    )}
                  </button>
                  {showSettings && (
                    <TypeSettings component={component} update={update} />
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <button type="button" onClick={() => onRemove(index)}
          className="mt-1 text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
          title="Remove component">
          <Trash2 size={16} />
        </button>
      </div>

      {isContainer && expanded && (
        <div className="mt-3 pl-6 border-l-2 border-brand-100">
          <p className="text-xs uppercase tracking-wide text-gray-400 font-medium mb-2">
            {component.type === 'repeat' ? 'Per-item fields' : 'Dialog fields'}
          </p>
          {(component.components || []).length === 0 ? (
            <p className="text-xs text-gray-400 italic mb-2">No sub-fields yet</p>
          ) : (
            <div className="space-y-2 mb-2">
              {(component.components || []).map((child, i) => (
                <ComponentCard
                  key={i}
                  component={child}
                  index={i}
                  total={(component.components || []).length}
                  onChange={c => updateChild(i, c)}
                  onRemove={removeChild}
                  onMove={moveChild}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
          <button type="button" onClick={addChild}
            className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
            <Plus size={12} /> Add sub-field
          </button>
        </div>
      )}
    </div>
  )
}

function MetadataPanel({ template }) {
  if (!template) return null
  const created = template.createdAt || template.created_at
  const updated = template.updatedAt || template.updated_at
  return (
    <div className="card p-4">
      <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Template details</h2>
      <div className="space-y-2.5 text-sm">
        <div className="flex items-start gap-3">
          <FileText size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-xs text-gray-400">Name</p>
            <p className="text-gray-900">{template.name}</p>
            {template.description && (
              <p className="text-gray-500 mt-0.5">{template.description}</p>
            )}
          </div>
        </div>
        {template.originalFilename && (
          <div className="flex items-start gap-3">
            <FileText size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-400">Source document</p>
              <p className="text-gray-900 font-mono text-xs truncate">{template.originalFilename}</p>
            </div>
          </div>
        )}
        {created && (
          <div className="flex items-start gap-3">
            <Calendar size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-400">Created</p>
              <p className="text-gray-900">{safeDate(created)}</p>
              {template.createdBy && (
                <p className="text-xs text-gray-500 mt-0.5">by {template.createdBy}</p>
              )}
            </div>
          </div>
        )}
        {updated && (
          <div className="flex items-start gap-3">
            <Clock size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-400">Last updated</p>
              <p className="text-gray-900">{safeDate(updated)}</p>
            </div>
          </div>
        )}
        {template.generationMethod && (
          <div className="flex items-start gap-3">
            <Sparkles size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-400">Generation method</p>
              <p className="text-gray-900 capitalize">{template.generationMethod}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function safeDate(s) {
  try {
    const d = new Date(s)
    if (Number.isNaN(d.getTime())) return s
    return format(d, 'PPp')
  } catch { return s }
}

export default function TemplateEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [template, setTemplate] = useState(null)
  const [interview, setInterview] = useState(null)
  const [components, setComponents] = useState([])
  const [saving, setSaving] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)
  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenPrompt, setRegenPrompt] = useState('')
  const [regenerating, setRegenerating] = useState(false)

  // Load metadata and the full interview JSON in parallel. Components come
  // from the interview file (not the simplified `fields` array on the
  // template meta) so nested repeat/dialog children round-trip correctly.
  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.get(`/templates/${id}`),
      api.get(`/templates/${id}/interview`),
    ]).then(([metaResp, intResp]) => {
      if (cancelled) return
      setTemplate(metaResp.data)
      setInterview(intResp.data)
      setComponents(intResp.data?.components || [])
      if (metaResp.data.originalPrompt || metaResp.data.original_prompt) {
        setRegenPrompt(metaResp.data.originalPrompt || metaResp.data.original_prompt)
      }
    }).catch(() => toast.error('Template not found'))
    return () => { cancelled = true }
  }, [id])

  const updateComponent = (index, newComp) => {
    setComponents(cs => cs.map((c, i) => i === index ? newComp : c))
  }
  const removeComponent = index => {
    setComponents(cs => cs.filter((_, i) => i !== index))
  }
  const moveComponent = (index, delta) => {
    const target = index + delta
    if (target < 0 || target >= components.length) return
    setComponents(cs => {
      const next = [...cs]
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }
  const addComponent = type => {
    setComponents(cs => [...cs, defaultComponent(type)])
  }

  // Recursively validate the editor state before sending it to the server.
  // The backend also validates, but catching it client-side gives clearer
  // per-field errors.
  const findValidationError = (list, path = '') => {
    for (let i = 0; i < list.length; i++) {
      const c = list[i]
      const where = `${path}#${i + 1}`
      if (!c.id || !c.id.trim()) return `Component ${where} is missing an ID`
      if (c.type === 'dialog') {
        if (!c.title || !c.title.trim()) return `Dialog '${c.id}' is missing a title`
      } else if (!c.label || !c.label.trim()) {
        return `Component '${c.id}' is missing a label`
      }
      if (c.type === 'choice') {
        if (!Array.isArray(c.options) || c.options.length === 0) {
          return `Choice '${c.id}' needs at least one option`
        }
        for (const opt of c.options) {
          if (!opt.value || !opt.label) return `Choice '${c.id}' has an option missing value or label`
        }
      }
      if ((c.type === 'repeat' || c.type === 'dialog')) {
        if (!Array.isArray(c.components) || c.components.length === 0) {
          return `${c.type === 'repeat' ? 'Repeat' : 'Dialog'} '${c.id}' needs at least one sub-field`
        }
        const err = findValidationError(c.components, `${c.id}.`)
        if (err) return err
      }
    }
    return null
  }

  const save = async () => {
    const err = findValidationError(components)
    if (err) return toast.error(err)
    setSaving(true)
    try {
      // Backend accepts `fields` and writes them into the interview JSON,
      // bumping the interview version on each save.
      await api.put(`/templates/${id}`, { fields: components })
      toast.success('Interview saved')
      navigate('/templates')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  const handleRegenerate = async () => {
    if (!regenPrompt.trim()) return toast.error('Please enter a prompt')
    if (!confirm('This will overwrite the current document and all interview questions. Continue?')) return
    setRegenerating(true)
    try {
      const { data } = await api.post(`/templates/${id}/regenerate`, { prompt: regenPrompt })
      setTemplate(data)
      // Reload the interview JSON since the components have changed.
      const intResp = await api.get(`/templates/${id}/interview`)
      setInterview(intResp.data)
      setComponents(intResp.data?.components || [])
      setShowRegenModal(false)
      toast.success('Template regenerated with AI')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Regeneration failed')
    } finally { setRegenerating(false) }
  }

  if (!template || !interview) {
    return <div className="text-center text-gray-400 py-16 text-sm">Loading…</div>
  }

  const isAi = template.generationMethod === 'ai' || template.generation_method === 'ai'
  const originalPrompt = template.originalPrompt || template.original_prompt

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate('/templates')}
          className="text-gray-400 hover:text-gray-600 transition-colors">
          <ChevronLeft size={20} />
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Edit interview</h1>
        <span className="text-xs text-gray-400 ml-2">v{interview.version}</span>
      </div>
      <p className="text-sm text-gray-500 mb-6 ml-8">
        {template.name}
        {template.originalFilename && <> &middot; {template.originalFilename}</>}
      </p>

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 space-y-3">
          {isAi && originalPrompt && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-3 text-sm text-purple-800">
              <button onClick={() => setShowPrompt(!showPrompt)}
                className="flex items-center gap-2 font-medium w-full text-left">
                <Sparkles size={14} />
                AI-generated template
                {showPrompt ? <ChevronUp size={14} className="ml-auto" /> : <ChevronDown size={14} className="ml-auto" />}
              </button>
              {showPrompt && (
                <div className="mt-2 bg-white rounded p-3 text-gray-700 text-sm whitespace-pre-wrap border border-purple-100">
                  {originalPrompt}
                </div>
              )}
              <button onClick={() => setShowRegenModal(true)}
                className="mt-2 text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1">
                <RefreshCw size={12} /> Regenerate with AI
              </button>
            </div>
          )}

          <div className="bg-brand-50 border border-brand-200 rounded-lg px-4 py-3 text-sm text-brand-800">
            <strong>Tip:</strong> Component IDs must match your <code className="font-mono bg-brand-100 px-1 rounded">{'{{placeholders}}'}</code> exactly.
            Repeat groups render as nested tables in the rendered document.
          </div>

          {components.length === 0 ? (
            <div className="card p-8 text-center text-gray-400 text-sm">
              No components yet. Add a component below to get started.
            </div>
          ) : (
            <div className="space-y-3">
              {components.map((c, i) => (
                <ComponentCard
                  key={i}
                  component={c}
                  index={i}
                  total={components.length}
                  onChange={nc => updateComponent(i, nc)}
                  onRemove={removeComponent}
                  onMove={moveComponent}
                />
              ))}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <div className="flex flex-wrap gap-2">
              {COMPONENT_TYPES.map(t => {
                const Icon = t.icon
                return (
                  <button key={t.value} type="button" onClick={() => addComponent(t.value)}
                    className="btn-secondary text-sm">
                    <Icon size={14} /> {t.label}
                  </button>
                )
              })}
            </div>
            <div className="flex gap-3">
              <button onClick={() => navigate('/templates')} className="btn-secondary">Cancel</button>
              <button onClick={save} disabled={saving} className="btn-primary">
                <Save size={16} /> {saving ? 'Saving…' : 'Save interview'}
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <MetadataPanel template={template} />
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Interview file</h2>
            <div className="space-y-2 text-sm">
              <div>
                <p className="text-xs text-gray-400">File</p>
                <p className="text-gray-900 font-mono text-xs truncate">
                  {template.interviewFile || template.interview_file || 'interview.json'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Schema version</p>
                <p className="text-gray-900">{interview.schemaVersion}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Components</p>
                <p className="text-gray-900">{components.length}</p>
              </div>
              {Array.isArray(interview.rules) && interview.rules.length > 0 && (
                <div>
                  <p className="text-xs text-gray-400">Rules</p>
                  <p className="text-gray-900">{interview.rules.length}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

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
                <Sparkles size={14} /> {regenerating ? 'Generating…' : 'Regenerate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
