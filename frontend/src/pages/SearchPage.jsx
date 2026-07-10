import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api'
import { formatDistanceToNow } from 'date-fns'
import { Search as SearchIcon, FileText, ClipboardList, FolderOpen } from 'lucide-react'

const STATUS_CLASSES = {
  pending: 'badge-pending', generated: 'badge-generated',
  approved: 'badge-approved', rejected: 'badge-rejected', error: 'badge-error'
}

function Section({ icon: Icon, title, items, render, empty }) {
  return (
    <div className="card mb-4">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-brand-100 bg-brand-50">
        <Icon size={15} className="text-brand-500" />
        <h2 className="text-sm font-semibold text-brand-800">{title}</h2>
        <span className="text-xs text-brand-400">({items.length})</span>
      </div>
      {items.length === 0 ? (
        <div className="px-5 py-4 text-sm text-brand-400">{empty}</div>
      ) : (
        <ul className="divide-y divide-brand-50">{items.map(render)}</ul>
      )}
    </div>
  )
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const [input, setInput] = useState(params.get('q') || '')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const runSearch = useCallback((q) => {
    if (!q || !q.trim()) { setResults(null); return }
    setLoading(true)
    api.get('/search/', { params: { q } })
      .then(r => setResults(r.data))
      .catch(() => setResults(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { runSearch(params.get('q') || '') }, [params, runSearch])

  const submit = (e) => {
    e.preventDefault()
    setParams(input.trim() ? { q: input.trim() } : {})
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-900 mb-6">Search</h1>

      <form onSubmit={submit} className="relative max-w-xl mb-6">
        <SearchIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-400" />
        <input
          className="input pl-9"
          placeholder="Search templates, submissions and answersets…"
          value={input}
          autoFocus
          onChange={e => setInput(e.target.value)}
        />
      </form>

      {loading && <div className="text-sm text-brand-400">Searching…</div>}

      {!loading && results && (
        <>
          <p className="text-sm text-brand-500 mb-4">{results.total} result{results.total === 1 ? '' : 's'} for “{results.query}”</p>

          <Section
            icon={FileText} title="Templates" items={results.templates} empty="No matching templates"
            render={t => (
              <li key={t.id} className="px-5 py-3 hover:bg-brand-50">
                <Link to={`/templates/${t.id}/edit`} className="flex items-center justify-between">
                  <span className="font-medium text-brand-900">{t.name}</span>
                  <span className="text-xs text-brand-500 truncate max-w-xs">{t.description}</span>
                </Link>
              </li>
            )}
          />

          <Section
            icon={ClipboardList} title="Submissions" items={results.submissions} empty="No matching submissions"
            render={s => (
              <li key={s.id} className="px-5 py-3 hover:bg-brand-50">
                <Link to={`/submissions/${s.id}`} className="flex items-center justify-between gap-3">
                  <span className="font-medium text-brand-900">{s.template_name}</span>
                  <span className="flex items-center gap-3 text-xs text-brand-500">
                    <span>{s.submitted_by_name}</span>
                    <span className={STATUS_CLASSES[s.status] || 'badge'}>{s.status}</span>
                    <span>{s.submitted_at ? formatDistanceToNow(new Date(s.submitted_at), { addSuffix: true }) : '—'}</span>
                  </span>
                </Link>
              </li>
            )}
          />

          <Section
            icon={FolderOpen} title="Answersets" items={results.answersets} empty="No matching answersets"
            render={a => (
              <li key={a.id} className="px-5 py-3 hover:bg-brand-50">
                <Link to={`/answersets/${a.id}`} className="flex items-center justify-between gap-3">
                  <span className="font-medium text-brand-900">{a.template_name}</span>
                  <span className="flex items-center gap-3 text-xs text-brand-500">
                    <span>{a.submitted_by_name}</span>
                    <span className={STATUS_CLASSES[a.status] || 'badge'}>{a.status}</span>
                    <span>{a.submitted_at ? formatDistanceToNow(new Date(a.submitted_at), { addSuffix: true }) : '—'}</span>
                  </span>
                </Link>
              </li>
            )}
          />
        </>
      )}
    </div>
  )
}
