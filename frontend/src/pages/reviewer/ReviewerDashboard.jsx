/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ReviewerDashboard — shows stats, pending queue, and recently reviewed badges.
 * Protected: requires reviewer authentication.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReviewer } from '../../context/ReviewerContext'
import { getReviewerQueue, getLog } from '../../services/api'

function StatCard({ label, value, color }) {
  const colorMap = {
    blue: 'text-blue-700 bg-blue-50 border-blue-200',
    yellow: 'text-yellow-700 bg-yellow-50 border-yellow-200',
    green: 'text-green-700 bg-green-50 border-green-200',
    purple: 'text-purple-700 bg-purple-50 border-purple-200',
  }
  return (
    <div className={`border rounded-lg p-4 text-center ${colorMap[color] || colorMap.blue}`}>
      <div className="text-3xl font-bold">{value ?? '—'}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
    </div>
  )
}

function StatusPill({ status }) {
  const cls = {
    pending:        'bg-gray-100 text-gray-700',
    pending_review: 'bg-yellow-100 text-yellow-800',
    accepted:       'bg-green-100 text-green-800',
    overridden:     'bg-blue-100 text-blue-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>
      {status?.replace('_', ' ')}
    </span>
  )
}

function ConfPill({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800 border-green-300',
    Medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    Low:    'bg-red-100 text-red-800 border-red-300',
  }[level] || 'bg-gray-100 text-gray-700 border-gray-300'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>{level || '—'}</span>
  )
}

// ── Pending queue table (unchanged behaviour) ─────────────────────────────────

function QueueTable({ rows, onReview, emptyMsg }) {
  if (!rows || rows.length === 0) {
    return <p className="text-sm text-gray-500 italic py-4">{emptyMsg}</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <th className="pb-2 pr-4">Badge</th>
            <th className="pb-2 pr-4">Issuer</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Confidence</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Submitted</th>
            <th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(log => (
            <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium text-njit-navy max-w-[200px] truncate">
                {log.badge_title}
              </td>
              <td className="py-2 pr-4 text-gray-600">{log.issuer || '—'}</td>
              <td className="py-2 pr-4 text-gray-600">
                {log.recommended_type || '—'} / {log.recommended_level || '—'}
              </td>
              <td className="py-2 pr-4"><ConfPill level={log.confidence} /></td>
              <td className="py-2 pr-4"><StatusPill status={log.reviewer_status} /></td>
              <td className="py-2 pr-4 text-gray-400 text-xs">
                {log.created_at ? new Date(log.created_at).toLocaleDateString() : '—'}
              </td>
              <td className="py-2">
                {log.review_token ? (
                  <button
                    onClick={() => onReview(log.review_token)}
                    className="text-njit-red text-xs font-medium hover:underline"
                  >
                    Review →
                  </button>
                ) : (
                  <button
                    onClick={() => onReview(null, log.id)}
                    className="text-gray-500 text-xs font-medium hover:underline"
                  >
                    View →
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Inline expanded detail panel for a reviewed log ───────────────────────────

function ReviewedDetailPanel({ logId }) {
  const [detail, setDetail] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    getLog(logId)
      .then(setDetail)
      .catch(err => setLoadError(err.message))
  }, [logId])

  if (loadError) {
    return (
      <div className="px-4 py-3 text-sm text-red-700 bg-red-50 rounded">
        Failed to load details: {loadError}
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="px-4 py-3 flex items-center gap-2 text-sm text-gray-500">
        <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        Loading…
      </div>
    )
  }

  const isOverridden = detail.reviewer_status === 'overridden'

  // Determine which final fields differ from recommended (highlight in amber)
  const catChanged  = isOverridden && detail.final_category !== detail.recommended_category
  const typeChanged = isOverridden && detail.final_type     !== detail.recommended_type
  const lvlChanged  = isOverridden && detail.final_level    !== detail.recommended_level

  // Parse triggered rules
  let rules = []
  try { rules = JSON.parse(detail.triggered_rules || '[]') } catch { /* ignore */ }

  // Parse normalized_facts for signals display
  let facts = {}
  try { facts = JSON.parse(detail.normalized_facts || '{}') } catch { /* ignore */ }

  const SIGNAL_LABELS = {
    issuer:               'Issuer',
    audience_type:        'Audience Type',
    assessment_type:      'Assessment Type',
    assessment_evaluator: 'Assessment Evaluator',
    self_declared_level:  'Declared Level',
    badge_purpose:        'Badge Purpose',
    criteria_logic:       'Criteria Logic',
    canvas_course_code:   'Canvas Code',
    expert_evaluation_required: 'Expert Evaluation Required',
  }
  const signalEntries = Object.entries(SIGNAL_LABELS)
    .map(([k, label]) => ({ key: k, label, value: facts[k] }))
    .filter(({ value }) => value !== null && value !== undefined && value !== '' && value !== false)

  const fmtDate = iso => {
    if (!iso) return '—'
    try { return new Date(iso).toLocaleString() } catch { return iso }
  }

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-4 py-5 space-y-5 text-sm">

      {/* Header row */}
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <p className="font-semibold text-njit-navy text-base">
            {detail.badge_title || 'Untitled Badge'}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Submitted: {fmtDate(detail.created_at)}
          </p>
        </div>
        <StatusPill status={detail.reviewer_status} />
      </div>

      {/* System recommended vs Final decision */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Left — System Recommended */}
        <div className="border border-gray-200 rounded-lg p-4 space-y-2 bg-white">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            System Recommended
          </p>
          <Row label="Category"   value={detail.recommended_category} />
          <Row label="Type"       value={detail.recommended_type} />
          <Row label="Level"      value={detail.recommended_level} />
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs text-gray-500">Confidence:</span>
            <ConfPill level={detail.confidence} />
          </div>
        </div>

        {/* Right — Final Decision */}
        <div className="border border-gray-200 rounded-lg p-4 space-y-2 bg-white">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Final Decision
          </p>
          <Row label="Category"    value={detail.final_category}   highlight={catChanged} />
          <Row label="Type"        value={detail.final_type}       highlight={typeChanged} />
          <Row label="Level"       value={detail.final_level}      highlight={lvlChanged} />
          <Row label="Reviewed by" value={detail.reviewer_id} />
          <Row label="Date"        value={fmtDate(detail.reviewed_at)} />
        </div>
      </div>

      {/* Accepted confirmation */}
      {!isOverridden && (
        <p className="text-green-700 text-sm font-medium">
          ✅ System recommendation confirmed
        </p>
      )}

      {/* Override reason */}
      {isOverridden && detail.override_reason && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Override Reason
          </p>
          <p className="text-gray-700 bg-amber-50 border border-amber-200 rounded p-3 text-sm">
            {detail.override_reason}
          </p>
        </div>
      )}

      {/* Classification explanation */}
      {detail.explanation_text && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Classification Explanation
          </p>
          <div className="bg-white border border-gray-200 rounded p-3 font-mono text-xs leading-relaxed overflow-y-auto max-h-[150px] whitespace-pre-wrap text-gray-700">
            {detail.explanation_text}
          </div>
        </div>
      )}

      {/* Rules triggered */}
      {rules.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Rules Triggered
          </p>
          <div className="flex flex-wrap gap-1.5">
            {rules.map(r => (
              <span key={r} className="bg-njit-navy text-white text-xs px-2 py-0.5 rounded font-mono">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Signals used */}
      {signalEntries.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Signals Used
          </p>
          <div className="flex flex-wrap gap-1.5">
            {signalEntries.map(({ key, label, value }) => (
              <span
                key={key}
                className="bg-gray-100 border border-gray-200 text-gray-700 text-xs px-2 py-0.5 rounded"
              >
                {label}: <span className="font-medium">{String(value)}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ label, value, highlight = false }) {
  return (
    <div className="flex items-start gap-1">
      <span className="text-gray-500 shrink-0">{label}:</span>
      <span className={`font-medium ${highlight ? 'text-amber-700 bg-amber-50 px-1 rounded' : 'text-gray-800'}`}>
        {value || '—'}
      </span>
    </div>
  )
}

// ── Recently reviewed table with inline expand ────────────────────────────────

function ReviewedTable({ rows, emptyMsg }) {
  const [expandedId, setExpandedId] = useState(null)

  if (!rows || rows.length === 0) {
    return <p className="text-sm text-gray-500 italic py-4">{emptyMsg}</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <th className="pb-2 pr-4">Badge</th>
            <th className="pb-2 pr-4">Issuer</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Confidence</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Reviewed</th>
            <th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(log => {
            const isExpanded = expandedId === log.id
            return (
              <>
                <tr
                  key={log.id}
                  className={`border-b border-gray-100 ${isExpanded ? 'bg-gray-50' : 'hover:bg-gray-50'}`}
                >
                  <td className="py-2 pr-4 font-medium text-njit-navy max-w-[200px] truncate">
                    {log.badge_title}
                  </td>
                  <td className="py-2 pr-4 text-gray-600">{log.issuer || '—'}</td>
                  <td className="py-2 pr-4 text-gray-600">
                    {log.recommended_type || '—'} / {log.recommended_level || '—'}
                  </td>
                  <td className="py-2 pr-4"><ConfPill level={log.confidence} /></td>
                  <td className="py-2 pr-4"><StatusPill status={log.reviewer_status} /></td>
                  <td className="py-2 pr-4 text-gray-400 text-xs">
                    {log.reviewed_at ? new Date(log.reviewed_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="py-2">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : log.id)}
                      className="text-gray-500 text-xs font-medium hover:underline whitespace-nowrap"
                    >
                      {isExpanded ? 'Close ↑' : 'View →'}
                    </button>
                  </td>
                </tr>
                {isExpanded && (
                  <tr key={`${log.id}-detail`}>
                    <td colSpan={7} className="p-0">
                      <ReviewedDetailPanel logId={log.id} />
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Main dashboard ─────────────────────────────────────────────────────────────

export default function ReviewerDashboard() {
  const { logout } = useReviewer()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getReviewerQueue()
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  function handleReview(token, logId) {
    if (token) {
      navigate(`/reviewer/review/${token}`)
    } else if (logId) {
      navigate(`/reviewer/review/${logId}`)
    }
  }

  function handleLogout() {
    logout()
    navigate('/')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">Reviewer Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Review and approve badge classifications.</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 px-3 py-1.5 rounded"
        >
          Sign Out
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-4 text-sm">{error}</div>
      )}

      {data && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Total Badges" value={data.stats.total} color="blue" />
            <StatCard label="Pending Review" value={data.stats.pending_review} color="yellow" />
            <StatCard label="Accepted" value={data.stats.accepted} color="green" />
            <StatCard label="Overridden" value={data.stats.overridden} color="purple" />
          </div>

          {/* Pending queue */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-njit-navy">
              Pending Review
              {data.stats.pending_review > 0 && (
                <span className="ml-2 text-sm font-normal text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded">
                  {data.stats.pending_review} waiting
                </span>
              )}
            </h2>
            <QueueTable
              rows={data.pending}
              onReview={handleReview}
              emptyMsg="No badges pending review."
            />
          </div>

          {/* Recently reviewed — inline expand */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-njit-navy">Recently Reviewed</h2>
            <ReviewedTable
              rows={data.recently_reviewed}
              emptyMsg="No badges reviewed yet."
            />
          </div>
        </>
      )}
    </div>
  )
}
