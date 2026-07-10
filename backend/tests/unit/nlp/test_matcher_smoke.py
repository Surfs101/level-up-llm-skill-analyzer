"""Smoke tests for app/nlp/matcher.py — the correctness gate for Phase 1.

Each test is a concrete, hand-checked (text -> expected ids) case across the
extraction behaviors that matter: exact canonical, id-as-surface, alias, case
folding, word boundaries, longest match, multi-word techniques, punctuation, and
no-false-positives.

NOTE on examples: three of the cases in the step spec ("built with fast api",
"postgres", "NextJS", bare "Vue") depend on aliases that the bulk alias
generation (Phase 1, step 1) has not produced yet — those aliases do not exist in
the current taxonomy. Rather than hand-adding aliases here (which belongs in the
taxonomy build, not in a test), each such case is substituted with an equivalent
that exercises the same behavior using a surface form that exists today. The
deferred originals are listed in test_deferred_until_alias_generation below.
"""

from app.nlp.matcher import extract_skill_ids


def test_exact_canonical_names() -> None:
    assert extract_skill_ids("I use Python and PostgreSQL") == {"python", "postgresql"}
    assert extract_skill_ids("We run Docker in production") == {"docker"}
    assert extract_skill_ids("Built on Django and Redis") == {"django", "redis"}


def test_id_as_surface_form() -> None:
    # csharp/cpp are ids that can't be stored as aliases, but must still match.
    assert extract_skill_ids("strong C# and C++ background") == {"csharp", "cpp"}
    assert extract_skill_ids("C# only") == {"csharp"}
    assert extract_skill_ids("experience with .NET") == {"dotnet"}


def test_aliases_that_exist_today() -> None:
    # js / ts / ml / nlp are real aliases in the current taxonomy.
    assert extract_skill_ids("wrote js and ts") == {"javascript", "typescript"}
    assert extract_skill_ids("ml and dl experience") == {"machine-learning", "deep-learning"}
    assert extract_skill_ids("nlp pipelines") == {"natural-language-processing"}


def test_case_insensitive() -> None:
    assert extract_skill_ids("PYTHON and POSTGRESQL") == {"python", "postgresql"}
    assert extract_skill_ids("ML, Js, NLP") == {
        "machine-learning",
        "javascript",
        "natural-language-processing",
    }
    assert extract_skill_ids("DoCkEr") == {"docker"}


def test_word_boundaries() -> None:
    # "JavaScript" must not also yield Java; both present yields both.
    assert extract_skill_ids("JavaScript is not Java") == {"javascript", "java"}
    assert extract_skill_ids("JavaScript only") == {"javascript"}
    assert extract_skill_ids("Java only") == {"java"}


def test_longest_match_wins() -> None:
    result = extract_skill_ids("React Native and React Router")
    assert result == {"react-native", "react-router"}
    assert "react" not in result


def test_bare_react_still_matches_alone() -> None:
    # The longest-match rule must not hide the short name when it stands alone.
    assert extract_skill_ids("Our UI is built in React") == {"react"}


def test_multi_word_techniques() -> None:
    assert extract_skill_ids("5 years of machine learning and NLP") == {
        "machine-learning",
        "natural-language-processing",
    }
    assert extract_skill_ids("experience with test-driven development") == {
        "test-driven-development"
    }


def test_punctuation_around_names() -> None:
    # Trailing/adjacent punctuation must not block a match. Vue.js (canonical) is
    # used instead of bare "Vue" since the "vue" alias does not exist yet.
    assert extract_skill_ids("React, Vue.js, Angular.") == {"react", "vue-js", "angular"}
    assert extract_skill_ids("Node.js and TypeScript") == {"node-js", "typescript"}
    assert extract_skill_ids("(Python)") == {"python"}


def test_dedupes_to_canonical_id() -> None:
    # "golang" is an alias of "go"; both surface forms collapse to one id.
    assert extract_skill_ids("golang and go") == {"go"}


def test_no_false_positives() -> None:
    assert extract_skill_ids("great communicator and team player") == set()
    assert extract_skill_ids("excellent communication and leadership skills") == set()
    assert extract_skill_ids("strong attention to detail and ownership") == set()
    assert extract_skill_ids("") == set()


def test_unicode_normalization() -> None:
    # Zero-width space inside a word must not break the match.
    assert extract_skill_ids("Java​Script") == {"javascript"}
    # Smart quotes and em-dash around a name must not block it.
    assert extract_skill_ids("“Python” — the language") == {"python"}
    # Collapsed whitespace across newlines/tabs.
    assert extract_skill_ids("Python\t\tand\n\nDocker") == {"python", "docker"}


def test_realistic_resume_snippet() -> None:
    text = (
        "Senior engineer with 6 years building backends in Python and Go. "
        "Shipped microservices on Kubernetes and Docker, data in PostgreSQL "
        "and Redis. Comfortable with React on the frontend and some TypeScript."
    )
    # "Go" matches case-sensitively; bare "frontend" is intentionally NOT a surface
    # (area-technique skills require their full phrase — see build_taxonomy.py), so
    # "on the frontend" yields nothing.
    assert extract_skill_ids(text) == {
        "python",
        "go",
        "microservices",
        "kubernetes",
        "docker",
        "postgresql",
        "redis",
        "react",
        "typescript",
    }


def test_returns_only_ids_never_surface_forms() -> None:
    # The result must contain canonical ids, never the matched alias/canonical text.
    result = extract_skill_ids("js and C# and golang")
    assert result == {"javascript", "csharp", "go"}
    assert "js" not in result
    assert "golang" not in result
    assert "c#" not in result


def test_case_sensitive_short_tokens_match_uppercase() -> None:
    # R, Go, C, AD are reachable only via their real capitalization (Part A).
    assert extract_skill_ids("Languages: Rust, R, Go, C") == {"rust", "r", "go", "c"}
    assert extract_skill_ids("R / Android / Linux") == {"r", "google-android", "linux"}
    assert extract_skill_ids("manages the Active Directory (AD) domain") == {
        "microsoft-active-directory"
    }


def test_lowercase_prose_does_not_trigger_short_tokens() -> None:
    # The whole point of case-sensitivity: ordinary lowercase prose containing the
    # letters r/c/go/ad/less/tf must yield NO spurious skill.
    assert extract_skill_ids("for the rest of the team, going forward") == set()
    assert extract_skill_ids("available immediately to go and see results") == set()
    assert extract_skill_ids("a basic ad campaign, less overhead, more focus") == set()
    assert extract_skill_ids("we ran a c-level review and shipped tf-idf features") == set()


def test_uppercase_compound_names_do_not_leak_c_or_r() -> None:
    # "#"/"+"/"&" are non-word-boundaries for the case-sensitive matcher, so the
    # one-letter C/R never leaks out of C#, C++, or R&D.
    assert extract_skill_ids("strong C# and C++ background") == {"csharp", "cpp"}
    assert extract_skill_ids("our R&D group") == set()
    # ...but a genuine standalone C alongside them still resolves.
    assert extract_skill_ids("Python, C, C#, C++") == {"python", "c", "csharp", "cpp"}


def test_js_suffix_does_not_leak_javascript() -> None:
    # Bare "js" must match standalone, never the ".js" inside a framework's name
    # (Part B). React/Vue/Express/Node resolve to their own framework; the unmapped
    # D3.js yields nothing instead of a spurious javascript.
    assert extract_skill_ids("React.js") == {"react"}
    assert extract_skill_ids("Vue.js") == {"vue-js"}
    assert extract_skill_ids("Express.js") == {"express"}
    assert extract_skill_ids("Node.js") == {"node-js"}
    assert extract_skill_ids("D3.js") == set()
    # Standalone JS is still matched.
    assert extract_skill_ids("HTML / CSS / JS") == {"html", "css", "javascript"}


def test_bulk_generated_aliases() -> None:
    """The spec's original alias/case/punctuation cases — now matching thanks to
    the gpt-4o-mini bulk alias pass (Phase 1, step 1). These surface forms
    ("fast api", "postgres", "nextjs", bare "vue") did not exist as aliases until
    that pass ran; they resolve to canonical ids now.
    """
    assert extract_skill_ids("built with fast api") == {"fastapi"}
    assert extract_skill_ids("postgres and NextJS") == {"postgresql", "next-js"}
    assert extract_skill_ids("React, Vue, Angular.") == {"react", "vue-js", "angular"}
