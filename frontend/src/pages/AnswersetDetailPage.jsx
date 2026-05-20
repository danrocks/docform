import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { format, formatDistanceToNow } from 'date-fns'
import {
  ChevronLeft, Download, CheckCircle, XCircle,
  FileText, User, Calendar, MessageSquare, AlertCircle,
  Copy, Share2, Clock, Shield
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

function FieldValue({ value }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-sm text-brand-400 italic">No entries</span>
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
  if (value && typeof value === 'object') return <ObjectEntries obj={value} />
  return <span className="text-sm text-brand-900 font-medium">{formatScalar(value)}</span>
}

function ObjectEntries({ obj }) {
  const entries = Object.entries(obj)
  if (entries.length === 0) return <span className="text-sm text-brand-400 italic">Empty</span>
  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-3">
          <p className="text-xs text-brand-500 w-32 flex-shrink-0 capitalize mt-0.5">{humanizeKey(k)}</p>
          <div className="flex-1 min-w-0"><FieldValue value={v} /></div>
        </div>
      ))}
    </div>
  )
}

export default function AnswersetDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [answerset, setAnswerset] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [showShareModal, setShowShareModal] = useState(false)
  const [shareWith, setShareWith] = useState('')
  const [auditLog, setAuditLog] = useState([])
  const [showAudit, setShowAudit] = useState(false)

  const load = useCallback(() => {
    api.get(`/answersets/${id}`)
      .then(r => setAnswerset(r.data))
      .catch(() => {
        api.get(`/submissions/${id}`).then(r => setAnswerset(r.data))
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => { load() }, [load])

  const loadAudit = async () => {
    try {
      const r = await api.get(`/answersets/${id}/audit`)
      setAuditLog(r.data)
      setShowAudit(true)
    } catch {
      toast.error('Unable to load audit log')
    }
  }

  const download = async (fmt) => {
    try {
      const resp = await api.get(`/answersets/${id}/download/${fmt}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${(answerset?.template_name || 'document').replace(/\s+/g, '_')}_${id.slice(0, 8)}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(`${fmt.toUpperCase()} not available`)
    }
  }

  const handleClone = async () => {
    try {
      const { data } = await api.post(`/answersets/${id}/clone`)
      toast.success('Answerset cloned')
      navigate(`/answersets/${data.id}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Clone failed')
    }
  }

  const handleShare = async () => {
    const userIds = shareWith.split(',').map(s => s.trim()).filter(Boolean)
    if (userIds.length === 0) return toast.error('Enter at least one user ID')
    try {
      await api.put(`/answersets/${id}/share`, { shared_with: userIds })
      toast.success('Sharing updated')
      setShowShareModal(false)
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Share failed')
    }
  }

  const approve = async () => {
    setActionLoading(true)
    try {
      const { data } = await api.put(`/submissions/${id}/approve`)
      setAnswerset(prev => ({ ...prev, ...data }))
      toast.success('Approved')
    } catch { toast.error('Failed to approve') }
    finally { setActionLoading(false) }
  }

  const reject = async () => {
    if (!rejectReason.trim()) return toast.error('Please enter a reason')
    setActionLoading(true)
    try {
      const { data } = await api.put(`/submissions/${id}/reject`, { reason: rejectReason })
      setAnswerset(prev => ({ ...prev, ...data }))
      setShowRejectModal(false)
      toast.success('Rejected')
    } catch { toast.error('Failed to reject') }
    finally { setActionLoading(false) }
  }

  if (loading) return <div className="text-center text-brand-400 py-16 text-sm">Loading…</div>
  if (!answerset) return <div className="text-center text-brand-400 py-16 text-sm">Not found</div>

  const sub = answerset
  const meta = sub.metadata || {}
  const canApprove = ['admin', 'approver'].includes(user.role) && ['generated', 'pending'].includes(sub.status)
  const isOwner = sub.submitted_by === user.id
  const canShare = (isOwner || user.role === 'admin') && !sub.workgroup_id
  const submittedDate = sub.submitted_at ? format(new Date(sub.submitted_at), 'PPpp') : '—'
  const approvedDate = sub.approved_at ? format(new Date(sub.approved_at), 'PPpp') : null

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/answersets')}
          className="text-brand-400 hover:text-brand-600 transition-colors">
          <ChevronLeft size={20}/>
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-brand-900">{sub.template_name}</h1>
            <span className={STATUS_CLASSES[sub.status] || 'badge'}>{sub.status}</span>
          </div>
          <p className="text-sm text-brand-500 mt-0.5 font-mono">#{id.slice(0, 8)}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Left: field data */}
        <div className="col-span-2 space-y-5">
          <div className="card p-5">
            <h2 className="font-semibold text-brand-900 mb-4 text-sm uppercase tracking-wide text-brand-500">Interview data</h2>
            <div className="space-y-3">
              {Object.entries(sub.data || {}).map(([k, v]) => (
                <div key={k} className="flex gap-4 border-b border-brand-50 pb-3 last:border-0 last:pb-0">
                  <p className="text-sm text-brand-500 w-40 flex-shrink-0 capitalize">{humanizeKey(k)}</p>
                  <div className="flex-1 min-w-0"><FieldValue value={v} /></div>
                </div>
              ))}
            </div>
          </div>

          {sub.context && (
            <div className="card p-5">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Context / Notes</h2>
              <p className="text-sm text-brand-700">{sub.context}</p>
            </div>
          )}

          {sub.completion_percentage !== undefined && (
            <div className="card p-5">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Completion</h2>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-brand-100 rounded-full h-2">
                  <div className="bg-accent-600 h-2 rounded-full transition-all"
                    style={{ width: `${sub.completion_percentage}%` }} />
                </div>
                <span className="text-sm font-medium text-brand-700">{sub.completion_percentage}%</span>
              </div>
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

          {/* Audit log */}
          {showAudit && auditLog.length > 0 && (
            <div className="card p-5">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Audit Log</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {auditLog.map(entry => (
                  <div key={entry.id} className="flex items-center gap-3 text-xs border-b border-brand-50 pb-2">
                    <Clock size={12} className="text-brand-400"/>
                    <span className="text-brand-500">
                      {entry.timestamp ? formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true }) : '—'}
                    </span>
                    <span className="font-medium text-brand-700">{entry.operation}</span>
                    <span className="text-brand-500">by {entry.user_name}</span>
                    <span className="text-brand-400">{entry.ip_address}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: meta + actions */}
        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Details</h2>
            <InfoRow icon={User} label="Submitted by" value={sub.submitted_by_name} />
            <InfoRow icon={Calendar} label="Submitted" value={submittedDate} />
            {sub.approved_by_name && (
              <InfoRow icon={CheckCircle} label="Approved by" value={`${sub.approved_by_name} · ${approvedDate}`} />
            )}
            {meta.version && (
              <InfoRow icon={Shield} label="Version" value={`v${meta.version}`} />
            )}
            {meta.shared_with && meta.shared_with.length > 0 && (
              <InfoRow icon={Share2} label="Shared with" value={meta.shared_with.join(', ')} />
            )}
          </div>

          {/* Documents */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Documents</h2>
            <div className="space-y-2">
              <button onClick={() => download('docx')} disabled={!sub.docx_path}
                className="btn-secondary w-full justify-center text-sm disabled:opacity-40">
                <Download size={14}/> Download .docx
              </button>
              <button onClick={() => download('pdf')} disabled={!sub.pdf_path}
                className="btn-secondary w-full justify-center text-sm disabled:opacity-40">
                <Download size={14}/> Download PDF
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-brand-500 mb-3">Actions</h2>
            <div className="space-y-2">
              <button onClick={handleClone} className="btn-secondary w-full justify-center text-sm">
                <Copy size={14}/> Clone
              </button>
              {canShare && (
                <button onClick={() => {
                  setShareWith((meta.shared_with || []).join(', '))
                  setShowShareModal(true)
                }} className="btn-secondary w-full justify-center text-sm">
                  <Share2 size={14}/> Share
                </button>
              )}
              {['admin', 'approver'].includes(user.role) && (
                <button onClick={loadAudit} className="btn-secondary w-full justify-center text-sm">
                  <Shield size={14}/> Audit Log
                </button>
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
            <h3 className="font-semibold text-brand-900 mb-3">Reject answerset</h3>
            <p className="text-sm text-brand-500 mb-3">Please provide a reason for rejecting.</p>
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

      {/* Share modal */}
      {showShareModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="card w-full max-w-sm p-6">
            <h3 className="font-semibold text-brand-900 mb-3">Share answerset</h3>
            <p className="text-sm text-brand-500 mb-3">Enter user IDs to share with (comma-separated).</p>
            <input className="input mb-4" value={shareWith}
              onChange={e => setShareWith(e.target.value)}
              placeholder="e.g. user-1, user-2" autoFocus />
            <div className="flex gap-3">
              <button onClick={() => setShowShareModal(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button onClick={handleShare} className="btn-primary flex-1 justify-center">
                Save sharing
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
