/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Audit trail table with expandable detail view and issuer/status filtering.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getLogs, getLog } from '../services/api'

const PAGE_SIZE = 20

// ── Shared display helpers ────────────────────────────────────────────────────

function ConfBadge({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low:    'bg-red-100 text-red-800',
  }[level] || 'bg-gray-100 text-gray-700'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{level || '—'}</span>
}

function StatusBadge({ status }) {
  const cls = {
    pending:        'bg-gray-100 text-gray-700',
    pending_review: 'bg-yellow-100 text-yellow-800',
    accepted:       'bg-green-100 text-green-800',
    overridden:     'bg-blue-100 text-blue-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>
      {status?.replace('_', ' ') || '—'}
    </span>
  )
}

function fmtDate(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function DRow({ label, value, highlight = false }) {
  return (
    <div className="flex items-start gap-1 text-sm">
      <span className="text-gray-500 shrink-0">{label}:</span>
      <span className={`font-medium break-all ${highlight ? 'text-amber-700 bg-amber-50 px-1 rounded' : 'text-gray-800'}`}>
        {value ?? '—'}
      </span>
    </div>
  )
}

// ── Log detail panel (lazy-loaded) ────────────────────────────────────────────

// Fields to surface in "Signals Used" and their display labels
const SIGNAL_LABELS = {
  issuer:                     'Issuer',
  audience_type:              'Audience',
  assessment_type:            'Assessment Type',
  assessment_evaluator:       'Evaluator',
  assessment_required:        'Assessment Required',
  expert_evaluation_required: 'Expert Eval Required',
  self_declared_level:        'Declared Level',
  badge_purpose:              'Badge Purpose',
  criteria_logic:             'Criteria Logic',
  canvas_course_code:         'Canvas Code',
  real_world_context:         'Real-World Context',
  bloom_level:                'Bloom Level',
}

// Fields whose source is considered regex/spacy → yellow chip
const NLP_SOURCE_FIELDS = new Set(['self_declared_level', 'bloom_level', 'real_world_context'])

function LogDetailPanel({ logId }) {
  const [detail, setDetail] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    getLog(logId)
      .then(setDetail)
      .catch(err => setLoadError(err.message))
  }, [logId])

  if (loadError) {
    return (
      <div className="px-6 py-4 text-sm text-red-700 bg-red-50">
        Failed to load: {loadError}
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="px-6 py-4 flex items-center gap-2 text-sm text-gray-500 bg-gray-50">
        <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        Loading…
      </div>
    )
  }

  const status = detail.reviewer_status
  const isOverridden = status === 'overridden'
  const isAccepted   = status === 'accepted'
  const isPending    = !isOverridden && !isAccepted

  const catChanged  = isOverridden && detail.final_category !== detail.recommended_category
  const typeChanged = isOverridden && detail.final_type     !== detail.recommended_type
  const lvlChanged  = isOverridden && detail.final_level    !== detail.recommended_level

  // Parse JSON blobs
  let rules = []
  try { rules = JSON.parse(detail.triggered_rules || '[]') } catch { /* */ }

  let facts = {}
  try { facts = JSON.parse(detail.normalized_facts || '{}') } catch { /* */ }

  let extracted = {}
  try { extracted = JSON.parse(detail.extracted_signals || '{}') } catch { /* */ }

  const missingSignals = extracted.missing_signals || facts.missing_signals || []

  // Build signal chips from SIGNAL_LABELS × normalized_facts
  const signalChips = Object.entries(SIGNAL_LABELS)
    .map(([key, label]) => ({ key, label, value: facts[key] }))
    .filter(({ value }) => value !== null && value !== undefined && value !== '' && value !== false)

  // Right-column border color by status
  const rightBorder = isOverridden
    ? 'border-amber-300 bg-amber-50'
    : isAccepted
      ? 'border-green-300 bg-green-50'
      : 'border-gray-200 bg-white'

  // Copy log ID to clipboard
  function copyId() {
    navigator.clipboard?.writeText(detail.id).catch(() => {})
  }

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-6 py-5 space-y-5 text-sm">

      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="space-y-0.5">
          <p className="font-semibold text-njit-navy text-base">
            {detail.badge_title || 'Untitled Badge'}
          </p>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-mono">{detail.id}</span>
            <button
              onClick={copyId}
              title="Copy Log ID"
              className="text-gray-400 hover:text-gray-600 text-xs border border-gray-200 rounded px-1 py-0.5 leading-none"
            >
              copy
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Submitted: {fmtDate(detail.created_at)}
            {detail.input_type && (
              <span className="ml-3 bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-mono">
                {detail.input_type}
              </span>
            )}
          </p>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* ── Two-column: Recommended vs Final ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Left — System Recommended */}
        <div className="border border-gray-200 rounded-lg p-4 space-y-2 bg-white">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            System Recommended
          </p>
          <DRow label="Category"   value={detail.recommended_category} />
          <DRow label="Type"       value={detail.recommended_type} />
          <DRow label="Level"      value={detail.recommended_type === 'Souvenir' ? 'N/A — no level' : detail.recommended_level} />
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs text-gray-500">Confidence:</span>
            <ConfBadge level={detail.confidence} />
          </div>
        </div>

        {/* Right — Final Decision */}
        <div className={`border rounded-lg p-4 space-y-2 ${rightBorder}`}>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Final Decision
          </p>
          {isPending ? (
            <p className="text-gray-500 italic text-sm pt-1">⏳ Awaiting reviewer decision</p>
          ) : (
            <>
              <DRow label="Category"    value={detail.final_category}    highlight={catChanged} />
              <DRow label="Type"        value={detail.final_type}        highlight={typeChanged} />
              <DRow label="Level"       value={detail.final_level}       highlight={lvlChanged} />
              <DRow label="Status"      value={status} />
              <DRow label="Reviewed by" value={detail.reviewer_id} />
              <DRow label="Date"        value={fmtDate(detail.reviewed_at)} />
            </>
          )}
        </div>
      </div>

      {/* ── Accepted banner ── */}
      {isAccepted && (
        <p className="text-green-700 text-sm font-medium">
          ✅ System recommendation confirmed
        </p>
      )}

      {/* ── Override details ── */}
      {isOverridden && (
        <div className="border border-amber-200 rounded-lg p-4 bg-amber-50 space-y-2">
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
            Override Details
          </p>
          {detail.override_reason && (
            <div>
              <span className="text-xs text-amber-700 font-medium">Reason: </span>
              <span className="text-amber-900 text-sm">{detail.override_reason}</span>
            </div>
          )}
          {(catChanged || typeChanged || lvlChanged) && (
            <div className="space-y-0.5 text-xs">
              <p className="text-amber-700 font-medium">What changed:</p>
              {catChanged  && <p className="text-amber-900">Category: {detail.recommended_category || '—'} → {detail.final_category || '—'}</p>}
              {typeChanged && <p className="text-amber-900">Type: {detail.recommended_type || '—'} → {detail.final_type || '—'}</p>}
              {lvlChanged  && <p className="text-amber-900">Level: {detail.recommended_level || '—'} → {detail.final_level || '—'}</p>}
            </div>
          )}
        </div>
      )}

      {/* ── Classification Explanation ── */}
      {detail.explanation_text && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Classification Explanation
          </p>
          <pre className="whitespace-pre-wrap font-mono text-xs bg-white border border-gray-200 rounded p-3 max-h-[200px] overflow-y-auto text-gray-700 leading-relaxed">
            {detail.explanation_text}
          </pre>
        </div>
      )}

      {/* ── Rules Triggered ── */}
      {rules.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Rules Triggered
          </p>
          <div className="flex flex-wrap gap-1.5">
            {rules.map(r => (
              <span
                key={r}
                className="bg-njit-navy text-white text-xs px-2 py-0.5 rounded font-mono"
              >
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Signals Used ── */}
      {(signalChips.length > 0 || missingSignals.length > 0) && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Signals Used
          </p>
          <div className="flex flex-wrap gap-1.5">
            {signalChips.map(({ key, label, value }) => {
              const isMissing = missingSignals.includes(key)
              const isNlp    = NLP_SOURCE_FIELDS.has(key)
              const chipCls  = isMissing
                ? 'bg-red-50 border-red-300 text-red-700'
                : isNlp
                  ? 'bg-yellow-50 border-yellow-300 text-yellow-800'
                  : 'bg-green-50 border-green-300 text-green-800'
              return (
                <span
                  key={key}
                  className={`border text-xs px-2 py-0.5 rounded ${chipCls}`}
                >
                  {label}: <span className="font-medium">{String(value)}</span>
                </span>
              )
            })}
            {missingSignals
              .filter(s => !signalChips.some(c => c.key === s))
              .map(s => (
                <span
                  key={s}
                  className="border border-red-300 bg-red-50 text-red-700 text-xs px-2 py-0.5 rounded"
                >
                  {s}: <span className="font-medium italic">missing</span>
                </span>
              ))
            }
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function GovernanceLogs() {
  const navigate = useNavigate()
  const [records, setRecords]     = useState([])
  const [total, setTotal]         = useState(0)
  const [page, setPage]           = useState(0)
  const [search, setSearch]       = useState('')
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [expandedId, setExpandedId] = useState(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchPage = useCallback(async (p) => {
    setLoading(true); setError('')
    try {
      const data = await getLogs(PAGE_SIZE, p * PAGE_SIZE)
      setRecords(data.records)
      setTotal(data.total)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchPage(page) }, [page, fetchPage])

  const filtered = search.trim()
    ? records.filter(r => r.badge_title?.toLowerCase().includes(search.toLowerCase()))
    : records

  function toggleExpand(id) {
    setExpandedId(prev => prev === id ? null : id)
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">Governance Logs</h1>
          <p className="text-gray-600 text-sm mt-0.5">{total} total classification records</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="bg-njit-red text-white px-4 py-2 rounded text-sm font-medium hover:bg-njit-red-dark"
        >
          + Submit Badge
        </button>
      </div>

      {/* Search */}
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Filter by badge title…"
        className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-sm focus:outline-none focus:ring-2 focus:ring-njit-red"
      />

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3 text-left">Badge Title</th>
                  <th className="px-4 py-3 text-left">Issuer</th>
                  <th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Level</th>
                  <th className="px-4 py-3 text-left">Confidence</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center text-gray-400 italic py-8">
                      {search ? 'No records match your search.' : 'No records yet.'}
                    </td>
                  </tr>
                )}
                {filtered.map(log => (
                  <>
                    <tr
                      key={log.id}
                      onClick={() => toggleExpand(log.id)}
                      className={`cursor-pointer ${expandedId === log.id ? 'bg-gray-50' : 'hover:bg-gray-50'}`}
                    >
                      <td className="px-4 py-3 font-medium text-njit-navy max-w-[200px] truncate">
                        {log.badge_title}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{log.issuer || '—'}</td>
                      <td className="px-4 py-3 text-gray-700 max-w-[180px] truncate">
                        {log.recommended_category || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-700">{log.recommended_type || '—'}</td>
                      <td className="px-4 py-3 text-gray-700">
                        {log.recommended_type === 'Souvenir'
                          ? <span className="text-gray-400 italic text-xs">N/A</span>
                          : (log.recommended_level || '—')}
                      </td>
                      <td className="px-4 py-3">
                        <ConfBadge level={log.confidence} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={log.reviewer_status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(log.created_at)}</td>
                    </tr>
                    {expandedId === log.id && (
                      <tr key={`${log.id}-detail`}>
                        <td colSpan={8} className="p-0">
                          <LogDetailPanel logId={log.id} />
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>Page {page + 1} of {totalPages} ({total} records)</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                ← Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
