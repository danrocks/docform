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
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-50 last:border-0">
      <Icon size={15} className="text-gray-400 mt-0.5 flex-shrink-0"/>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 mb-0.5">{label}</p>
        <p className="text-sm text-gray-900">{value}</p>
      </div>
    </div>
  )
}

export default function SubmissionDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [sub, setSub] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const load = () => api.get(`/submissions/${id}`).then(r => setSub(r.data)).finally(() => setLoading(false))
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

  if (loading) return <div className="text-center text-gray-400 py-16 text-sm">Loading…</div>
  if (!sub) return <div className="text-center text-gray-400 py-16 text-sm">Not found</div>

  const canApprove = ['admin','approver'].includes(user.role) && ['generated','pending'].includes(sub.status)
  const submittedDate = sub.submitted_at ? format(new Date(sub.submitted_at + 'Z'), 'PPpp') : '—'
  const approvedDate = sub.approved_at ? format(new Date(sub.approved_at + 'Z'), 'PPpp') : null

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/submissions')}
          className="text-gray-400 hover:text-gray-600 transition-colors">
          <ChevronLeft size={20}/>
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{sub.template_name}</h1>
            <span className={STATUS_CLASSES[sub.status] || 'badge'}>{sub.status}</span>
          </div>
          <p className="text-sm text-gray-500 mt-0.5 font-mono">#{id.slice(0,8)}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Left: field data */}
        <div className="col-span-2 space-y-5">
          <div className="card p-5">
            <h2 className="font-semibold text-gray-900 mb-4 text-sm uppercase tracking-wide text-gray-500">Form data</h2>
            <div className="space-y-3">
              {Object.entries(sub.data || {}).map(([k, v]) => (
                <div key={k} className="flex gap-4 border-b border-gray-50 pb-3 last:border-0 last:pb-0">
                  <p className="text-sm text-gray-500 w-40 flex-shrink-0 capitalize">{k.replace(/_/g,' ')}</p>
                  <p className="text-sm text-gray-900 font-medium flex-1">{String(v)}</p>
                </div>
              ))}
            </div>
          </div>

          {sub.context && (
            <div className="card p-5">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Context / notes</h2>
              <p className="text-sm text-gray-700">{sub.context}</p>
            </div>
          )}

          {sub.status === 'rejected' && sub.rejection_reason && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3">
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
            <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Details</h2>
            <InfoRow icon={User}     label="Submitted by" value={sub.submitted_by_name} />
            <InfoRow icon={Calendar} label="Submitted"    value={submittedDate} />
            {sub.approved_by_name && (
              <InfoRow icon={CheckCircle} label="Approved by"  value={`${sub.approved_by_name} · ${approvedDate}`} />
            )}
          </div>

          {/* Downloads */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Documents</h2>
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
                <p className="text-xs text-gray-400 text-center">PDF requires LibreOffice on the server</p>
              )}
            </div>
          </div>

          {/* Approver actions */}
          {canApprove && (
            <div className="card p-4">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-500 mb-3">Review</h2>
              <div className="space-y-2">
                <button onClick={approve} disabled={actionLoading}
                  className="btn-primary w-full justify-center text-sm bg-green-600 hover:bg-green-700">
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
            <h3 className="font-semibold text-gray-900 mb-3">Reject submission</h3>
            <p className="text-sm text-gray-500 mb-3">Please provide a reason for rejecting this submission.</p>
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
