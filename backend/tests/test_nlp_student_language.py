"""
NLP Student Language Tests.

Tests the extended phrase dictionaries and regex patterns that cover
student-friendly natural language expressions for badge classification.

Covers:
  - Foundational level phrases (beginner-friendly language)
  - Milestone level phrases (intermediate progression language)
  - Terminal level phrases (completion/capstone language)
  - Assessment patterns (student-friendly assessment descriptions)
  - Audience patterns (broader audience terminology)
  - Real-world context patterns (student workplace language)
"""

import pytest
from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.nlp.phrase_dictionary import (
    LEVEL_PHRASES,
    ASSESSMENT_PHRASES,
    AUDIENCE_PHRASES,
    PURPOSE_PHRASES,
)
from app.services.nlp.pattern_rules import (
    LEVEL_PATTERNS,
    ASSESSMENT_PATTERNS,
    REAL_WORLD_PATTERNS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def blank_bfs():
    """Return a blank BadgeFactSheet for signal extraction tests."""
    return BadgeFactSheet()


@pytest.fixture
def extractor():
    """Return a SignalExtractor with LLM disabled."""
    from app.services.nlp.signal_extractor import SignalExtractor
    return SignalExtractor(use_llm=False)


# ---------------------------------------------------------------------------
# Level Phrase Tests — Student Language
# ---------------------------------------------------------------------------

class TestStudentLevelPhrases:
    """Verify student-friendly level phrases are present and trigger correctly."""

    def test_foundational_student_phrases_present(self):
        """All new foundational student phrases must exist in dictionary."""
        phrases = [
            "starting out",
            "beginner level",
            "new to this",
            "just learning",
            "learning the ropes",
            "no background",
            "no previous skills",
            "first timers",
            "never done this",
            "step one",
            "step 1",
            "part one",
            "part 1",
            "basic concepts",
            "basic skills",
            "fundamental concepts",
            "fundamental skills",
            "groundwork",
            "building blocks",
            "starting point",
            "newcomers welcome",
            "beginners welcome",
            "open to beginners",
            "no experience necessary",
            "experience not required",
            "no prerequisites",
            "prerequisites not required",
            "open to all levels",
            "all skill levels",
            "open to everyone",
            "no prior knowledge",
            "prior knowledge not required",
            "from scratch",
            "from the ground up",
            "zero to hero",
            "zero experience",
            "for dummies",
            "101",
            "level one",
            "level 1",
            "tier one",
            "tier 1",
            "stage one",
            "stage 1",
            "phase one",
            "phase 1",
            "module one",
            "module 1",
            "unit one",
            "unit 1",
            "lesson one",
            "lesson 1",
            "chapter one",
            "chapter 1",
            "section one",
            "section 1",
        ]
        for phrase in phrases:
            assert phrase in LEVEL_PHRASES, f"Missing foundational phrase: {phrase}"
            assert LEVEL_PHRASES[phrase][0] == "Foundational"

    def test_milestone_student_phrases_present(self):
        """All new milestone student phrases must exist in dictionary."""
        phrases = [
            "level up",
            "moving up",
            "moving forward",
            "progressing to",
            "taking the next step",
            "step two",
            "step 2",
            "part two",
            "part 2",
            "second part",
            "second step",
            "next phase",
            "next stage",
            "next level",
            "intermediate level",
            "intermediate skills",
            "intermediate course",
            "intermediate badge",
            "intermediate module",
            "advanced beginner",
            "beyond the basics",
            "beyond basics",
            "not beginner",
            "not a beginner",
            "some experience",
            "prior experience",
            "previous experience",
            "some background",
            "prior knowledge",
            "previous knowledge",
            "already know",
            "already familiar",
            "already understand",
            "assumes knowledge",
            "assumes understanding",
            "assumes familiarity",
            "prerequisite course",
            "prerequisite badge",
            "prerequisite module",
            "required prerequisite",
            "must complete first",
            "must complete before",
            "builds on",
            "builds upon",
            "building on",
            "building upon",
            "expand on",
            "expand upon",
            "expanding on",
            "deepen skills",
            "deepen understanding",
            "deepen knowledge",
            "deepens skills",
            "deepens understanding",
            "deepens knowledge",
            "advance skills",
            "advance knowledge",
            "advances skills",
            "advances understanding",
            "further develop",
            "further development",
            "more advanced",
            "more complex",
            "more challenging",
            "more difficult",
            "more sophisticated",
            "higher level",
            "level two",
            "level 2",
            "tier two",
            "tier 2",
            "stage two",
            "stage 2",
            "phase two",
            "phase 2",
            "module two",
            "module 2",
            "course two",
            "course 2",
            "continuing education",
            "continuing development",
            "ongoing development",
            "ongoing learning",
            "professional development",
            "career development",
            "skill advancement",
            "skill progression",
            "career advancement",
            "upskilling",
            "reskilling",
        ]
        for phrase in phrases:
            assert phrase in LEVEL_PHRASES, f"Missing milestone phrase: {phrase}"
            assert LEVEL_PHRASES[phrase][0] == "Milestone"

    def test_terminal_student_phrases_present(self):
        """All new terminal student phrases must exist in dictionary."""
        phrases = [
            "capstone project",
            "capstone course",
            "capstone badge",
            "final step",
            "final stage",
            "final phase",
            "final level",
            "culminating project",
            "culminating course",
            "culminating experience",
            "culminating achievement",
            "culmination of",
            "ultimate achievement",
            "highest level",
            "top level",
            "expert level",
            "expert status",
            "mastery level",
            "mastery badge",
            "mastery achievement",
            "complete mastery",
            "full mastery",
            "total mastery",
            "complete proficiency",
            "full proficiency",
            "total proficiency",
            "comprehensive understanding",
            "comprehensive knowledge",
            "comprehensive skills",
            "well rounded",
            "well-rounded",
            "fully prepared",
            "fully qualified",
            "fully trained",
            "completely trained",
            "thoroughly trained",
            "wrap up",
            "wrapping up",
            "tied together",
            "ties together",
            "bring it all together",
            "bringing it all together",
            "synthesize knowledge",
            "synthesize skills",
            "synthesis of",
            "integrate all",
            "integrate everything",
            "integration of",
            "complete program",
            "complete series",
            "complete curriculum",
            "complete pathway",
            "end of the journey",
            "end of the road",
            "end of the path",
            "final destination",
            "graduation level",
            "graduation badge",
            "graduation achievement",
            "terminal course",
            "terminal badge",
            "terminal achievement",
            "terminal level",
            "senior level",
            "advanced level",
            "top tier",
            "highest tier",
            "ultimate level",
            "peak achievement",
            "final achievement",
            "crowning achievement",
            "final certification",
            "terminal certification",
            "program completion",
            "series completion",
            "pathway completion",
            "curriculum completion",
            "all requirements met",
            "all courses completed",
            "all modules completed",
            "all badges earned",
            "sum of all parts",
            "greater than the sum",
            "combined knowledge",
            "combined skills",
        ]
        for phrase in phrases:
            assert phrase in LEVEL_PHRASES, f"Missing terminal phrase: {phrase}"
            assert LEVEL_PHRASES[phrase][0] == "Terminal"

    def test_foundational_phrase_extraction(self, blank_bfs, extractor):
        """Student foundational phrases trigger correct level extraction."""
        blank_bfs.badge_description = "This is for beginners welcome and starts from scratch."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"

    def test_milestone_phrase_extraction(self, blank_bfs, extractor):
        """Student milestone phrases trigger correct level extraction."""
        blank_bfs.badge_description = "This course builds on prior knowledge and is level two."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"

    def test_terminal_phrase_extraction(self, blank_bfs, extractor):
        """Student terminal phrases trigger correct level extraction."""
        blank_bfs.badge_description = "This capstone project completes the program and all requirements met."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Terminal"

    def test_101_foundational_extraction(self, blank_bfs, extractor):
        """101 course number triggers foundational level."""
        blank_bfs.badge_description = "Data Analytics 101: Introduction to the field."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"

    def test_level_up_milestone_extraction(self, blank_bfs, extractor):
        """Level up language triggers milestone level."""
        blank_bfs.badge_description = "Take your skills to the next level with this level up course."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"

    def test_zero_to_hero_foundational_extraction(self, blank_bfs, extractor):
        """Zero to hero language triggers foundational level."""
        blank_bfs.badge_description = "Learn from zero to hero in just 8 weeks. No experience necessary."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"


# ---------------------------------------------------------------------------
# Assessment Phrase Tests — Student Language
# ---------------------------------------------------------------------------

class TestStudentAssessmentPhrases:
    """Verify student-friendly assessment phrases are present and trigger."""

    def test_assessment_phrases_present(self):
        """New assessment phrases must exist in dictionary."""
        phrases = [
            "final exam",
            "final test",
            "final quiz",
            "end of course exam",
            "end of course test",
            "comprehensive exam",
            "comprehensive test",
            "comprehensive quiz",
            "summative assessment",
            "summative evaluation",
            "cumulative exam",
            "cumulative test",
            "checkpoint quiz",
            "module quiz",
            "section quiz",
            "unit quiz",
            "weekly quiz",
            "chapter quiz",
            "quick check",
            "comprehension check",
            "understanding check",
            "mastery check",
            "skill check",
            "progress check",
            "learning check",
            "knowledge check",
            "pre assessment",
            "post assessment",
            "pre evaluation",
            "post evaluation",
            "pre test",
            "post test",
            "before and after",
            "before and after assessment",
            "entry and exit",
            "entry and exit assessment",
            "show up",
            "show up to",
            "must attend",
            "must be present",
            "required attendance",
            "mandatory attendance",
            "attendance is required",
            "attendance is mandatory",
            "physical presence",
            "in person attendance",
            "in-person attendance",
            "all sessions",
            "all classes",
            "all meetings",
            "complete all modules",
            "complete all lessons",
            "complete all units",
            "complete all sections",
            "complete all chapters",
            "finish all modules",
            "finish all lessons",
            "finish all units",
            "demonstrate hands on",
            "demonstrate hands-on",
            "hands on assessment",
            "hands-on assessment",
            "hands on evaluation",
            "hands-on evaluation",
            "live demonstration",
            "live demo",
            "instructor graded",
            "teacher graded",
            "professor graded",
            "mentor reviewed",
            "supervisor reviewed",
            "peer reviewed",
            "peer evaluation",
            "panel review",
            "jury evaluation",
            "portfolio review",
            "portfolio assessment",
            "submit portfolio",
            "present findings",
            "present results",
            "present project",
            "oral presentation",
            "oral defense",
            "thesis defense",
            "dissertation defense",
            "capstone presentation",
            "final presentation",
            "showcase",
            "exhibition",
        ]
        for phrase in phrases:
            assert phrase in ASSESSMENT_PHRASES, f"Missing assessment phrase: {phrase}"

    def test_checkpoint_quiz_extraction(self, blank_bfs, extractor):
        """Checkpoint quiz triggers knowledge_checks assessment type."""
        blank_bfs.earning_criteria_text = "Pass checkpoint quiz at 80% or higher."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "knowledge_checks"

    def test_show_up_attendance_extraction(self, blank_bfs, extractor):
        """Show up triggers attendance assessment type."""
        blank_bfs.earning_criteria_text = "Just show up to all sessions."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "attendance"

    def test_live_demo_practical_extraction(self, blank_bfs, extractor):
        """Live demo triggers practical assessment type."""
        blank_bfs.earning_criteria_text = "Complete a live demo of the project."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "practical"

    def test_peer_reviewed_expert_scored(self, blank_bfs, extractor):
        """Peer reviewed triggers expert_scored evaluator."""
        blank_bfs.earning_criteria_text = "Work is peer reviewed and evaluated."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_evaluator == "expert_scored"


# ---------------------------------------------------------------------------
# Audience Phrase Tests — Student Language
# ---------------------------------------------------------------------------

class TestStudentAudiencePhrases:
    """Verify broader audience terminology triggers correct audience_type."""

    def test_audience_phrases_present(self):
        """New audience phrases must exist in dictionary."""
        phrases = [
            "college students",
            "university students",
            "graduate students",
            "undergraduate students",
            "phd students",
            "doctoral students",
            "masters students",
            "freshmen",
            "sophomores",
            "juniors",
            "seniors",
            "undergrads",
            "grad students",
            "all students",
            "student body",
            "campus community",
        ]
        for phrase in phrases:
            assert phrase in AUDIENCE_PHRASES, f"Missing audience phrase: {phrase}"
            assert AUDIENCE_PHRASES[phrase][0] == "njit_student"

    def test_graduate_students_audience(self, blank_bfs, extractor):
        """Graduate students triggers njit_student audience."""
        blank_bfs.badge_description = "Open to graduate students in engineering."
        result = extractor.extract_all(blank_bfs)
        assert result.audience_type == "njit_student"

    def test_undergraduate_students_audience(self, blank_bfs, extractor):
        """Undergraduate students triggers njit_student audience."""
        blank_bfs.badge_description = "Designed for undergraduate students new to CS."
        result = extractor.extract_all(blank_bfs)
        assert result.audience_type == "njit_student"


# ---------------------------------------------------------------------------
# Purpose Phrase Tests — Student Language
# ---------------------------------------------------------------------------

class TestStudentPurposePhrases:
    """Verify broader purpose phrases are present."""

    def test_purpose_phrases_present(self):
        """New purpose phrases must exist in dictionary."""
        phrases = [
            "required to complete",
            "must complete before",
            "needed before",
            "must finish before",
            "needed for",
            "required for",
            "necessary for",
            "prerequisite to",
            "gate to",
            "stepping stone to",
            "pathway to",
            "leads to",
            "progresses to",
            "advances to",
            "moves to",
            "continues to",
        ]
        for phrase in phrases:
            assert phrase in PURPOSE_PHRASES, f"Missing purpose phrase: {phrase}"

    def test_prerequisite_to_gate(self, blank_bfs, extractor):
        """Prerequisite to triggers prerequisite_gate purpose."""
        blank_bfs.badge_description = "This badge is prerequisite to the advanced course."
        result = extractor.extract_all(blank_bfs)
        assert result.badge_purpose == "prerequisite_gate"


# ---------------------------------------------------------------------------
# Pattern Tests — Student Language Regex Patterns
# ---------------------------------------------------------------------------

class TestStudentLevelPatterns:
    """Verify student-friendly regex patterns trigger correctly."""

    def test_just_starting_pattern(self, blank_bfs, extractor):
        """Just starting pattern triggers foundational."""
        blank_bfs.badge_description = "This is just starting your journey in data science."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"

    def test_no_experience_pattern(self, blank_bfs, extractor):
        """No experience pattern triggers foundational."""
        blank_bfs.badge_description = "No experience required for this course."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"

    def test_level_up_pattern(self, blank_bfs, extractor):
        """Level up pattern triggers milestone."""
        blank_bfs.badge_description = "Level up your skills with this intermediate course."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"

    def test_builds_on_pattern(self, blank_bfs, extractor):
        """Builds on pattern triggers milestone level."""
        # Use text without 'introductory' to avoid conflict with existing
        # Foundational phrase 'introductory' in Rajat's dictionary.
        blank_bfs.badge_description = "This course builds on the prior concepts."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"

    def test_capstone_pattern(self, blank_bfs, extractor):
        """Capstone pattern triggers terminal."""
        blank_bfs.badge_description = "Capstone project for the data science program."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Terminal"

    def test_put_it_together_pattern(self, blank_bfs, extractor):
        """Put it all together pattern triggers terminal."""
        blank_bfs.badge_description = "Put it all together in this final project."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Terminal"


class TestStudentAssessmentPatterns:
    """Verify student-friendly assessment patterns trigger correctly."""

    def test_just_show_up_pattern(self, blank_bfs, extractor):
        """Just show up triggers attendance."""
        blank_bfs.earning_criteria_text = "Just show up and participate."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "attendance"

    def test_physical_presence_pattern(self, blank_bfs, extractor):
        """Physical presence triggers attendance."""
        blank_bfs.earning_criteria_text = "Physical presence at all workshops is required."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "attendance"


class TestStudentRealWorldPatterns:
    """Verify student-friendly real-world patterns trigger correctly."""

    def test_workplace_pattern(self, blank_bfs, extractor):
        """Workplace triggers real_world_context."""
        blank_bfs.badge_description = "Apply skills in a workplace setting."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True

    def test_client_project_pattern(self, blank_bfs, extractor):
        """Client project triggers real_world_context."""
        blank_bfs.badge_description = "Complete a client project for local business."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True

    def test_community_service_pattern(self, blank_bfs, extractor):
        """Community service triggers real_world_context."""
        blank_bfs.badge_description = "Participate in community service learning."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True

    def test_practicum_pattern(self, blank_bfs, extractor):
        """Practicum triggers real_world_context."""
        blank_bfs.badge_description = "Complete clinical practicum at hospital."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True

    def test_case_study_pattern(self, blank_bfs, extractor):
        """Case study triggers real_world_context."""
        blank_bfs.badge_description = "Analyze real-world case studies in class."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True


# ---------------------------------------------------------------------------
# Integration Tests — Free Text Student Descriptions
# ---------------------------------------------------------------------------

class TestFreeTextStudentDescriptions:
    """Test realistic student-written badge descriptions."""

    def test_beginner_friendly_description(self, blank_bfs, extractor):
        """A typical beginner-friendly free text description."""
        blank_bfs.badge_description = (
            "New to coding? No worries! This badge is for beginners welcome. "
            "Learn Python from scratch and build your first project. "
            "No experience necessary."
        )
        # Use "topics" instead of "lessons" to avoid conflict with
        # module_completion phrase "complete all lessons".
        blank_bfs.earning_criteria_text = (
            "Complete all topics and pass checkpoint quiz at 80%."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"
        assert result.assessment_type == "knowledge_checks"

    def test_intermediate_progression_description(self, blank_bfs, extractor):
        """A typical intermediate progression description."""
        blank_bfs.badge_description = (
            "Level up your Python skills! This intermediate course builds on "
            "prior knowledge from Python 101. You must complete the first "
            "course before starting."
        )
        blank_bfs.earning_criteria_text = (
            "Build a portfolio project and get peer reviewed."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"
        assert result.assessment_evaluator == "expert_scored"
        assert result.real_world_context is True

    def test_capstone_description(self, blank_bfs, extractor):
        """A typical capstone/terminal description."""
        blank_bfs.badge_description = (
            "Capstone project putting it all together. Complete the full "
            "data science program and demonstrate mastery. All courses must be "
            "completed first."
        )
        blank_bfs.earning_criteria_text = (
            "Present final findings to panel and submit portfolio."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Terminal"
        assert result.assessment_type == "project_presentation"

    def test_internship_description(self, blank_bfs, extractor):
        """A description involving real-world work experience."""
        blank_bfs.badge_description = (
            "Gain hands-on experience through industry collaboration. "
            "Work on applied projects with real clients in professional setting."
        )
        blank_bfs.earning_criteria_text = (
            "Complete practicum hours and get mentor reviewed."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True
        assert result.assessment_evaluator == "expert_scored"

    def test_attendance_only_description(self, blank_bfs, extractor):
        """An attendance-only souvenir badge."""
        blank_bfs.badge_description = (
            "Just show up to the welcome week events! No tests or quizzes. "
            "Must attend all sessions to earn."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "attendance"
        assert result.assessment_required == "no"

    def test_compliance_prerequisite_description(self, blank_bfs, extractor):
        """A compliance badge with prerequisite gate."""
        blank_bfs.badge_description = (
            "Required to complete before advancing to senior level. "
            "This badge is prerequisite to the capstone course."
        )
        result = extractor.extract_all(blank_bfs)
        assert result.badge_purpose == "prerequisite_gate"


# ---------------------------------------------------------------------------
# Regression Tests — Ensure Original Rajat Phrases Still Work
# ---------------------------------------------------------------------------

class TestOriginalPhraseRegression:
    """Verify Rajat's original phrases still trigger correctly."""

    def test_original_foundational_phrase(self, blank_bfs, extractor):
        """Original 'no prior experience' still works."""
        blank_bfs.badge_description = "No prior experience required."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Foundational"

    def test_original_milestone_phrase(self, blank_bfs, extractor):
        """Original 'building on foundational' still works."""
        blank_bfs.badge_description = "Building on foundational concepts."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Milestone"

    def test_original_terminal_phrase(self, blank_bfs, extractor):
        """Original 'completion of all' still works."""
        blank_bfs.badge_description = "Completion of all modules in the series."
        result = extractor.extract_all(blank_bfs)
        assert result.self_declared_level == "Terminal"

    def test_original_assessment_phrase(self, blank_bfs, extractor):
        """Original 'passing knowledge checks' still works."""
        blank_bfs.earning_criteria_text = "Passing knowledge checks with 80% or higher."
        result = extractor.extract_all(blank_bfs)
        assert result.assessment_type == "knowledge_checks"
        assert result.assessment_pass_threshold == "80%"

    def test_original_audience_phrase(self, blank_bfs, extractor):
        """Original 'working professionals' still works."""
        blank_bfs.badge_description = "For working professionals in the industry."
        result = extractor.extract_all(blank_bfs)
        assert result.audience_type == "external_professional"

    def test_original_real_world_pattern(self, blank_bfs, extractor):
        """Original 'real-world experience' pattern still works."""
        blank_bfs.badge_description = "Apply skills in a real-world context."
        result = extractor.extract_all(blank_bfs)
        assert result.real_world_context is True
