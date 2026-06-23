"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

NLP Layer 1 — Exact phrase matching.

All phrases are case-insensitive exact substring matches.
Dictionaries are from docs/nlp-phrase-dictionary.md — do not modify without
updating docs/nlp-phrase-dictionary.md.

PhraseExtractor applies all dictionaries to a BFS and returns
the updated BFS with signal fields populated.

Matching rules:
- Phrases are sorted longest-first so the most specific phrase wins.
  ("foundation-level badge" beats "foundation-level")
- For LEVEL_PHRASES: word-boundary matching (EC17); negation-aware (EC18);
  all matches collected to detect conflicts (EC19); first non-negated
  match (longest) wins.
- For ASSESSMENT_PHRASES: multiple matches allowed (type + threshold).
- For AUDIENCE_PHRASES: first match wins.
- For PURPOSE_PHRASES: multiple matches allowed (purpose + workflow).
"""

import re

from app.models.badge_fact_sheet import BadgeFactSheet

# ---------------------------------------------------------------------------
# EC18 — Negation words checked before a matched level phrase
# ---------------------------------------------------------------------------
NEGATION_WORDS: frozenset[str] = frozenset([
    "not", "no", "never", "without", "non",
    "doesn't", "don't", "isn't", "aren't", "wasn't", "weren't",
    "cannot", "can't", "couldn't", "won't", "wouldn't",
])


def phrase_matches(phrase: str, text: str) -> "re.Match[str] | None":
    """
    EC17 — Word-boundary-aware matching for level phrases.

    Returns the first Match object if `phrase` appears in `text` as a
    whole-word sequence (\\b anchors on both ends), else None.
    Always case-insensitive.
    """
    pattern = r'\b' + re.escape(phrase) + r'\b'
    return re.search(pattern, text, re.IGNORECASE)


def is_negated(text: str, match_start: int, window: int = 10) -> bool:
    """
    EC18 — Negation detection.

    Inspects the `window` words immediately before `match_start` in `text`.
    Returns True if any negation word is found in that window.
    Punctuation attached to words is stripped before comparison.
    """
    prefix = text[:match_start]
    words = prefix.split()
    recent = words[-window:]
    return any(w.strip(".,;:!?\"'()") in NEGATION_WORDS for w in recent)


# ---------------------------------------------------------------------------
# Past-context blocking — prevents level phrases from firing when the phrase
# appears as a description of a prerequisite or already-completed activity
# rather than as a declaration of the badge's own level.
#
# Example blocked:
#   "students who have already completed the introductory series"
#   → "introductory" is a past-completed thing, not this badge's level.
# ---------------------------------------------------------------------------
PAST_CONTEXT_WORDS: list[str] = [
    "completed", "finishing", "finished", "already",
    "done with", "having finished", "after completing",
    "having completed",
    # "who have/has" alone is too broad — "who have never done" is a beginner
    # audience description, not a past-completion context. Use specific forms.
    "who have already", "who have completed", "who have finished",
    "who has already", "who has completed", "who has finished",
]


def is_past_context(text: str, match_start: int, window: int = 8) -> bool:
    """
    Past-context detection.

    Inspects the `window` words immediately before `match_start` in `text`.
    Returns True if any past-context phrase appears in that window, indicating
    the level phrase describes a completed prerequisite rather than this badge.
    Multi-word phrases are checked against the joined window string so that
    "who have" and "after completing" are detected correctly.
    """
    words_before = text[:match_start].split()
    recent_words = [w.lower().strip(".,;:!?\"'()") for w in words_before[-window:]]
    joined = " ".join(recent_words)
    return any(past in joined for past in PAST_CONTEXT_WORDS)


# ---------------------------------------------------------------------------
# LEVEL_PHRASES
# Tuple: (level_value, confidence)
# ---------------------------------------------------------------------------
LEVEL_PHRASES: dict[str, tuple[str, str]] = {
    # Foundational
    "foundation-level badge":            ("Foundational", "High"),
    "this foundation-level":             ("Foundational", "High"),
    "foundation-level":                  ("Foundational", "High"),
    "foundation level":                  ("Foundational", "High"),
    "foundational understanding":        ("Foundational", "High"),
    "foundational knowledge":            ("Foundational", "High"),
    "lays the groundwork":               ("Foundational", "High"),
    "build essential":                   ("Foundational", "High"),
    "equips emerging leaders":           ("Foundational", "High"),
    "readiness to begin":                ("Foundational", "High"),
    "introduction to":                   ("Foundational", "Medium"),
    "introductory":                      ("Foundational", "High"),
    "beginner":                          ("Foundational", "High"),
    "entry-level":                       ("Foundational", "High"),
    "entry level":                       ("Foundational", "High"),
    "no prior experience":               ("Foundational", "High"),
    "no experience required":            ("Foundational", "High"),
    "getting started":                   ("Foundational", "Medium"),
    "first step":                        ("Foundational", "Medium"),
    "fundamentals of":                   ("Foundational", "High"),
    "basics of":                         ("Foundational", "Medium"),
    "first in":                          ("Foundational", "Medium"),
    "first course":                      ("Foundational", "High"),
    # Conversational / plain-language Foundational phrases
    "never done this before":            ("Foundational", "High"),
    "beginning of the journey":          ("Foundational", "Medium"),
    "starting their journey":            ("Foundational", "Medium"),
    "starting point":                    ("Foundational", "Medium"),
    "entry point":                       ("Foundational", "Medium"),
    "getting started with":              ("Foundational", "Medium"),
    "just beginning to":                 ("Foundational", "Medium"),
    "just starting":                     ("Foundational", "Medium"),
    "new to this":                       ("Foundational", "Medium"),
    "first time":                        ("Foundational", "Medium"),
    "starting out":                      ("Foundational", "Medium"),
    "beginner level":                    ("Foundational", "Medium"),
    "just learning":                     ("Foundational", "Medium"),
    "learning the ropes":                ("Foundational", "Medium"),
    "no background":                     ("Foundational", "High"),
    "no previous skills":                ("Foundational", "High"),
    "first timers":                      ("Foundational", "Medium"),
    "never done this":                   ("Foundational", "High"),
    "step one":                          ("Foundational", "Medium"),
    "step 1":                            ("Foundational", "Medium"),
    "part one":                          ("Foundational", "Medium"),
    "part 1":                            ("Foundational", "Medium"),
    "basic concepts":                    ("Foundational", "Medium"),
    "basic skills":                      ("Foundational", "Medium"),
    "fundamental concepts":              ("Foundational", "Medium"),
    "fundamental skills":                ("Foundational", "Medium"),
    "groundwork":                        ("Foundational", "Medium"),
    "building blocks":                   ("Foundational", "Medium"),
    "newcomers welcome":                 ("Foundational", "Medium"),
    "beginners welcome":                 ("Foundational", "Medium"),
    "open to beginners":                 ("Foundational", "Medium"),
    "no experience necessary":             ("Foundational", "High"),
    "experience not required":             ("Foundational", "High"),
    "no prerequisites":                  ("Foundational", "High"),
    "prerequisites not required":          ("Foundational", "High"),
    "open to all levels":                ("Foundational", "Medium"),
    "all skill levels":                  ("Foundational", "Medium"),
    "open to everyone":                  ("Foundational", "Low"),
    "no prior knowledge":                ("Foundational", "High"),
    "prior knowledge not required":      ("Foundational", "High"),
    "from scratch":                      ("Foundational", "Medium"),
    "from the ground up":                ("Foundational", "Medium"),
    "zero to hero":                      ("Foundational", "Medium"),
    "zero experience":                   ("Foundational", "High"),
    "for dummies":                       ("Foundational", "Medium"),
    "101":                               ("Foundational", "Medium"),
    "level one":                         ("Foundational", "Medium"),
    "level 1":                           ("Foundational", "Medium"),
    "tier one":                          ("Foundational", "Medium"),
    "tier 1":                            ("Foundational", "Medium"),
    "stage one":                         ("Foundational", "Medium"),
    "stage 1":                           ("Foundational", "Medium"),
    "phase one":                         ("Foundational", "Medium"),
    "phase 1":                           ("Foundational", "Medium"),
    "module one":                        ("Foundational", "Medium"),
    "module 1":                          ("Foundational", "Medium"),
    "unit one":                          ("Foundational", "Medium"),
    "unit 1":                            ("Foundational", "Medium"),
    "lesson one":                        ("Foundational", "Medium"),
    "lesson 1":                          ("Foundational", "Medium"),
    "chapter one":                       ("Foundational", "Medium"),
    "chapter 1":                         ("Foundational", "Medium"),
    "section one":                       ("Foundational", "Medium"),
    "section 1":                         ("Foundational", "Medium"),

    # Milestone
    "building on foundational concepts": ("Milestone", "High"),
    "building on the foundational series": ("Milestone", "High"),
    "building on foundational":          ("Milestone", "High"),
    "expanding on the foundational series": ("Milestone", "High"),
    "expanding on the foundational":     ("Milestone", "High"),
    "intermediate-level":                ("Milestone", "High"),
    "intermediate credential":           ("Milestone", "High"),
    "intermediate level":                ("Milestone", "High"),
    "deepens skills":                    ("Milestone", "High"),
    "deepens understanding":             ("Milestone", "High"),
    "deepens knowledge":                 ("Milestone", "High"),
    "advances skills":                   ("Milestone", "High"),
    "advances understanding":            ("Milestone", "High"),
    "builds upon":                       ("Milestone", "High"),
    "prior knowledge required":          ("Milestone", "High"),
    "second course":                     ("Milestone", "High"),
    "second in":                         ("Milestone", "High"),
    "continues from":                    ("Milestone", "High"),
    # Plain-language Milestone phrases
    "more advanced than the first":      ("Milestone", "High"),
    "second part":                       ("Milestone", "High"),
    "building on what":                  ("Milestone", "Medium"),
    "continuing from":                   ("Milestone", "Medium"),
    "following up on":                   ("Milestone", "Medium"),
    "taking it further":                 ("Milestone", "Medium"),
    # ---- Student language for Milestone ----
    "level up":                          ("Milestone", "Medium"),
    "moving up":                         ("Milestone", "Medium"),
    "moving forward":                    ("Milestone", "Medium"),
    "progressing to":                    ("Milestone", "Medium"),
    "taking the next step":              ("Milestone", "Medium"),
    "step two":                          ("Milestone", "Medium"),
    "step 2":                            ("Milestone", "Medium"),
    "part two":                          ("Milestone", "Medium"),
    "part 2":                            ("Milestone", "Medium"),
    "second step":                       ("Milestone", "Medium"),
    "next phase":                        ("Milestone", "Medium"),
    "next stage":                        ("Milestone", "Medium"),
    "next level":                        ("Milestone", "Medium"),
    "intermediate skills":               ("Milestone", "High"),
    "intermediate course":               ("Milestone", "High"),
    "intermediate badge":                ("Milestone", "High"),
    "intermediate module":               ("Milestone", "High"),
    "advanced beginner":                 ("Milestone", "Medium"),
    "beyond the basics":                 ("Milestone", "Medium"),
    "beyond basics":                     ("Milestone", "Medium"),
    "not beginner":                      ("Milestone", "Medium"),
    "not a beginner":                    ("Milestone", "Medium"),
    "some experience":                   ("Milestone", "Medium"),
    "some background":                   ("Milestone", "Medium"),
    "prior experience":                  ("Milestone", "High"),
    "previous experience":               ("Milestone", "High"),
    "prior knowledge":                   ("Milestone", "High"),
    "previous knowledge":                ("Milestone", "High"),
    "already know":                      ("Milestone", "Medium"),
    "already familiar":                  ("Milestone", "Medium"),
    "already understand":                ("Milestone", "Medium"),
    "assumes knowledge":                 ("Milestone", "High"),
    "assumes understanding":             ("Milestone", "High"),
    "assumes familiarity":               ("Milestone", "High"),
    "prerequisite course":               ("Milestone", "High"),
    "prerequisite badge":                ("Milestone", "High"),
    "prerequisite module":               ("Milestone", "High"),
    "required prerequisite":             ("Milestone", "High"),
    "must complete first":               ("Milestone", "High"),
    "must complete before":              ("Milestone", "High"),
    "builds on":                         ("Milestone", "High"),
    "building on":                       ("Milestone", "High"),
    "building upon":                     ("Milestone", "High"),
    "expand on":                         ("Milestone", "Medium"),
    "expand upon":                       ("Milestone", "Medium"),
    "expanding on":                      ("Milestone", "Medium"),
    "deepen skills":                     ("Milestone", "High"),
    "deepen understanding":              ("Milestone", "High"),
    "deepen knowledge":                  ("Milestone", "High"),
    "advance skills":                    ("Milestone", "High"),
    "advance knowledge":                 ("Milestone", "High"),
    "further develop":                   ("Milestone", "Medium"),
    "further development":                 ("Milestone", "Medium"),
    "more advanced":                     ("Milestone", "Medium"),
    "more complex":                      ("Milestone", "Medium"),
    "more challenging":                  ("Milestone", "Medium"),
    "more difficult":                    ("Milestone", "Medium"),
    "more sophisticated":                ("Milestone", "Medium"),
    "higher level":                      ("Milestone", "Medium"),
    "level two":                         ("Milestone", "Medium"),
    "level 2":                           ("Milestone", "Medium"),
    "tier two":                          ("Milestone", "Medium"),
    "tier 2":                            ("Milestone", "Medium"),
    "stage two":                         ("Milestone", "Medium"),
    "stage 2":                           ("Milestone", "Medium"),
    "phase two":                         ("Milestone", "Medium"),
    "phase 2":                           ("Milestone", "Medium"),
    "module two":                        ("Milestone", "Medium"),
    "module 2":                          ("Milestone", "Medium"),
    "course two":                        ("Milestone", "Medium"),
    "course 2":                          ("Milestone", "Medium"),
    "continuing education":              ("Milestone", "Medium"),
    "continuing development":            ("Milestone", "Medium"),
    "ongoing development":               ("Milestone", "Medium"),
    "ongoing learning":                  ("Milestone", "Medium"),
    "professional development":            ("Milestone", "Medium"),
    "career development":                ("Milestone", "Medium"),
    "skill advancement":                 ("Milestone", "Medium"),
    "skill progression":                 ("Milestone", "Medium"),
    "career advancement":                ("Milestone", "Medium"),
    "upskilling":                        ("Milestone", "Medium"),
    "reskilling":                        ("Milestone", "Medium"),

    # Terminal
    "after completing the foundational and intermediate": ("Terminal", "High"),
    "comprehensive foundational understanding across all": ("Terminal", "High"),
    "comprehensive achievement":         ("Terminal", "High"),
    "demonstrates comprehensive":        ("Terminal", "High"),
    "demonstrates mastery":              ("Terminal", "High"),
    "completion of all":                 ("Terminal", "High"),
    "upon completing all":               ("Terminal", "High"),
    "culminating the":                   ("Terminal", "High"),
    "completes the series":              ("Terminal", "High"),
    "final course":                      ("Terminal", "High"),
    "capstone":                          ("Terminal", "High"),
    # Plain-language Terminal phrases
    "everything comes together":         ("Terminal", "High"),
    "putting it all together":           ("Terminal", "High"),
    "completing the program":            ("Terminal", "High"),
    "finishing the series":              ("Terminal", "High"),
    "end of the program":                ("Terminal", "High"),
    "last course":                       ("Terminal", "High"),
    "final step":                        ("Terminal", "Medium"),
    "the last thing needed":             ("Terminal", "Medium"),
    # ---- Student language for Terminal ----
    "capstone project":                  ("Terminal", "High"),
    "capstone course":                   ("Terminal", "High"),
    "capstone badge":                    ("Terminal", "High"),
    "final stage":                       ("Terminal", "Medium"),
    "final phase":                       ("Terminal", "Medium"),
    "final level":                       ("Terminal", "Medium"),
    "culminating project":               ("Terminal", "High"),
    "culminating course":                ("Terminal", "High"),
    "culminating experience":            ("Terminal", "High"),
    "culminating achievement":           ("Terminal", "High"),
    "culmination of":                    ("Terminal", "High"),
    "ultimate achievement":              ("Terminal", "High"),
    "highest level":                     ("Terminal", "High"),
    "top level":                         ("Terminal", "High"),
    "expert level":                      ("Terminal", "High"),
    "expert status":                     ("Terminal", "High"),
    "mastery level":                     ("Terminal", "High"),
    "mastery badge":                     ("Terminal", "High"),
    "mastery achievement":               ("Terminal", "High"),
    "complete mastery":                  ("Terminal", "High"),
    "full mastery":                      ("Terminal", "High"),
    "total mastery":                     ("Terminal", "High"),
    "complete proficiency":              ("Terminal", "High"),
    "full proficiency":                  ("Terminal", "High"),
    "total proficiency":                 ("Terminal", "High"),
    "comprehensive understanding":       ("Terminal", "High"),
    "comprehensive knowledge":           ("Terminal", "High"),
    "comprehensive skills":              ("Terminal", "High"),
    "well rounded":                      ("Terminal", "Medium"),
    "well-rounded":                      ("Terminal", "Medium"),
    "fully prepared":                    ("Terminal", "Medium"),
    "fully qualified":                   ("Terminal", "High"),
    "fully trained":                     ("Terminal", "High"),
    "completely trained":                ("Terminal", "High"),
    "thoroughly trained":                ("Terminal", "High"),
    "wrap up":                           ("Terminal", "Medium"),
    "wrapping up":                       ("Terminal", "Medium"),
    "tied together":                     ("Terminal", "Medium"),
    "ties together":                     ("Terminal", "Medium"),
    "bring it all together":             ("Terminal", "Medium"),
    "bringing it all together":          ("Terminal", "Medium"),
    "synthesize knowledge":              ("Terminal", "Medium"),
    "synthesize skills":                 ("Terminal", "Medium"),
    "synthesis of":                      ("Terminal", "Medium"),
    "integrate all":                     ("Terminal", "Medium"),
    "integrate everything":              ("Terminal", "Medium"),
    "integration of":                    ("Terminal", "Medium"),
    "complete program":                  ("Terminal", "High"),
    "complete series":                   ("Terminal", "High"),
    "complete curriculum":               ("Terminal", "High"),
    "complete pathway":                  ("Terminal", "High"),
    "end of the journey":                ("Terminal", "Medium"),
    "end of the road":                   ("Terminal", "Medium"),
    "end of the path":                   ("Terminal", "Medium"),
    "final destination":                 ("Terminal", "Medium"),
    "graduation level":                  ("Terminal", "High"),
    "graduation badge":                  ("Terminal", "High"),
    "graduation achievement":            ("Terminal", "High"),
    "terminal course":                   ("Terminal", "High"),
    "terminal badge":                    ("Terminal", "High"),
    "terminal achievement":              ("Terminal", "High"),
    "terminal level":                    ("Terminal", "High"),
    "senior level":                      ("Terminal", "High"),
    "advanced level":                    ("Terminal", "Medium"),
    "top tier":                        ("Terminal", "High"),
    "highest tier":                      ("Terminal", "High"),
    "ultimate level":                    ("Terminal", "High"),
    "peak achievement":                  ("Terminal", "High"),
    "final achievement":                 ("Terminal", "High"),
    "crowning achievement":              ("Terminal", "High"),
    "final certification":               ("Terminal", "High"),
    "terminal certification":            ("Terminal", "High"),
    "program completion":                ("Terminal", "High"),
    "series completion":                 ("Terminal", "High"),
    "pathway completion":                ("Terminal", "High"),
    "curriculum completion":             ("Terminal", "High"),
    "all requirements met":              ("Terminal", "High"),
    "all courses completed":             ("Terminal", "High"),
    "all modules completed":             ("Terminal", "High"),
    "all badges earned":                 ("Terminal", "High"),
    "sum of all parts":                  ("Terminal", "Medium"),
    "greater than the sum":              ("Terminal", "Medium"),
    "combined knowledge":                ("Terminal", "Medium"),
    "combined skills":                   ("Terminal", "Medium"),
}

# Pre-sorted: longest phrase first so the most specific match wins
_LEVEL_PHRASES_SORTED: list[tuple[str, str, str]] = sorted(
    ((phrase, level, conf) for phrase, (level, conf) in LEVEL_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# ASSESSMENT_PHRASES
# Tuple: (type_key, threshold_or_None, confidence)
#
# type_key values and how they're used:
#   "final_assessment" | "knowledge_checks" | "pre_post_assessment" |
#   "project_presentation" | "attendance" | "module_completion" | "practical"
#     → sets assessment_type
#   "expert_scored"
#     → sets assessment_evaluator
#   "compliance"
#     → sets badge_purpose (handled also by PURPOSE_PHRASES)
#   "downstream_workflow"
#     → signals a downstream workflow exists (handled also by PURPOSE_PHRASES)
# ---------------------------------------------------------------------------
ASSESSMENT_PHRASES: dict[str, tuple[str, str | None, str]] = {
    # ---- Final assessment — original strict phrases ----
    "passing the final assessment with an 80% or higher": ("final_assessment", "80%", "High"),
    "passing the final assessment with an 90% or higher": ("final_assessment", "90%", "High"),

    # ---- Final assessment — flexible "pass the/a final X with Y%" variants ----
    # Longer phrases first so the most specific match wins in sorted order.
    "pass the final assessment with 80%":  ("final_assessment", "80%", "High"),
    "pass the final assessment with 90%":  ("final_assessment", "90%", "High"),
    "pass a final assessment with 80%":    ("final_assessment", "80%", "High"),
    "pass a final assessment with 90%":    ("final_assessment", "90%", "High"),
    "pass the final quiz with 80%":        ("final_assessment", "80%", "High"),
    "pass the final exam with 80%":        ("final_assessment", "80%", "High"),

    # ---- Score + explicit percentage ----
    "80% or higher to earn":               ("final_assessment", "80%", "High"),
    "80% or better":                       ("final_assessment", "80%", "High"),
    "90% or higher to earn":               ("final_assessment", "90%", "High"),
    "90% or better":                       ("final_assessment", "90%", "High"),
    "score 80% or higher":                 ("final_assessment", "80%", "High"),
    "score 90% or higher":                 ("final_assessment", "90%", "High"),
    "score of 80":                         ("final_assessment", "80%", "High"),
    "score of 90":                         ("final_assessment", "90%", "High"),

    # Short bare-percentage phrases — lower specificity, useful as fallback.
    # Longer phrases above will win when both appear in the same text.
    "90% or higher":                       ("final_assessment", "90%", "High"),
    "80% or higher":                       ("final_assessment", "80%", "High"),

    # ---- Knowledge checks ----
    "passing knowledge checks with an 80% or higher":    ("knowledge_checks", "80%", "High"),
    "passing knowledge checks with a 80% or higher":     ("knowledge_checks", "80%", "High"),

    # ---- Pre/post assessments ----
    "pre- and post-assessment":  ("pre_post_assessment", None, "High"),
    "pre and post assessment":   ("pre_post_assessment", None, "High"),

    # ---- Project / presentation ----
    "capstone project and present": ("project_presentation", None, "High"),

    # ---- Attendance ----
    "attend all sessions":        ("attendance", None, "High"),
    "attend the full":            ("attendance", None, "High"),
    "attended the full":          ("attendance", None, "High"),
    "full attendance":            ("attendance", None, "High"),

    # ---- Compliance / downstream ----
    "mandatory to apply":         ("compliance", None, "High"),
    "required to apply":          ("compliance", None, "High"),
    "share their digital badge to": ("downstream_workflow", None, "High"),

    # ---- Module / practical ----
    "module quizzes":             ("module_completion", None, "Medium"),
    "in person practical":        ("practical", None, "High"),
    "in-person practical":        ("practical", None, "High"),

    # ---- Expert scored ----
    "expert-verified":            ("expert_scored", None, "High"),
    "graded by instructor":       ("expert_scored", None, "High"),
    "reviewed by mentor":         ("expert_scored", None, "High"),
    "evaluated by":               ("expert_scored", None, "Medium"),
    "assessed by":                ("expert_scored", None, "Medium"),
    # ---- Student language for assessment ----
    "final exam":                 ("final_assessment", None, "High"),
    "final test":                 ("final_assessment", None, "High"),
    "final quiz":                 ("final_assessment", None, "High"),
    "end of course exam":         ("final_assessment", None, "High"),
    "end of course test":         ("final_assessment", None, "High"),
    "comprehensive exam":         ("final_assessment", None, "High"),
    "comprehensive test":         ("final_assessment", None, "High"),
    "comprehensive quiz":         ("final_assessment", None, "High"),
    "summative assessment":       ("final_assessment", None, "High"),
    "summative evaluation":       ("final_assessment", None, "High"),
    "cumulative exam":            ("final_assessment", None, "High"),
    "cumulative test":            ("final_assessment", None, "High"),
    "checkpoint quiz":            ("knowledge_checks", None, "High"),
    "module quiz":                ("knowledge_checks", None, "High"),
    "section quiz":               ("knowledge_checks", None, "High"),
    "unit quiz":                  ("knowledge_checks", None, "High"),
    "weekly quiz":                ("knowledge_checks", None, "High"),
    "chapter quiz":               ("knowledge_checks", None, "High"),
    "quick check":                ("knowledge_checks", None, "High"),
    "comprehension check":        ("knowledge_checks", None, "High"),
    "understanding check":        ("knowledge_checks", None, "High"),
    "mastery check":              ("knowledge_checks", None, "High"),
    "skill check":                ("knowledge_checks", None, "High"),
    "progress check":             ("knowledge_checks", None, "High"),
    "learning check":             ("knowledge_checks", None, "High"),
    "knowledge check":            ("knowledge_checks", None, "High"),
    "pre assessment":             ("pre_post_assessment", None, "High"),
    "post assessment":            ("pre_post_assessment", None, "High"),
    "pre evaluation":             ("pre_post_assessment", None, "High"),
    "post evaluation":            ("pre_post_assessment", None, "High"),
    "pre test":                   ("pre_post_assessment", None, "High"),
    "post test":                  ("pre_post_assessment", None, "High"),
    "before and after":           ("pre_post_assessment", None, "High"),
    "before and after assessment":("pre_post_assessment", None, "High"),
    "entry and exit":             ("pre_post_assessment", None, "High"),
    "entry and exit assessment":  ("pre_post_assessment", None, "High"),
    "show up":                    ("attendance", None, "High"),
    "show up to":                 ("attendance", None, "High"),
    "must attend":                ("attendance", None, "High"),
    "must be present":            ("attendance", None, "High"),
    "required attendance":        ("attendance", None, "High"),
    "mandatory attendance":       ("attendance", None, "High"),
    "attendance is required":     ("attendance", None, "High"),
    "attendance is mandatory":    ("attendance", None, "High"),
    "physical presence":          ("attendance", None, "High"),
    "in person attendance":       ("attendance", None, "High"),
    "in-person attendance":       ("attendance", None, "High"),
    "all sessions":               ("attendance", None, "High"),
    "all classes":                ("attendance", None, "High"),
    "all meetings":               ("attendance", None, "High"),
    "complete all modules":     ("module_completion", None, "High"),
    "complete all lessons":     ("module_completion", None, "High"),
    "complete all units":       ("module_completion", None, "High"),
    "complete all sections":    ("module_completion", None, "High"),
    "complete all chapters":    ("module_completion", None, "High"),
    "finish all modules":       ("module_completion", None, "High"),
    "finish all lessons":       ("module_completion", None, "High"),
    "finish all units":         ("module_completion", None, "High"),
    "demonstrate hands on":     ("practical", None, "High"),
    "demonstrate hands-on":     ("practical", None, "High"),
    "hands on assessment":      ("practical", None, "High"),
    "hands-on assessment":      ("practical", None, "High"),
    "hands on evaluation":      ("practical", None, "High"),
    "hands-on evaluation":      ("practical", None, "High"),
    "live demonstration":       ("practical", None, "High"),
    "live demo":                ("practical", None, "High"),
    "instructor graded":        ("expert_scored", None, "High"),
    "teacher graded":           ("expert_scored", None, "High"),
    "professor graded":         ("expert_scored", None, "High"),
    "mentor reviewed":          ("expert_scored", None, "High"),
    "supervisor reviewed":      ("expert_scored", None, "High"),
    "peer reviewed":            ("expert_scored", None, "Medium"),
    "peer evaluation":          ("expert_scored", None, "Medium"),
    "panel review":             ("expert_scored", None, "High"),
    "jury evaluation":          ("expert_scored", None, "High"),
    "portfolio review":         ("expert_scored", None, "High"),
    "portfolio assessment":     ("project_presentation", None, "High"),
    "submit portfolio":         ("project_presentation", None, "High"),
    "present findings":         ("project_presentation", None, "High"),
    "present results":          ("project_presentation", None, "High"),
    "present project":          ("project_presentation", None, "High"),
    "oral presentation":        ("project_presentation", None, "High"),
    "oral defense":             ("project_presentation", None, "High"),
    "thesis defense":           ("project_presentation", None, "High"),
    "dissertation defense":     ("project_presentation", None, "High"),
    "capstone presentation":    ("project_presentation", None, "High"),
    "final presentation":       ("project_presentation", None, "High"),
    "showcase":                 ("project_presentation", None, "High"),
    "exhibition":               ("project_presentation", None, "High"),
}

_ASSESSMENT_PHRASES_SORTED: list[tuple[str, str, str | None, str]] = sorted(
    ((phrase, type_key, threshold, conf)
     for phrase, (type_key, threshold, conf) in ASSESSMENT_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)

# Valid assessment_type values (not special-case signals)
_ASSESSMENT_TYPE_VALUES = {
    "final_assessment", "knowledge_checks", "pre_post_assessment",
    "project_presentation", "attendance", "module_completion", "practical",
}


# ---------------------------------------------------------------------------
# AUDIENCE_PHRASES
# Tuple: (audience_type, audience_signal_detail, confidence)
# ---------------------------------------------------------------------------
AUDIENCE_PHRASES: dict[str, tuple[str, str | None, str]] = {
    "faculty and instructors":    ("njit_employee", "faculty", "High"),
    "healthcare professional":    ("external_professional", "healthcare", "High"),
    "f-1 international students": ("njit_student", "international", "High"),
    "f-1 students":               ("njit_student", "international", "High"),
    "working professionals":      ("external_professional", "professional", "High"),
    "international students":     ("njit_student", "international", "High"),
    "njit employees":             ("njit_employee", "staff", "High"),
    "njit students":              ("njit_student", "student", "High"),
    "njit staff":                 ("njit_employee", "staff", "High"),
    "in partnership with":        ("external_partner", None, "High"),
    "workforce":                  ("external_professional", "professional", "Medium"),
    "industry":                   ("external_professional", "professional", "Medium"),
    "clinical":                   ("external_professional", "healthcare", "Medium"),
    "instructor":                 ("njit_employee", "faculty", "Medium"),
    "educator":                   ("njit_employee", "faculty", "Medium"),
    "faculty":                    ("njit_employee", "faculty", "Medium"),
    "students":                   ("njit_student", "student", "Low"),
    # Student audience language
    "college students":           ("njit_student", "student", "Medium"),
    "university students":        ("njit_student", "student", "Medium"),
    "graduate students":          ("njit_student", "graduate", "High"),
    "undergraduate students":     ("njit_student", "undergraduate", "High"),
    "phd students":               ("njit_student", "phd", "High"),
    "doctoral students":          ("njit_student", "phd", "High"),
    "masters students":           ("njit_student", "masters", "High"),
    "freshmen":                 ("njit_student", "undergraduate", "Medium"),
    "sophomores":               ("njit_student", "undergraduate", "Medium"),
    "juniors":                  ("njit_student", "undergraduate", "Medium"),
    "seniors":                  ("njit_student", "undergraduate", "Medium"),
    "undergrads":               ("njit_student", "undergraduate", "Medium"),
    "grad students":            ("njit_student", "graduate", "Medium"),
    "all students":             ("njit_student", "student", "Low"),
    "student body":             ("njit_student", "student", "Low"),
    "campus community":         ("njit_student", "student", "Low"),
    "campus wide":              ("njit_student", "student", "Low"),
    "campus-wide":              ("njit_student", "student", "Low"),
    "entire campus":            ("njit_student", "student", "Low"),
    "researchers":              ("njit_employee", "faculty", "Medium"),
    "research staff":           ("njit_employee", "staff", "High"),
    "research faculty":         ("njit_employee", "faculty", "High"),
    "tenure track":             ("njit_employee", "faculty", "High"),
    "tenure-track":             ("njit_employee", "faculty", "High"),
    "adjunct faculty":          ("njit_employee", "faculty", "High"),
    "adjunct professors":       ("njit_employee", "faculty", "High"),
    "part time faculty":        ("njit_employee", "faculty", "Medium"),
    "full time faculty":        ("njit_employee", "faculty", "Medium"),
    "professors":               ("njit_employee", "faculty", "Medium"),
    "lecturers":                ("njit_employee", "faculty", "Medium"),
    "teaching assistants":      ("njit_employee", "faculty", "Medium"),
    "tas":                      ("njit_employee", "faculty", "Medium"),
    "t.a.s":                    ("njit_employee", "faculty", "Medium"),
    "support staff":            ("njit_employee", "staff", "High"),
    "administrative staff":     ("njit_employee", "staff", "High"),
    "admin staff":              ("njit_employee", "staff", "High"),
    "professional staff":       ("njit_employee", "staff", "High"),
    "technical staff":          ("njit_employee", "staff", "High"),
    "it staff":                 ("njit_employee", "staff", "High"),
    "library staff":            ("njit_employee", "staff", "High"),
    "maintenance staff":        ("njit_employee", "staff", "Medium"),
    "facilities staff":         ("njit_employee", "staff", "Medium"),
    "all staff":                ("njit_employee", "staff", "Low"),
    "all employees":            ("njit_employee", "staff", "Low"),
    "everyone at njit":         ("njit_employee", "staff", "Low"),
    "entire njit community":    ("njit_employee", "staff", "Low"),
    "njit community":           ("njit_employee", "staff", "Low"),
    "healthcare workers":       ("external_professional", "healthcare", "High"),
    "medical professionals":    ("external_professional", "healthcare", "High"),
    "nurses":                   ("external_professional", "healthcare", "High"),
    "physicians":               ("external_professional", "healthcare", "High"),
    "doctors":                  ("external_professional", "healthcare", "High"),
    "therapists":               ("external_professional", "healthcare", "High"),
    "clinicians":               ("external_professional", "healthcare", "High"),
    "healthcare providers":     ("external_professional", "healthcare", "High"),
    "it professionals":         ("external_professional", "professional", "High"),
    "software engineers":       ("external_professional", "professional", "High"),
    "data scientists":          ("external_professional", "professional", "High"),
    "data analysts":            ("external_professional", "professional", "High"),
    "project managers":         ("external_professional", "professional", "High"),
    "product managers":         ("external_professional", "professional", "High"),
    "business analysts":        ("external_professional", "professional", "High"),
    "financial analysts":       ("external_professional", "professional", "High"),
    "accountants":              ("external_professional", "professional", "High"),
    "lawyers":                  ("external_professional", "professional", "High"),
    "attorneys":                ("external_professional", "professional", "High"),
    "consultants":              ("external_professional", "professional", "High"),
    "contractors":              ("external_professional", "professional", "Medium"),
    "freelancers":              ("external_professional", "professional", "Medium"),
    "entrepreneurs":            ("external_professional", "professional", "Medium"),
    "business owners":          ("external_professional", "professional", "Medium"),
    "startup founders":         ("external_professional", "professional", "Medium"),
    "engineers":                ("external_professional", "professional", "High"),
    "architects":               ("external_professional", "professional", "High"),
    "designers":                ("external_professional", "professional", "Medium"),
    "developers":               ("external_professional", "professional", "High"),
    "programmers":              ("external_professional", "professional", "High"),
    "technicians":              ("external_professional", "professional", "Medium"),
    "specialists":              ("external_professional", "professional", "Medium"),
    "analysts":                 ("external_professional", "professional", "Medium"),
    "managers":                 ("external_professional", "professional", "Medium"),
    "supervisors":              ("external_professional", "professional", "Medium"),
    "coordinators":             ("external_professional", "professional", "Medium"),
    "directors":                ("external_professional", "professional", "Medium"),
    "executives":               ("external_professional", "professional", "Medium"),
    "leaders":                  ("external_professional", "professional", "Medium"),
    "practitioners":            ("external_professional", "professional", "Medium"),
    "job seekers":              ("external_professional", "professional", "Medium"),
    "career changers":          ("external_professional", "professional", "Medium"),
    "recent graduates":         ("external_professional", "professional", "Medium"),
    "new grads":                ("external_professional", "professional", "Medium"),
    "early career":             ("external_professional", "professional", "Medium"),
    "mid career":               ("external_professional", "professional", "Medium"),
    "mid-career":               ("external_professional", "professional", "Medium"),
    "senior professionals":     ("external_professional", "professional", "Medium"),
    "experienced professionals": ("external_professional", "professional", "Medium"),
    "seasoned professionals":   ("external_professional", "professional", "Medium"),
    "veteran professionals":    ("external_professional", "professional", "Medium"),
    "industry veterans":        ("external_professional", "professional", "Medium"),
    "industry experts":         ("external_professional", "professional", "Medium"),
    "subject matter experts":   ("external_professional", "professional", "Medium"),
    "sme":                      ("external_professional", "professional", "Low"),
}

_AUDIENCE_PHRASES_SORTED: list[tuple[str, str, str | None, str]] = sorted(
    ((phrase, aud_type, detail, conf)
     for phrase, (aud_type, detail, conf) in AUDIENCE_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# PURPOSE_PHRASES
# Maps phrase → badge_purpose value or "downstream_workflow" sentinel
# ---------------------------------------------------------------------------
PURPOSE_PHRASES: dict[str, str] = {
    "mandatory to apply":          "compliance",
    "required to apply":           "compliance",
    "prerequisite for":            "prerequisite_gate",
    "required before":             "prerequisite_gate",
    "share their digital badge to": "downstream_workflow",
    "share your badge to":         "downstream_workflow",
    # ---- Student language for purpose ----
    "required to complete":         "compliance",
    "must complete before":         "prerequisite_gate",
    "needed before":                "prerequisite_gate",
    "must finish before":           "prerequisite_gate",
    "needed for":                   "prerequisite_gate",
    "required for":                 "prerequisite_gate",
    "necessary for":                "prerequisite_gate",
    "prerequisite to":              "prerequisite_gate",
    "gate to":                      "prerequisite_gate",
    "stepping stone to":            "prerequisite_gate",
    "pathway to":                   "prerequisite_gate",
    "leads to":                     "downstream_workflow",
    "progresses to":                "downstream_workflow",
    "advances to":                  "downstream_workflow",
    "moves to":                     "downstream_workflow",
    "continues to":                 "downstream_workflow",
}

_PURPOSE_PHRASES_SORTED: list[tuple[str, str]] = sorted(
    PURPOSE_PHRASES.items(),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# PhraseExtractor — applies all four dictionaries to a BFS
# ---------------------------------------------------------------------------

class PhraseExtractor:
    """
    Layer 1: case-insensitive exact phrase matching.

    Operates on the concatenation of badge_description and
    earning_criteria_text — the same text surface used by all NLP layers.
    """

    def extract(self, bfs: BadgeFactSheet, text: str) -> BadgeFactSheet:
        lower = text.lower()

        bfs = self._extract_level(bfs, lower)
        bfs = self._extract_assessment(bfs, lower, text)
        bfs = self._extract_audience(bfs, lower)
        bfs = self._extract_purpose(bfs, lower, text)

        return bfs

    # ------------------------------------------------------------------
    # Level signals
    # ------------------------------------------------------------------

    def _extract_level(self, bfs: BadgeFactSheet, lower: str) -> BadgeFactSheet:
        """
        EC17: Word-boundary matching (phrase_matches) instead of substring.
        EC18: Skip negated phrase matches (is_negated).
        EC19: Collect all non-negated matches; detect conflicting levels and
              record them in confidence_notes; first (longest/highest-priority)
              match still wins.
        """
        if bfs.self_declared_level is not None:
            # Already set by a structured field — don't overwrite
            return bfs

        all_matches: list[tuple[str, str, str]] = []  # (level, phrase, conf)

        for phrase, level, conf in _LEVEL_PHRASES_SORTED:
            m = phrase_matches(phrase, lower)   # EC17 — word boundary
            if m is None:
                continue
            if is_negated(lower, m.start()):    # EC18 — skip negated
                continue
            if is_past_context(lower, m.start()):  # skip past-completion context
                continue
            all_matches.append((level, phrase, conf))

        if not all_matches:
            return bfs

        # EC19 — detect conflicting level signals
        seen_levels: list[str] = []
        for lvl, _, _ in all_matches:
            if lvl not in seen_levels:
                seen_levels.append(lvl)
        if len(seen_levels) > 1:
            conflict_note = (
                f"CONFLICT: multiple level signals detected: {', '.join(seen_levels)}"
            )
            bfs.confidence_notes = (
                (bfs.confidence_notes or "") + f" | {conflict_note}"
            ).lstrip(" |").strip()

        # Use the highest-priority match (longest phrase wins — list is sorted)
        best_level, best_phrase, _ = all_matches[0]
        bfs.self_declared_level = best_level
        bfs.level_phrase_matched = best_phrase
        bfs.level_signal_source = "keyword_rule"

        return bfs

    # ------------------------------------------------------------------
    # Assessment signals
    # ------------------------------------------------------------------

    def _extract_assessment(
        self, bfs: BadgeFactSheet, lower: str, original: str
    ) -> BadgeFactSheet:
        """Multiple matches allowed — sets type, threshold, evaluator."""
        for phrase, type_key, threshold, _ in _ASSESSMENT_PHRASES_SORTED:
            if phrase.lower() not in lower:
                continue

            if type_key in _ASSESSMENT_TYPE_VALUES:
                if bfs.assessment_type is None:
                    bfs.assessment_type = type_key
                    bfs.assessment_required = "yes" if type_key != "attendance" else "no"
                if threshold and bfs.assessment_pass_threshold is None:
                    bfs.assessment_pass_threshold = threshold

            elif type_key == "expert_scored":
                if bfs.assessment_evaluator is None:
                    bfs.assessment_evaluator = "expert_scored"

            # compliance and downstream_workflow are handled by _extract_purpose

        return bfs

    # ------------------------------------------------------------------
    # Audience signals
    # ------------------------------------------------------------------

    def _extract_audience(self, bfs: BadgeFactSheet, lower: str) -> BadgeFactSheet:
        """First match wins — longest phrase has priority."""
        if bfs.audience_type is not None:
            return bfs

        for phrase, aud_type, detail, conf in _AUDIENCE_PHRASES_SORTED:
            if phrase.lower() in lower:
                bfs.audience_type = aud_type
                bfs.audience_signal = detail or phrase
                bfs.audience_signal_source = "keyword_rule"
                return bfs

        return bfs

    # ------------------------------------------------------------------
    # Purpose / downstream workflow signals
    # ------------------------------------------------------------------

    def _extract_purpose(
        self, bfs: BadgeFactSheet, lower: str, original: str
    ) -> BadgeFactSheet:
        for phrase, purpose_value in _PURPOSE_PHRASES_SORTED:
            if phrase.lower() not in lower:
                continue

            if purpose_value in ("compliance", "prerequisite_gate"):
                bfs.badge_purpose = purpose_value

            elif purpose_value == "downstream_workflow":
                # Capture text that follows the trigger phrase as the workflow description
                idx = lower.find(phrase.lower())
                if idx != -1:
                    after = original[idx + len(phrase):].strip().rstrip(".")
                    bfs.downstream_workflow = after[:120] if after else "detected"

        return bfs
