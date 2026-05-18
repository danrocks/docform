import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import {
  ChevronLeft, Download, CheckCircle, XCircle,
  FileText, User, Calendar, MessageSquare, AlertCircle
} from 'lucide-react'

const STATUS_CLASSES = {
  pending: 'badge-pending', generated: 'badge-generated',
  approved: 'badge-approved', rejected: 'badge-rejected', error: 'badge-error'
}

function InfoRow({ icon: Icon, label, value }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-brand-50 last:border-0">
      <Icon size={15} className="text-brand-400 mt-0.5 flex-shrink-0"/>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-brand-400 mb-0.5">{label}</p>
        <p className="text-sm text-brand-900">{value}</p>
      </div>
    </div>
  )
}

function humanizeKey(k) {
  return String(k).replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2')
}

function formatScalar(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  return String(v)
}

// Render a single submission value. Strings/numbers/dates render inline;
// arrays render as numbered nested blocks (repeat groups); plain objects
// render as a stack of key/value pairs.
function FieldValue({ value }) {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-sm text-brand-400 italic">No entries</span>
    }
    return (
      <div className="space-y-2">
        {value.map((item, idx) => (
          <div key={idx} className="border border-brand-100 rounded-lg p-3 bg-brand-50/50">
            <p className="text-xs text-brand-400 mb-2 font-medium">Item {idx + 1}</p>
            {item && typeof item === 'object' && !Array.isArray(item) ? (
              <ObjectEntries obj={item} />
            ) : (
              <FieldValue value={item} />
            )}
          </div>
        ))}
      </div>
    )
  }

  if (value && typeof value === 'object') {
    return <ObjectEntries obj={value} />
  }

  return <span className="text-sm text-brand-900 font-medium">{formatScalar(value)}</span>
}

function ObjectEntries({ obj }) {
  const entries = Object.entries(obj)
  if (entries.length === 0) {
    return <span className="text-sm text-brand-400 italic">Empty</span>
  }
  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-3">
          <p className="text-xs text-brand-500 w-32 flex-shrink-0 capitalize mt-0.5">{humanizeKey(k)}</p>
          <div className="flex-1 min-w-0">
            <FieldValue value={v} />
          </div>
        </div>
      ))}
    </div>
  )
}

// Render a leaf-component value (string / number / datetime / choice) using
// metadata from the component itself rather than just the raw key/value pair.
// This lets us honour labels, choice option labels, number prefix/suffix, etc.
function LeafValue({ component, value }) {
  if (value === null || value === undefined || value === '') {
    return <span className="text-sm text-brand-400 italic">—</span>
  }

  if (component.type === 'choice') {
    const options = component.options || []
    const lookup = v => {
      const opt = options.find(o => o.value === v)
      return opt ? opt.label : String(v)
    }
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-sm text-brand-400 italic">—</span>
      }
      return <span className="text-sm text-brand-900 font-medium">{value.map(lookup).join(', ')}</span>
    }
    return <span className="text-sm text-brand-900 font-medium">{lookup(value)}</span>
  }

  if (component.type === 'number') {
    let n = value
    if (typeof n === 'string') {
      const parsed = parseFloat(n)
      if (Number.isFinite(parsed)) n = parsed
    }
    if (typeof n === 'number' && Number.isFinite(n)) {
      const display = component.decimalPlaces != null
        ? n.toFixed(component.decimalPlaces)
        : String(n)
      const prefix = component.prefix || ''
      const suffix = component.suffix
        ? ` ${component.suffix}`
        : component.unit && !component.prefix
          ? ` ${component.unit}`
          : ''
      return <span className="text-sm text-brand-900 font-medium">{prefix}{display}{suffix}</span>
    }
  }

  return <span className="text-sm text-brand-900 font-medium">{formatScalar(value)}</span>
}

// Walk a list of InterviewSchema components and render their values against
// `data` (an object whose keys match component ids). Dialog components are
// rendered as labelled sections; repeat components render each row by
// recursing with the row data. Missing values render as an em-dash so users
// can see which fields the schema declares even when the submission predates
// them.
function SchemaSection({ components, data, depth = 0 }) {
  if (!components || components.length === 0) return null
  return (
    <div className="space-y-3">
      {components.map(c => {
        if (c.type === 'dialog') {
          return (
            <div key={c.id} className="space-y-2">
              {c.title && (
                <h3 className="text-xs font-semibold text-brand-500 uppercase tracking-wide">
                  {c.title}
                </h3>
              )}
              <div className={depth === 0 ? 'pl-0' : 'pl-3 border-l border-brand-100'}>
                <SchemaSection components={c.components || []} data={data} depth={depth + 1} />
              </div>
            </div>
          )
        }

        const label = c.label || c.id

        if (c.type === 'repeat') {
          const rows = Array.isArray(data?.[c.id]) ? data[c.id] : []
          return (
            <div key={c.id} className="flex gap-4 border-b border-brand-50 pb-3 last:border-0 last:pb-0">
              <p className="text-sm text-brand-500 w-40 flex-shrink-0">{label}</p>
              <div className="flex-1 min-w-0">
                {rows.length === 0 ? (
                  <span className="text-sm text-brand-400 italic">No entries</span>
                ) : (
                  <div className="space-y-2">
                    {rows.map((row, idx) => {
                      const rowData = row && typeof row === 'object' ? row : {}
                      const knownInRow = collectTopLevelKeys(c.components || [])
                      const extras = Object.entries(rowData).filter(([k]) => !knownInRow.has(k))
                      return (
                        <div key={idx} className="border border-brand-100 rounded-lg p-3 bg-brand-50/50">
                          <p className="text-xs text-brand-400 mb-2 font-medium">Item {idx + 1}</p>
                          <SchemaSection
                            components={c.components || []}
                            data={rowData}
                            depth={depth + 1}
                          />
                          {extras.length > 0 && (
                            <div className="space-y-2 pt-2 mt-2 border-t border-brand-200">
                              <p className="text-xs text-brand-400 italic">Other data not in current template</p>
                              {extras.map(([k, v]) => (
                                <div key={k} className="flex gap-4">
                                  <p className="text-sm text-brand-500 w-40 flex-shrink-0 capitalize">{humanizeKey(k)}</p>
                                  <div className="flex-1 min-w-0">
                                    <FieldValue value={v} />
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )
        }

        const value = data?.[c.id]
        return (
          <div key={c.id} className="flex gap-4 border-b border-brand-50 pb-3 last:border-0 last:pb-0">
            <p className="text-sm text-brand-500 w-40 flex-shrink-0">{label}</p>
            <div className="flex-1 min-w-0">
              <LeafValue component={c} value={value} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Collect the top-level data keys that a component tree reads from, so we can
// surface any extra/legacy keys in the submission separately.
function collectTopLevelKeys(components, into = new Set()) {
  for (const c of components || []) {
    if (c.type === 'dialog') {
      collectTopLevelKeys(c.components || [], into)
    } else if (c.id) {
      into.add(c.id)
    }
  }
  return into
}

export default function SubmissionDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [sub, setSub] = useState(null)
  const [interview, setInterview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const load = () => api.get(`/submissions/${id}`)
    .then(async r => {
      setSub(r.data)
      if (r.data?.template_id) {
        try {
          const iv = await api.get(`/templates/${r.data.template_id}/interview`)
          setInterview(iv.data)
        } catch {
          // Template may have been deleted or interview missing — fall back to
          // raw data rendering.
          setInterview(null)
        }
      }
    })
    .finally(() => setLoading(false))
  useEffect(() => { load() }, [id])

  const download = async (fmt) => {
    try {
      const resp = await api.get(`/submissions/${id}/download/${fmt}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${sub.template_name.replace(/\s+/g,'_')}_${id.slice(0,8)}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
    } catch { toast.error(`${fmt.toUpperCase()} not available`) }
  }

  const approve = async () => {
    setActionLoading(true)
    try {
      const { data } = await api.put(`/submissions/${id}/approve`)
      setSub(data)
      toast.success('Submission approved')
    } catch { toast.error('Failed to approve') }
    finally { setActionLoading(false) }
  }

  const reject = async () => {
    if (!rejectReason.trim()) return toast.error('Please enter a reason')
    setActionLoading(true)
    try {
      const { data } = await api.put(`/submissions/${id}/reject`, { reason: rejectReason })
      setSub(data)
      setShowRejectModal(false)
      toast.success('Submission rejected')
    } catch { toast.error('Failed to reject') }
    finally { setActionLoading(false) }
  }

  if (loading) return <div className="text-center text-brand-400 py-16 text-sm">Loading…</div>
  if (!sub) return <div className="text-center text-brand-400 py-16 text-sm">Not found</div>

  const canApprove = ['admin','approver'].includes(user.role) && ['generated','pending'].includes(sub.status)
  const submittedDate = sub.submitted_at ? format(new Date(sub.submitted_at), 'PPpp') : '—'
  const approvedDate = sub.approved_at ? format(new Date(sub.approved_at), 'PPpp') : null

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/submissions')}
          className="text-brand-400 hover:text-brand-600 transition-colors">
          <ChevronLeft size={20}/>
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-brand-900">{sub.template_name}</h1>
            <span className={STATUS_CLASSES[sub.status] || 'badge'}>{sub.status}</span>
          </div>
          <p className="text-sm text-brand-500 mt-0.5 font-mono">#{id.slice(0,8)}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Left: field data */}
        <div className="col-span-2 space-y-5">
          <div className="card p-5">
            <h2 className="font-semibold text-brand-900 mb-4 text-sm uppercase tracking-wide text-brand-500">Interview data</h2>
            {(() => {
              const data = sub.data || {}
              const components = interview?.components
              if (components && components.length > 0) {
                const known = collectTopLevelKeys(components)
                const extras = Object.entries(data).filter(([k]) => !known.has(k))
                return (
                  <div className="space-y-3">
                    <SchemaSection components={components} data={data} />
                    {extras.length > 0 && (
                      <div className="space-y-2 pt-3 border-t border-brand-100">
                        <p className="text-xs text-brand-400 italic">
                          Other data not in current template
                        </p>
                        {extras.map(([k, v]) => (
                          <div key={k} className="flex gap-4">
                            <p className="text-sm text-brand-500 w-40 flex-shrink-0 capitalize">{humanizeKey(k)}</p>
                            <div className="flex-1 min-w-0">
                              <FieldValue value={v} />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              }
              return (
                <div className="space-y-3">
                  {Object.entries(data).map(([k, v]) => (
                    <div key={k} className="flex gap-4 border-b border-brand-50 pb-3 last:border-0 last:pb-0">
                      <p className="text-sm text-brand-500 w-40 flex-shrink-0 capitalize">{humanizeKey(k)}</p>
                      <div className="flex-1 min-w-0">
                        <FieldValue value={v} />
                      </div>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>

          {sub.context && (
            <div className="card p-5">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Interview context / notes</h2>
              <p className="text-sm text-brand-700">{sub.context}</p>
            </div>
          )}

          {sub.status === 'rejected' && sub.rejection_reason && (
            <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex gap-3">
              <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5"/>
              <div>
                <p className="text-sm font-medium text-red-700">Rejected</p>
                <p className="text-sm text-red-600 mt-0.5">{sub.rejection_reason}</p>
              </div>
            </div>
          )}
        </div>

        {/* Right: meta + actions */}
        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Details</h2>
            <InfoRow icon={User}     label="Submitted by" value={sub.submitted_by_name} />
            <InfoRow icon={Calendar} label="Submitted"    value={submittedDate} />
            {sub.approved_by_name && (
              <InfoRow icon={CheckCircle} label="Approved by"  value={`${sub.approved_by_name} · ${approvedDate}`} />
            )}
          </div>

          {/* Downloads */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Documents</h2>
            <div className="space-y-2">
              <button onClick={() => download('docx')} disabled={!sub.docx_path}
                className="btn-secondary w-full justify-center text-sm disabled:opacity-40">
                <Download size={14}/> Download .docx
              </button>
              <button onClick={() => download('pdf')} disabled={!sub.pdf_path}
                className="btn-secondary w-full justify-center text-sm disabled:opacity-40"
                title={!sub.pdf_path ? 'LibreOffice not available on this server' : ''}>
                <Download size={14}/> Download PDF
              </button>
              {!sub.pdf_path && sub.docx_path && (
                <p className="text-xs text-brand-400 text-center">PDF requires LibreOffice on the server</p>
              )}
            </div>
          </div>

          {/* Approver actions */}
          {canApprove && (
            <div className="card p-4">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Review</h2>
              <div className="space-y-2">
                <button onClick={approve} disabled={actionLoading}
                  className="btn-primary w-full justify-center text-sm bg-accent-600 hover:bg-accent-700">
                  <CheckCircle size={14}/> Approve
                </button>
                <button onClick={() => setShowRejectModal(true)} disabled={actionLoading}
                  className="btn-danger w-full justify-center text-sm">
                  <XCircle size={14}/> Reject
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reject modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="card w-full max-w-sm p-6">
            <h3 className="font-semibold text-brand-900 mb-3">Reject submission</h3>
            <p className="text-sm text-brand-500 mb-3">Please provide a reason for rejecting this submission.</p>
            <textarea className="input resize-none mb-4" rows={3}
              value={rejectReason} onChange={e => setRejectReason(e.target.value)}
              placeholder="e.g. Missing client signature on page 2" autoFocus />
            <div className="flex gap-3">
              <button onClick={() => setShowRejectModal(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button onClick={reject} disabled={actionLoading} className="btn-danger flex-1 justify-center">
                {actionLoading ? 'Rejecting…' : 'Confirm rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
