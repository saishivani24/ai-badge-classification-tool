/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Three-tab badge submission page: structured form, JSON paste, and free text.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ingestBadge, classifyBadge } from '../services/api'
import {
  translateFormAnswers,
  translateAreaAnswer,
  translateVerificationAnswer,
  translateAudienceAnswer,
  AREA_OPTIONS,
  LDI_AUDIENCE_OPTIONS,
  AUDIENCE_OPTIONS,
  VERIFICATION_OPTIONS,
  PASS_SCORE_OPTIONS,
} from '../utils/formTranslator'

// ── Small shared UI primitives ────────────────────────────────────────────────

function Label({ children }) {
  return <label className="block text-sm font-medium text-gray-700 mb-1">{children}</label>
}

function Input({ error, ...props }) {
  return (
    <input
      className={`w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-njit-red
        ${error ? 'border-red-500' : 'border-gray-300'}`}
      {...props}
    />
  )
}

function Textarea({ error, rows = 4, ...props }) {
  return (
    <textarea
      rows={rows}
      className={`w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-njit-red
        ${error ? 'border-red-500' : 'border-gray-300'}`}
      {...props}
    />
  )
}

function FieldGroup({ label, children, helper }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      {children}
      {helper && <p className="text-xs text-gray-500 mt-1">{helper}</p>}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">
      {message}
    </div>
  )
}

function FieldError({ message }) {
  if (!message) return null
  return <p className="text-red-600 text-xs mt-1">{message}</p>
}

/**
 * Radio card group — renders a list of options as styled selectable cards.
 */
function RadioGroup({ options, value, onChange, name, error }) {
  return (
    <div className={`space-y-2 ${error ? 'ring-1 ring-red-400 rounded-lg p-1' : ''}`}>
      {options.map(opt => (
        <label
          key={opt}
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors select-none
            ${value === opt
              ? 'border-njit-red bg-red-50'
              : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'}`}
        >
          <input
            type="radio"
            name={name}
            value={opt}
            checked={value === opt}
            onChange={() => onChange(opt)}
            className="mt-0.5 accent-njit-red flex-shrink-0"
          />
          <span className="text-sm leading-snug text-gray-800">{opt}</span>
        </label>
      ))}
    </div>
  )
}

// ── BFS Confirmation Panel ────────────────────────────────────────────────────

/**
 * Follow-up question for a single missing field.
 * Translates the selected answer immediately and reports BFS fields to parent.
 */
function FollowupQuestion({ field, onAnswer }) {
  const [selected, setSelected] = useState('')

  const QUESTIONS = {
    issuer: {
      label: 'Which area of NJIT issued this badge?',
      options: AREA_OPTIONS,
      translate: translateAreaAnswer,
    },
    assessment_evaluator: {
      label: 'How is the earner evaluated for this badge?',
      options: VERIFICATION_OPTIONS,
      translate: translateVerificationAnswer,
    },
    audience_type: {
      label: 'Who earns this badge?',
      options: AUDIENCE_OPTIONS,
      translate: translateAudienceAnswer,
    },
  }

  const q = QUESTIONS[field]
  if (!q) return null

  function handleSelect(opt) {
    setSelected(opt)
    onAnswer(q.translate(opt))
  }

  return (
    <div>
      <p className="text-sm font-semibold text-gray-800 mb-2">{q.label}</p>
      <RadioGroup
        options={q.options}
        value={selected}
        onChange={handleSelect}
        name={`followup_${field}`}
      />
    </div>
  )
}

/**
 * Plain-language follow-up section shown inside BfsConfirmPanel.
 * inputMode='json': show for missing issuer and/or assessment_evaluator (max 2)
 * inputMode='free_text': show for fields in missing_signals (max 3)
 * inputMode='form': nothing shown
 */
function PlainLanguageFollowups({ bfs, inputMode, onAnswer }) {
  const missing = bfs.missing_signals || []
  const questions = []

  if (inputMode === 'json') {
    if (!bfs.issuer) questions.push('issuer')
    if (!bfs.assessment_evaluator) questions.push('assessment_evaluator')
  } else if (inputMode === 'free_text') {
    const priority = ['issuer', 'assessment_evaluator', 'audience_type']
    for (const f of priority) {
      if (missing.includes(f) && questions.length < 3) questions.push(f)
    }
  }

  if (questions.length === 0) return null

  return (
    <div className="border border-yellow-200 rounded-lg p-4 space-y-5 bg-yellow-50">
      <p className="text-sm font-medium text-yellow-900">
        Please answer {questions.length === 1 ? 'this question' : `these ${questions.length} questions`} to improve the classification:
      </p>
      {questions.map(q => (
        <FollowupQuestion key={q} field={q} onAnswer={onAnswer} />
      ))}
    </div>
  )
}

function BfsConfirmPanel({ bfs, inputMode, onConfirm, onFollowupChange, loading, showEmailStep = false }) {
  const [emailStep, setEmailStep] = useState(false)
  const [submitterEmail, setSubmitterEmail] = useState('')
  const [reviewerEmail, setReviewerEmail] = useState('')
  const [emailErrors, setEmailErrors] = useState({})

  const keyFields = [
    ['badge_title', 'Badge Title'],
    ['issuer', 'Issuer'],
    ['badge_description', 'Description'],
    ['earning_criteria_text', 'Earning Criteria'],
    ['assessment_required', 'Assessment Required'],
    ['assessment_type', 'Assessment Type'],
    ['assessment_evaluator', 'Assessment Evaluator'],
    ['canvas_course_code', 'Canvas Course Code'],
    ['canvas_sequence_number', 'Sequence Number'],
    ['audience_type', 'Audience Type'],
    ['bloom_level', 'Bloom Level'],
    ['self_declared_level', 'Declared Level'],
  ]
  const missing = bfs.missing_signals || []
  const needsFollowup = bfs.needs_followup_questions

  return (
    <div className="border border-gray-200 rounded-lg p-6 space-y-4">
      <h2 className="text-lg font-semibold text-njit-navy">Extracted Badge Fact Sheet</h2>

      {needsFollowup && (
        <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 rounded p-3 text-sm">
          <strong>Follow-up required:</strong> Some signals could not be extracted automatically.
          Please answer the questions below before classifying.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {keyFields.map(([field, label]) => {
          const val = bfs[field]
          const isMissing = missing.includes(field)
          const hasVal = val !== null && val !== undefined && val !== ''
          return (
            <div
              key={field}
              className={`rounded p-2 text-sm border
                ${isMissing ? 'bg-yellow-50 border-yellow-300' : 'bg-gray-50 border-gray-200'}`}
            >
              <span className="font-medium text-gray-600">{label}: </span>
              <span className={hasVal ? 'text-gray-900' : 'text-gray-400 italic'}>
                {hasVal ? String(val) : 'not detected'}
              </span>
              {isMissing && <span className="ml-2 text-yellow-700 font-semibold text-xs">⚠ missing</span>}
            </div>
          )
        })}
      </div>

      <PlainLanguageFollowups
        bfs={bfs}
        inputMode={inputMode}
        onAnswer={onFollowupChange}
      />

      {/* Email collection step for JSON paste mode */}
      {showEmailStep && emailStep ? (
        <div className="border border-gray-200 rounded-lg p-5 space-y-4 bg-gray-50">
          <div>
            <p className="text-base font-semibold text-njit-navy">Almost done! Where should we send updates?</p>
            <p className="text-sm text-gray-500 mt-0.5">The reviewer will check and confirm this classification.</p>
          </div>

          <FieldGroup label="Your email address *">
            <Input
              type="email"
              value={submitterEmail}
              error={emailErrors.submitter}
              onChange={e => { setSubmitterEmail(e.target.value); setEmailErrors(ev => ({ ...ev, submitter: '' })) }}
              placeholder="you@njit.edu"
            />
            <FieldError message={emailErrors.submitter} />
          </FieldGroup>

          <FieldGroup
            label="Reviewer email (optional)"
            helper="If provided, reviewer will be notified. Otherwise classification appears in reviewer dashboard."
          >
            <Input
              type="email"
              value={reviewerEmail}
              error={emailErrors.reviewer}
              onChange={e => { setReviewerEmail(e.target.value); setEmailErrors(ev => ({ ...ev, reviewer: '' })) }}
              placeholder="reviewer@njit.edu"
            />
            <FieldError message={emailErrors.reviewer} />
          </FieldGroup>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setEmailStep(false)}
              className="px-4 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-white"
            >
              ← Back
            </button>
            <button
              disabled={loading}
              onClick={() => {
                const errs = {}
                if (!submitterEmail.trim()) errs.submitter = 'Required'
                else if (!EMAIL_RE.test(submitterEmail)) errs.submitter = 'Valid email required'
                if (reviewerEmail.trim() && !EMAIL_RE.test(reviewerEmail)) errs.reviewer = 'Valid email required'
                if (Object.keys(errs).length) { setEmailErrors(errs); return }
                onConfirm({
                  submitter_email: submitterEmail.trim(),
                  reviewer_email: reviewerEmail.trim() || null,
                })
              }}
              className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
            >
              {loading ? 'Classifying…' : 'Submit for Review →'}
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={showEmailStep ? () => setEmailStep(true) : () => onConfirm()}
          disabled={loading}
          className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
        >
          {loading ? 'Classifying…' : 'Confirm & Classify →'}
        </button>
      )}
    </div>
  )
}

// ── Free Text Student Follow-up Panel ────────────────────────────────────────
//
// Shown instead of BfsConfirmPanel when input_type === "free_text".
// Asks plain-language student questions (max 3), merges answers, then
// calls classify immediately — no second confirmation round.

const _FT_Q1 = {
  label: 'Where did this activity or training take place at NJIT?',
  helper: 'Select the closest match — your reviewer will confirm.',
  signal: 'issuer',
  options: [
    { text: 'It was a professional development or continuing education program', fields: { issuer: 'LDI', audience_type: 'external_professional' } },
    { text: 'It was a student club, leadership, or involvement program',         fields: { issuer: 'OSIL', audience_type: 'njit_student' } },
    { text: 'It was in the Makerspace (3D printing, laser cutting, etc.)',        fields: { issuer: 'Makerspace', audience_type: 'njit_student' } },
    { text: 'It was part of a class or academic program',                         fields: { issuer: 'NCE', audience_type: 'njit_student' } },
    { text: 'It was an administrative requirement (visa, work authorization)',    fields: { issuer: 'OGI', audience_type: 'njit_student' } },
  ],
}

const _FT_Q2 = {
  label: 'How was your work or participation checked?',
  helper: 'Choose the option that best describes how you were evaluated.',
  signal: 'assessment_evaluator',
  options: [
    { text: 'I took an online quiz or test',                               fields: { assessment_evaluator: 'auto_assessed',  assessment_type: 'final_assessment' } },
    { text: 'A person watched me do something and said I passed',          fields: { assessment_evaluator: 'expert_scored',  expert_evaluation_required: true, assessment_type: 'practical' } },
    { text: 'I submitted a project or portfolio that someone reviewed',    fields: { assessment_evaluator: 'expert_scored',  expert_evaluation_required: true, assessment_type: 'portfolio' } },
    { text: 'I just showed up — no grading was required',                  fields: { assessment_evaluator: null, assessment_type: 'attendance', assessment_required: 'no' } },
  ],
}

// Q4 — shown only when level signal is genuinely missing.
// Student-reported level uses confidence Medium and source "student_reported".
const _FT_Q4 = {
  label: 'Where does this badge fit in your learning journey?',
  signal: 'self_declared_level',
  options: [
    {
      text: 'It was my first time learning about this topic',
      fields: { self_declared_level: 'Foundational', level_signal_source: 'student_reported' },
    },
    {
      text: 'I had some background and this built on what I knew',
      fields: { self_declared_level: 'Milestone', level_signal_source: 'student_reported' },
    },
    {
      text: 'This was the final or most advanced step in the program',
      fields: { self_declared_level: 'Terminal', level_signal_source: 'student_reported' },
    },
    // Reviewer handles Unknown level — never blocks classification
    { text: "Not sure — reviewer will confirm", fields: null },
  ],
}

function FreeTextFollowupPanel({ bfs, onClassify, loading }) {
  const missing = bfs.missing_signals || []

  // ── Suppression logic ────────────────────────────────────────────────────────
  const showQ1 = !bfs.issuer && missing.includes('issuer')
  const showQ2 = missing.includes('assessment_evaluator')
  const showQ3 = missing.includes('badge_title')
  // Q4 — level is genuinely unknown: no NLP level phrase extracted AND
  // no canvas_sequence_number or canvas_pathway_code to drive a structural level rule AND
  // the full description text does not already contain a recognisable level keyword that
  // the backend NLP will resolve at classify time.
  // NOTE: self_declared_level is always null at ingest time (NLP runs at classify time),
  // so we must scan bfs.badge_description directly to avoid always showing Q4.
  const _Q4_SUPPRESS_KEYWORDS = [
    // Foundational indicators
    'no prior experience', 'new to the topic', 'people who are new',
    'designed for people who are new', 'brand new', 'getting started',
    'beginners', 'beginner', 'entry level', 'entry-level', 'starting point',
    'introduction to', 'introductory', 'foundational', 'foundation-level',
    'foundation level', 'first course', 'first in the series', 'course 1',
    'part 1', 'level 1', 'awareness level',
    // Milestone / intermediate indicators
    'intermediate', 'building on', 'prior knowledge', 'prerequisite',
    'second course', 'course 2', 'part 2', 'level 2',
    // Terminal indicators
    'capstone', 'final course', 'last course', 'advanced', 'third course',
    'course 3', 'part 3', 'level 3', 'completing all', 'after completing',
  ]
  const _descLower = (bfs.badge_description || '').toLowerCase()
  const _levelInDesc = _Q4_SUPPRESS_KEYWORDS.some(kw => _descLower.includes(kw))
  const showQ4 = !bfs.self_declared_level
    && bfs.canvas_sequence_number == null
    && !bfs.canvas_pathway_code
    && !_levelInDesc

  // ── Question queue (built once from suppression flags) ───────────────────────
  const questionQueue = []
  if (showQ1) questionQueue.push('Q1')
  if (showQ2) questionQueue.push('Q2')
  if (showQ3) questionQueue.push('Q3')
  if (showQ4) questionQueue.push('Q4')

  // ── Answer state ─────────────────────────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState(0)
  const [q1, setQ1] = useState(null)   // selected option object
  const [q2, setQ2] = useState(null)
  const [titleText, setTitleText] = useState('')
  const [q4, setQ4] = useState(null)
  const [currentError, setCurrentError] = useState('')

  // ── Email collection step ────────────────────────────────────────────────────
  const [emailStep, setEmailStep] = useState(false)
  const [submitterEmail, setSubmitterEmail] = useState('')
  const [reviewerEmail, setReviewerEmail] = useState('')
  const [emailErrors, setEmailErrors] = useState({})

  // Summary fields — what the NLP already extracted.
  // assessment_type is an internal derived field — never shown as a student concern.
  const summaryFields = [
    ['issuer',           'Issuer'],
    ['audience_type',    'Audience Type'],
    ['badge_description','Description (first 120 chars)'],
  ]

  // ── buildMergedBfs (reads q1/q2/titleText/q4 — unchanged) ───────────────────
  function buildMergedBfs() {
    const extra = {}
    if (q1?.fields) Object.assign(extra, q1.fields)
    if (q2?.fields) Object.assign(extra, q2.fields)
    if (titleText.trim()) extra.badge_title = titleText.trim()
    // Q4 — student-reported level uses Medium confidence, not High.
    // "Not sure — reviewer will confirm" leaves self_declared_level null; reviewer handles it.
    if (q4?.fields) Object.assign(extra, q4.fields)

    // Context-aware Q2 override for "A person watched me do something and said I passed".
    // The default fields set expert_evaluation_required=true which fires S2R06 → Skill.
    // OSIL panels facilitate review, not expert skill scoring → override to prevent
    // misclassification as Skill. Makerspace/NCE keep expert_evaluation_required=true.
    const _WATCHED_TEXT = 'A person watched me do something and said I passed'
    if (q2?.text === _WATCHED_TEXT) {
      const effectiveIssuer = extra.issuer ?? bfs.issuer
      if (effectiveIssuer === 'OSIL') {
        extra.assessment_type = 'project_presentation'
        extra.assessment_evaluator = 'expert_scored'
        extra.expert_evaluation_required = false
      } else if (effectiveIssuer === 'Makerspace' || effectiveIssuer === 'NCE') {
        extra.assessment_type = 'practical'
        extra.assessment_evaluator = 'expert_scored'
        extra.expert_evaluation_required = true
      }
      // Unknown issuer: keep defaults (practical, expert_scored, expert_evaluation_required=true)
    }

    // Derive audience_type from issuer when not already set by Q1 answer or BFS.
    // This covers issuers detected by Layer 0 keyword matching on the backend
    // where Q1 was never shown (issuer already present in BFS).
    const effectiveIssuer = extra.issuer ?? bfs.issuer
    const effectiveAudience = extra.audience_type ?? bfs.audience_type
    if (!effectiveAudience && effectiveIssuer) {
      const _ISSUER_AUDIENCE = {
        OSIL:       'njit_student',
        Makerspace: 'njit_student',
        NCE:        'njit_student',
        OGI:        'njit_student',
        // LDI: left null — backend Layer 0 infers from faculty/professional context
      }
      if (_ISSUER_AUDIENCE[effectiveIssuer]) {
        extra.audience_type = _ISSUER_AUDIENCE[effectiveIssuer]
      }
    }

    // Remove from missing_signals any field we showed a question for — whether
    // the student answered it or left it blank.
    let updatedMissing = [...missing]
    if (showQ1) updatedMissing = updatedMissing.filter(s => s !== 'issuer')
    if (showQ2) updatedMissing = updatedMissing.filter(s => s !== 'assessment_evaluator')
    updatedMissing = updatedMissing.filter(s => s !== 'badge_title')
    if (showQ4) updatedMissing = updatedMissing.filter(s => s !== 'self_declared_level')

    // Defensive: if assessment_evaluator has been resolved (set to a non-null value
    // by Q2 answer or context-aware override), ensure it is not in missing_signals
    // regardless of how it was removed above. This prevents a stale missing_signals
    // entry from forcing confidence to Low on the backend.
    const resolvedEvaluator = extra.assessment_evaluator ?? bfs.assessment_evaluator
    if (resolvedEvaluator != null) {
      updatedMissing = updatedMissing.filter(s => s !== 'assessment_evaluator')
    }

    // Explicitly carry all Q2-derived assessment fields into the merged BFS so
    // the backend never sees null for a field the student already answered.
    const mergedAssessment = {}
    if (extra.assessment_evaluator != null)      mergedAssessment.assessment_evaluator      = extra.assessment_evaluator
    if (extra.expert_evaluation_required != null) mergedAssessment.expert_evaluation_required = extra.expert_evaluation_required
    if (extra.assessment_type != null)            mergedAssessment.assessment_type            = extra.assessment_type
    if (extra.assessment_required != null)        mergedAssessment.assessment_required        = extra.assessment_required
    // When student confirmed any form of assessment was performed, mark as required
    // so S2R05 (no-assessment → Souvenir) does not fire incorrectly.
    if (q2 && q2.fields && q2.fields.assessment_required !== 'no' && resolvedEvaluator != null) {
      mergedAssessment.assessment_required = mergedAssessment.assessment_required ?? 'yes'
    }

    return {
      ...bfs,
      ...extra,
      ...mergedAssessment,
      missing_signals: updatedMissing,
      needs_followup_questions: updatedMissing.length > 0,
    }
  }

  // ── Step navigation helpers ───────────────────────────────────────────────────
  const allDone = currentStep >= questionQueue.length

  // Display text for each answered question (shown in the summary row above current Q)
  function getAnswerSummary(qid) {
    switch (qid) {
      case 'Q1': return q1?.text || null
      case 'Q2': return q2?.text || null
      case 'Q3': return titleText.trim() || '(skipped)'
      case 'Q4': return q4?.text || '(skipped)'
      default:   return null
    }
  }

  // Advance to the next question; validate required questions first
  function handleContinue() {
    const qid = questionQueue[currentStep]
    if (qid === 'Q1' && !q1) {
      setCurrentError('Please select where this activity took place')
      return
    }
    if (qid === 'Q2' && !q2) {
      setCurrentError('Please select how your work was evaluated')
      return
    }
    setCurrentError('')
    setCurrentStep(s => s + 1)
  }

  // Skip Q3 without saving any typed text
  function handleSkipQ3() {
    setTitleText('')
    setCurrentError('')
    setCurrentStep(s => s + 1)
  }

  // ── Render question body ──────────────────────────────────────────────────────
  function renderQuestion(qid) {
    switch (qid) {
      case 'Q1':
        return (
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-1">{_FT_Q1.label}</p>
            <p className="text-xs text-gray-500 mb-2">{_FT_Q1.helper}</p>
            <RadioGroup
              options={_FT_Q1.options.map(o => o.text)}
              value={q1?.text || ''}
              onChange={txt => { setQ1(_FT_Q1.options.find(o => o.text === txt)); setCurrentError('') }}
              name="ft_q1"
              error={!!currentError}
            />
            <FieldError message={currentError} />
          </div>
        )
      case 'Q2':
        return (
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-1">{_FT_Q2.label}</p>
            <p className="text-xs text-gray-500 mb-2">{_FT_Q2.helper}</p>
            <RadioGroup
              options={_FT_Q2.options.map(o => o.text)}
              value={q2?.text || ''}
              onChange={txt => { setQ2(_FT_Q2.options.find(o => o.text === txt)); setCurrentError('') }}
              name="ft_q2"
              error={!!currentError}
            />
            <FieldError message={currentError} />
          </div>
        )
      case 'Q3':
        return (
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-1">
              What would you call this badge or achievement?
            </p>
            <p className="text-xs text-gray-500 mb-2">
              Optional — for example: Leadership Workshop, AI Training, Laser Cutting Certification
            </p>
            <Input
              value={titleText}
              onChange={e => setTitleText(e.target.value)}
              placeholder="e.g. Leadership Workshop"
            />
          </div>
        )
      case 'Q4':
        return (
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-2">{_FT_Q4.label}</p>
            <p className="text-xs text-gray-500 mb-2">
              Optional — helps us decide whether this is a beginner, intermediate, or advanced badge.
            </p>
            <RadioGroup
              options={_FT_Q4.options.map(o => o.text)}
              value={q4?.text || ''}
              onChange={txt => setQ4(_FT_Q4.options.find(o => o.text === txt))}
              name="ft_q4"
            />
          </div>
        )
      default:
        return null
    }
  }

  // ── Render Continue / Skip buttons for the active question ───────────────────
  function renderStepButtons(qid) {
    if (qid === 'Q3') {
      return (
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSkipQ3}
            className="px-4 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
          >
            Skip
          </button>
          <button
            onClick={handleContinue}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark text-sm"
          >
            Continue →
          </button>
        </div>
      )
    }
    return (
      <button
        onClick={handleContinue}
        className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark text-sm mt-1"
      >
        Continue →
      </button>
    )
  }

  const questionCount = questionQueue.length

  return (
    <div className="border border-gray-200 rounded-lg p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-njit-navy">Almost there!</h2>
        <p className="text-sm text-gray-600 mt-1">
          {questionCount > 0
            ? `We extracted what we could. Answer ${questionCount === 1 ? 'this quick question' : `these ${questionCount} quick questions`} to get a better classification.`
            : 'We extracted everything we need. Click Classify to continue.'}
        </p>
      </div>

      {/* What NLP already found */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {summaryFields.map(([field, label]) => {
          const raw = bfs[field]
          const hasVal = raw !== null && raw !== undefined && raw !== ''
          const display = hasVal
            ? (field === 'badge_description' ? String(raw).slice(0, 120) + (String(raw).length > 120 ? '…' : '') : String(raw))
            : null
          return (
            <div key={field} className="rounded p-2 text-sm border bg-gray-50 border-gray-200">
              <span className="font-medium text-gray-600">{label}: </span>
              <span className={display ? 'text-gray-900' : 'text-gray-400 italic'}>
                {display || 'not detected'}
              </span>
            </div>
          )
        })}
      </div>

      {/* Answered question summaries — one line per answered step */}
      {questionQueue.slice(0, currentStep).map((qid, idx) => (
        <div key={qid} className="flex items-center justify-between text-sm">
          <span className="text-gray-700">
            <span className="text-green-600 mr-1.5">✅</span>
            {getAnswerSummary(qid)}
          </span>
          <button
            onClick={() => { setCurrentError(''); setCurrentStep(idx) }}
            className="text-xs text-gray-400 hover:text-njit-red ml-4 underline flex-shrink-0"
          >
            Change
          </button>
        </div>
      ))}

      {/* Current active question — one at a time */}
      {!allDone && !emailStep && (
        <div className="space-y-3">
          {renderQuestion(questionQueue[currentStep])}
          {renderStepButtons(questionQueue[currentStep])}
        </div>
      )}

      {/* After all questions: email step or Classify button */}
      {allDone && (
        emailStep ? (
          <div className="border border-gray-200 rounded-lg p-5 space-y-4 bg-gray-50">
            <div>
              <p className="text-base font-semibold text-njit-navy">Almost done! Where should we send updates?</p>
              <p className="text-sm text-gray-500 mt-0.5">The reviewer will check and confirm this classification.</p>
            </div>

            <FieldGroup label="Your email address *">
              <Input
                type="email"
                value={submitterEmail}
                error={emailErrors.submitter}
                onChange={e => { setSubmitterEmail(e.target.value); setEmailErrors(ev => ({ ...ev, submitter: '' })) }}
                placeholder="you@njit.edu"
              />
              <FieldError message={emailErrors.submitter} />
            </FieldGroup>

            <FieldGroup
              label="Reviewer email (optional)"
              helper="If provided, reviewer will be notified. Otherwise classification appears in reviewer dashboard."
            >
              <Input
                type="email"
                value={reviewerEmail}
                error={emailErrors.reviewer}
                onChange={e => { setReviewerEmail(e.target.value); setEmailErrors(ev => ({ ...ev, reviewer: '' })) }}
                placeholder="reviewer@njit.edu"
              />
              <FieldError message={emailErrors.reviewer} />
            </FieldGroup>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setEmailStep(false)}
                className="px-4 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-white"
              >
                ← Back
              </button>
              <button
                disabled={loading}
                onClick={() => {
                  const errs = {}
                  if (!submitterEmail.trim()) errs.submitter = 'Required'
                  else if (!EMAIL_RE.test(submitterEmail)) errs.submitter = 'Valid email required'
                  if (reviewerEmail.trim() && !EMAIL_RE.test(reviewerEmail)) errs.reviewer = 'Valid email required'
                  if (Object.keys(errs).length) { setEmailErrors(errs); return }
                  onClassify(buildMergedBfs(), {
                    submitter_email: submitterEmail.trim(),
                    reviewer_email: reviewerEmail.trim() || null,
                  })
                }}
                className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
              >
                {loading ? 'Classifying…' : 'Submit for Review →'}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setEmailStep(true)}
            disabled={loading}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
          >
            Classify →
          </button>
        )
      )}
    </div>
  )
}

// ── Tab 1: Guided Form (replaces Proposal Form) ───────────────────────────────

const STEP_TITLES = [
  'Badge Identity',
  'Who Is This For',
  'Earning Criteria',
  'How Is It Verified',
  'Pathway',
  'Notifications',
]

const PATHWAY_OPTIONS = [
  'No — this badge stands alone',
  'Yes — it is one course in a series',
  'Yes — it is the final badge completing the whole series',
  'Not sure',
]

const PATHWAY_POSITION_OPTIONS = ['1st', '2nd', '3rd', '4th', 'Later']

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function GuidedForm({ onIngested }) {
  const [step, setStep] = useState(1)
  const [answers, setAnswers] = useState({
    badge_title: '',
    badge_description: '',
    area: '',
    area_other: '',
    ldi_audience: '',
    earning_criteria: '',
    verification: '',
    pass_score: '',
    pass_score_other: '',
    pathway: '',
    pathway_position: '',
    canvas_code: '',
    submitter_email: '',
    reviewer_email: '',
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  function set(field, val) {
    setAnswers(a => ({ ...a, [field]: val }))
    if (errors[field]) setErrors(e => ({ ...e, [field]: '' }))
  }

  function validateStep(s) {
    const e = {}
    if (s === 1) {
      if (answers.badge_title.trim().length < 5)
        e.badge_title = 'At least 5 characters required'
      if (answers.badge_description.trim().length < 50)
        e.badge_description = 'At least 50 characters required'
    }
    if (s === 2) {
      if (!answers.area) e.area = 'Please select an option'
      if (
        answers.area === 'Learning and Development / Continuing Education' &&
        !answers.ldi_audience
      )
        e.ldi_audience = 'Please select who will earn this badge'
    }
    if (s === 3) {
      if (answers.earning_criteria.trim().length < 30)
        e.earning_criteria = 'At least 30 characters required'
    }
    if (s === 4) {
      if (!answers.verification)
        e.verification = 'Please select how the earner is verified'
    }
    if (s === 5) {
      if (!answers.pathway) e.pathway = 'Please select an option'
      if (
        answers.pathway === 'Yes — it is one course in a series' &&
        !answers.pathway_position
      )
        e.pathway_position = 'Please select the position in the series'
    }
    if (s === 6) {
      if (!answers.submitter_email.trim()) e.submitter_email = 'Required'
      else if (!EMAIL_RE.test(answers.submitter_email))
        e.submitter_email = 'Valid email required'
      if (answers.reviewer_email.trim() && !EMAIL_RE.test(answers.reviewer_email))
        e.reviewer_email = 'Valid email required'
    }
    return e
  }

  function goNext() {
    const e = validateStep(step)
    if (Object.keys(e).length) { setErrors(e); return }
    setErrors({})
    setStep(s => s + 1)
  }

  function goBack() {
    setErrors({})
    setStep(s => s - 1)
  }

  async function handleSubmit() {
    const e = validateStep(6)
    if (Object.keys(e).length) { setErrors(e); return }
    setLoading(true)
    setApiError('')
    try {
      const fields = translateFormAnswers(answers)
      const bfs = await ingestBadge('form', fields)
      onIngested(bfs, 'form', {
        submitter_email: answers.submitter_email.trim(),
        reviewer_email: answers.reviewer_email.trim(),
      })
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const isLDI = answers.area === 'Learning and Development / Continuing Education'
  const totalSteps = 6

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm font-semibold text-njit-navy">
            Step {step} of {totalSteps}
          </span>
          <span className="text-sm text-gray-500">{STEP_TITLES[step - 1]}</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-njit-red transition-all duration-300 rounded-full"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      <ErrorBanner message={apiError} />

      {/* ── Step 1: Badge Identity ── */}
      {step === 1 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">What is this badge called?</p>

          <FieldGroup label="Badge Title *">
            <Input
              value={answers.badge_title}
              error={errors.badge_title}
              onChange={e => set('badge_title', e.target.value)}
              placeholder="e.g. AI Fundamentals"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.badge_title} />
              <span className={`text-xs ml-auto ${answers.badge_title.trim().length < 5 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.badge_title.trim().length} / 5 min
              </span>
            </div>
          </FieldGroup>

          <FieldGroup label="Badge Description *">
            <Textarea
              value={answers.badge_description}
              error={errors.badge_description}
              onChange={e => set('badge_description', e.target.value)}
              rows={5}
              placeholder="Describe what this badge represents and who it is for…"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.badge_description} />
              <span className={`text-xs ml-auto ${answers.badge_description.trim().length < 50 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.badge_description.trim().length} / 50 min
              </span>
            </div>
          </FieldGroup>
        </div>
      )}

      {/* ── Step 2: Who Is This For ── */}
      {step === 2 && (
        <div className="space-y-5">
          <p className="text-base font-semibold text-njit-navy">
            Which area of NJIT is this badge from?
          </p>

          <RadioGroup
            options={AREA_OPTIONS}
            value={answers.area}
            onChange={val => { set('area', val); set('ldi_audience', '') }}
            name="area"
            error={errors.area}
          />
          <FieldError message={errors.area} />

          {answers.area === 'Other' && (
            <div className="pl-2">
              <FieldGroup label="Please describe the issuing area:">
                <Input
                  value={answers.area_other}
                  onChange={e => set('area_other', e.target.value)}
                  placeholder="e.g. Center for Pre-College Programs"
                />
              </FieldGroup>
            </div>
          )}

          {isLDI && (
            <div className="mt-4 pl-2 border-l-2 border-njit-red space-y-3">
              <p className="text-sm font-semibold text-njit-navy">
                Who will earn this badge?
              </p>
              <RadioGroup
                options={LDI_AUDIENCE_OPTIONS}
                value={answers.ldi_audience}
                onChange={val => set('ldi_audience', val)}
                name="ldi_audience"
                error={errors.ldi_audience}
              />
              <FieldError message={errors.ldi_audience} />
            </div>
          )}
        </div>
      )}

      {/* ── Step 3: Earning Criteria ── */}
      {step === 3 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">
            What must someone do to earn this badge?
          </p>
          <FieldGroup
            helper='Describe the specific actions, activities, or requirements the earner must complete.'
          >
            <Textarea
              value={answers.earning_criteria}
              error={errors.earning_criteria}
              onChange={e => set('earning_criteria', e.target.value)}
              rows={7}
              placeholder="e.g. Attend the full workshop session and pass the final assessment with 80% or higher…"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.earning_criteria} />
              <span className={`text-xs ml-auto ${answers.earning_criteria.trim().length < 30 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.earning_criteria.trim().length} / 30 min
              </span>
            </div>
          </FieldGroup>
        </div>
      )}

      {/* ── Step 4: How Is It Verified ── */}
      {step === 4 && (
        <div className="space-y-5">
          <div>
            <p className="text-base font-semibold text-njit-navy mb-3">
              How is the earner's work checked?
            </p>
            <RadioGroup
              options={VERIFICATION_OPTIONS}
              value={answers.verification}
              onChange={val => set('verification', val)}
              name="verification"
              error={errors.verification}
            />
            <FieldError message={errors.verification} />
          </div>

          <div>
            <p className="text-sm font-semibold text-gray-700 mb-3">
              Is there a minimum pass score required?
            </p>
            <RadioGroup
              options={PASS_SCORE_OPTIONS}
              value={answers.pass_score}
              onChange={val => { set('pass_score', val); set('pass_score_other', '') }}
              name="pass_score"
            />
            {answers.pass_score === 'Other' && (
              <div className="mt-2 pl-2">
                <Input
                  value={answers.pass_score_other}
                  onChange={e => set('pass_score_other', e.target.value)}
                  placeholder="e.g. 75%"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Step 5: Pathway ── */}
      {step === 5 && (
        <div className="space-y-5">
          <div>
            <p className="text-base font-semibold text-njit-navy mb-3">
              Is this badge part of a learning series?
            </p>
            <RadioGroup
              options={PATHWAY_OPTIONS}
              value={answers.pathway}
              onChange={val => { set('pathway', val); set('pathway_position', '') }}
              name="pathway"
              error={errors.pathway}
            />
            <FieldError message={errors.pathway} />

            {answers.pathway === 'Yes — it is one course in a series' && (
              <div className="mt-3 pl-2 border-l-2 border-njit-red">
                <p className="text-sm font-semibold text-njit-navy mb-2">Which position?</p>
                <div className="flex flex-wrap gap-2">
                  {PATHWAY_POSITION_OPTIONS.map(pos => (
                    <button
                      key={pos}
                      type="button"
                      onClick={() => set('pathway_position', pos)}
                      className={`px-4 py-1.5 rounded-full text-sm border transition-colors
                        ${answers.pathway_position === pos
                          ? 'bg-njit-red text-white border-njit-red'
                          : 'border-gray-300 text-gray-700 hover:border-njit-red hover:text-njit-red'}`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
                <FieldError message={errors.pathway_position} />
              </div>
            )}
          </div>

          <FieldGroup
            label="Canvas course code (optional):"
            helper="Leave blank if you don't have this."
          >
            <Input
              value={answers.canvas_code}
              onChange={e => set('canvas_code', e.target.value)}
              placeholder="MCAI.002.03"
            />
          </FieldGroup>
        </div>
      )}

      {/* ── Step 6: Notifications ── */}
      {step === 6 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">
            Who should be notified about this classification?
          </p>

          <FieldGroup label="Your email address *">
            <Input
              type="email"
              value={answers.submitter_email}
              error={errors.submitter_email}
              onChange={e => set('submitter_email', e.target.value)}
              placeholder="you@njit.edu"
            />
            <FieldError message={errors.submitter_email} />
          </FieldGroup>

          <FieldGroup
            label="Reviewer email (optional)"
            helper="If provided, reviewer will be notified. Otherwise classification appears in reviewer dashboard."
          >
            <Input
              type="email"
              value={answers.reviewer_email}
              error={errors.reviewer_email}
              onChange={e => set('reviewer_email', e.target.value)}
              placeholder="reviewer@njit.edu"
            />
            <FieldError message={errors.reviewer_email} />
          </FieldGroup>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex items-center gap-3 pt-2">
        {step > 1 && (
          <button
            type="button"
            onClick={goBack}
            className="px-5 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
          >
            ← Back
          </button>
        )}
        {step < totalSteps && (
          <button
            type="button"
            onClick={goNext}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark text-sm"
          >
            Next →
          </button>
        )}
        {step === totalSteps && (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50 text-sm"
          >
            {loading ? 'Submitting…' : 'Submit Badge →'}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Tab 2: JSON Paste ─────────────────────────────────────────────────────────

function JsonPasteTab({ onIngested }) {
  const [raw, setRaw] = useState('')
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  function handleParse() {
    setParseError('')
    setParsed(null)
    try {
      const obj = JSON.parse(raw)
      setParsed(obj)
    } catch {
      setParseError('Invalid JSON — please check your input.')
    }
  }

  async function handleSubmit() {
    if (!raw.trim()) { setParseError('Paste JSON before submitting.'); return }
    setLoading(true)
    setApiError('')
    try {
      // Always parse fresh from raw — never rely on stale `parsed` state.
      // This is the correct pattern: const parsed = JSON.parse(text); ingestBadge("obv3_json", parsed)
      let jsonObj
      try {
        jsonObj = JSON.parse(raw)
      } catch {
        setParseError('Invalid JSON — please check your input.')
        setLoading(false)
        return
      }
      const bfs = await ingestBadge('obv3_json', jsonObj)
      onIngested(bfs, 'json')
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <ErrorBanner message={apiError} />
      <FieldGroup label="Paste OBv3 JSON">
        <Textarea
          value={raw}
          onChange={e => { setRaw(e.target.value); setParsed(null); setParseError('') }}
          rows={12}
          placeholder={'{\n  "@context": "https://purl.imsglobal.org/spec/ob/v3p0/...",\n  "name": "Badge Name",\n  ...\n}'}
          error={!!parseError}
        />
      </FieldGroup>

      {parseError && <p className="text-red-600 text-sm">{parseError}</p>}

      {parsed && (() => {
        // Extract summary fields from common OBv3 shapes
        const name = parsed.name || parsed.badge?.name || null
        const issuerRaw = parsed.issuer
        const issuerName = typeof issuerRaw === 'string'
          ? issuerRaw
          : (issuerRaw?.name || issuerRaw?.id || null)
        const achievementType = parsed.achievementType || parsed.badge?.achievementType || null
        const hasCriteria = !!(parsed.criteria || parsed.badge?.criteria || parsed.credentialSubject?.achievement?.criteria)
        const alignments = parsed.alignment || parsed.badge?.alignment || []
        const alignCount = Array.isArray(alignments) ? alignments.length : 0
        return (
          <div className="bg-green-50 border border-green-200 rounded p-4 text-sm space-y-2">
            <p className="font-semibold text-green-800">Valid JSON detected</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                ['Badge name', name],
                ['Issuer', issuerName],
                ['Achievement type', achievementType],
                ['Has criteria', hasCriteria ? 'Yes' : 'No'],
                ['Alignments', alignCount > 0 ? `${alignCount} found` : 'None'],
              ].map(([label, val]) => (
                <div key={label} className="rounded p-2 border bg-white border-green-200">
                  <span className="font-medium text-gray-600">{label}: </span>
                  <span className={val && val !== 'No' && val !== 'None' ? 'text-gray-900' : 'text-gray-400 italic'}>
                    {val ?? 'not detected'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })()}

      <div className="flex gap-3">
        <button
          onClick={handleParse}
          className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
        >
          Parse JSON
        </button>
        <button
          onClick={handleSubmit}
          disabled={!raw.trim() || loading}
          className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
        >
          {loading ? 'Submitting…' : 'Submit & Extract →'}
        </button>
      </div>
    </div>
  )
}

// ── Tab 3: Free Text ──────────────────────────────────────────────────────────

function FreeTextTab({ onIngested }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  async function handleSubmit() {
    if (!text.trim()) return
    setLoading(true)
    setApiError('')
    try {
      const bfs = await ingestBadge('free_text', { text })
      onIngested(bfs, 'free_text')
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <ErrorBanner message={apiError} />
      <FieldGroup label="Describe the badge in plain language">
        <Textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={12}
          placeholder="This badge is awarded to faculty who complete the AI for Education course series. Learners must pass the final assessment with 80% or higher…"
        />
      </FieldGroup>
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || loading}
        className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
      >
        {loading ? 'Submitting…' : 'Submit & Extract →'}
      </button>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const TABS = ['Proposal Form', 'JSON Paste', 'Free Text']

export default function SubmitBadge() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)
  const [bfs, setBfs] = useState(null)
  const [inputMode, setInputMode] = useState('form')
  const [followupValues, setFollowupValues] = useState({})
  const [submissionMeta, setSubmissionMeta] = useState({})
  const [classifying, setClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState('')

  function handleIngested(bfsData, mode, meta = {}) {
    // For free_text and json: NLP may not flag assessment_evaluator as missing even
    // when it is null. Add it here so follow-up question conditions work correctly.
    if ((mode === 'free_text' || mode === 'json') && bfsData.assessment_evaluator == null) {
      const ms = bfsData.missing_signals || []
      if (!ms.includes('assessment_evaluator')) {
        bfsData = { ...bfsData, missing_signals: [...ms, 'assessment_evaluator'] }
      }
    }
    setBfs(bfsData)
    setInputMode(mode)
    setFollowupValues({})
    setSubmissionMeta(meta)
    setClassifyError('')
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  // Remove fields from missing_signals that now have a resolved value.
  // Applied as a final cleanup step before every classifyBadge() call so that
  // stale missing_signals entries (added at ingest time or augmented by handleIngested)
  // do not force needs_followup_questions = true and drive confidence to Low.
  function cleanMissingSignals(bfsObj) {
    const fieldsToCheck = ['issuer', 'assessment_evaluator', 'audience_type', 'badge_title']
    let missing = bfsObj.missing_signals ? [...bfsObj.missing_signals] : []
    fieldsToCheck.forEach(field => {
      const val = bfsObj[field]
      if (val !== null && val !== undefined && val !== '') {
        missing = missing.filter(s => s !== field)
      }
    })
    return {
      ...bfsObj,
      missing_signals: missing,
      needs_followup_questions: missing.length > 0,
    }
  }

  // Accepts either a multi-field object or (field, val) for backward compat
  function handleFollowupChange(fieldsOrField, val) {
    if (typeof fieldsOrField === 'object' && fieldsOrField !== null) {
      setFollowupValues(v => ({ ...v, ...fieldsOrField }))
    } else {
      setFollowupValues(v => ({ ...v, [fieldsOrField]: val }))
    }
  }

  // Free-text path: receives merged BFS + email meta from FreeTextFollowupPanel.
  // Navigates to SubmissionConfirmation when emails are present.
  async function handleFreeTextClassify(mergedBfs, emailMeta = {}) {
    setClassifying(true)
    setClassifyError('')
    try {
      const cleanedBfs = cleanMissingSignals(mergedBfs)
      const result = await classifyBadge(cleanedBfs, emailMeta)
      const logId = result.governance.log_id
      if (emailMeta.submitter_email || emailMeta.reviewer_email) {
        navigate('/submit/confirmation', {
          state: {
            badgeTitle: result.badge_title || cleanedBfs.badge_title,
            submitterEmail: emailMeta.submitter_email,
            reviewerEmail: emailMeta.reviewer_email,
            logId,
          },
        })
      } else {
        navigate(`/review/${logId}`, { state: { result, bfs: cleanedBfs } })
      }
    } catch (err) {
      setClassifyError(err.message)
    } finally {
      setClassifying(false)
    }
  }

  async function handleConfirmClassify(emailMeta = {}) {
    setClassifying(true)
    setClassifyError('')
    try {
      const enrichedBfs = cleanMissingSignals({ ...bfs, ...followupValues })
      const meta = { ...submissionMeta, ...emailMeta }
      const result = await classifyBadge(enrichedBfs, meta)
      const logId = result.governance.log_id
      if (meta.submitter_email || meta.reviewer_email) {
        navigate('/submit/confirmation', {
          state: {
            badgeTitle: result.badge_title || enrichedBfs.badge_title,
            submitterEmail: meta.submitter_email,
            reviewerEmail: meta.reviewer_email,
            logId,
          },
        })
      } else {
        navigate(`/review/${logId}`, { state: { result, bfs: enrichedBfs } })
      }
    } catch (err) {
      setClassifyError(err.message)
    } finally {
      setClassifying(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-njit-navy">Submit Badge for Classification</h1>
        <p className="text-gray-600 text-sm mt-1">
          Choose an input method below. The system will extract signals and recommend a classification.
        </p>
      </div>

      {/* Tab headers */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-0">
          {TABS.map((tab, i) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(i); setBfs(null) }}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors
                ${activeTab === i
                  ? 'border-njit-red text-njit-red'
                  : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 0 && <GuidedForm onIngested={handleIngested} />}
        {activeTab === 1 && <JsonPasteTab onIngested={handleIngested} />}
        {activeTab === 2 && <FreeTextTab onIngested={handleIngested} />}
      </div>

      {/* Post-ingest panel — student follow-ups for free text, BFS confirm for others */}
      {bfs && (
        <>
          <hr className="border-gray-200" />
          <ErrorBanner message={classifyError} />
          {inputMode === 'free_text' ? (
            <FreeTextFollowupPanel
              bfs={bfs}
              onClassify={handleFreeTextClassify}
              loading={classifying}
            />
          ) : (
            <BfsConfirmPanel
              bfs={bfs}
              inputMode={inputMode}
              onConfirm={handleConfirmClassify}
              onFollowupChange={handleFollowupChange}
              loading={classifying}
              showEmailStep={inputMode === 'json'}
            />
          )}
        </>
      )}
    </div>
  )
}
