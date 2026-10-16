"""Task-contract regression tests for the signature compiler — D-2 / THE-76.

The defect: `CompileRequest.task` / `compile(task=...)` was threaded from the CLI through
`client.compile` and `loader.compile` into `SignatureCompiler.compile`, read into a local, and
then never used. Every compile behaved identically regardless of the task requested.

Worse than inert: `score()` rewarded a matching citation style by only +80 points while admission
was decided against `token_cost`, a frontmatter figure that understates composed size by
1.5x-2.25x. A compile with `citation_style="apa"` and `task="citation"` produced a prompt
containing **no APA module at all**, and a warning-free manifest that looked successful.

These tests pin the three properties the spec requires:
  1. a citation-task compile contains every reserved module;
  2. a `general` compile at 2500 stays budget-bounded and reserves nothing;
  3. the `evaluation_layer_decoupled` exclusion is untouched.
"""

import sys
from pathlib import Path

SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais.signature.compiler import (  # noqa: E402
    COMPILE_TASKS,
    DEFAULT_TASK,
    TOKEN_WORDS_TO_TOKENS,
    CompileRequest,
    SignatureCompiler,
    normalize_task,
)

RESERVED_CITATION_MODULES = (
    "arkais.research.source_hierarchy",
    "arkais.citation.citation_integrity",
    "arkais.rhetoric.citation_weaving",
)


def _compiler():
    c = SignatureCompiler()
    c.discover()
    return c


class TestTaskVocabulary:
    def test_known_tasks_resolve_without_a_note(self):
        for name in COMPILE_TASKS:
            assert normalize_task(name) == (name, None)

    def test_unknown_task_falls_back_visibly(self):
        """A typo must not crash a pipeline, but it must not pass silently either."""
        resolved, note = normalize_task("citaton")
        assert resolved == DEFAULT_TASK
        assert note == "unknown_task:citaton"

    def test_missing_task_is_not_a_note(self):
        assert normalize_task(None) == (DEFAULT_TASK, None)
        assert normalize_task("") == (DEFAULT_TASK, None)

    def test_task_is_case_and_whitespace_insensitive(self):
        assert normalize_task("  Citation ") == ("citation", None)


class TestCitationTaskReservation:
    def test_all_reserved_modules_present(self):
        c = _compiler()
        r = c.compile(section="citation", task="citation", inject_exemplars=False)
        selected = set(r.included_modules)
        for module_id in RESERVED_CITATION_MODULES:
            assert module_id in selected, f"{module_id} was dropped from a citation compile"

    def test_requested_style_module_is_included(self):
        """The regression that motivated the whole contract.

        Before the fix, `citation_style="apa"` produced a prompt with no APA module in it.
        """
        c = _compiler()
        for style in ("apa", "chicago", "mla"):
            r = c.compile(
                section="citation",
                citation_style=style,
                task="citation",
                inject_exemplars=False,
            )
            assert f"arkais.citation.{style}" in r.included_modules, (
                f"citation_style={style!r} did not include the {style} module"
            )

    def test_manifest_records_the_guarantee(self):
        """A caller should be able to verify the guarantee, not assume it."""
        c = _compiler()
        r = c.compile(section="citation", task="citation", inject_exemplars=False)
        assert r.manifest.task == "citation"
        for module_id in RESERVED_CITATION_MODULES:
            assert module_id in r.manifest.reserved_module_ids
            assert module_id in r.manifest.to_dict()["reserved_module_ids"]

    def test_no_warning_claims_a_reserved_module_is_missing(self):
        c = _compiler()
        r = c.compile(section="citation", task="citation", inject_exemplars=False)
        assert not any(w.startswith("Reserved modules missing") for w in r.manifest.warnings)

    def test_budget_shortfall_is_reported_not_hidden(self):
        """Below the converted ceiling the reserved set is still admitted — omitting it would
        make the compile silently not a citation compile — but the caller is told rather than
        quietly over budget.

        The budget here is below the point where the reserved set fits. `token_budget` is a
        *declared* budget and admission is compared against the measured ceiling it converts
        to, so a declared budget that looks adequate on paper can still not cover the reserved
        set; that gap is exactly what this warning exists to make visible.
        """
        c = _compiler()
        r = c.compile(
            section="citation", token_budget=1500, task="citation", inject_exemplars=False
        )
        assert r.manifest.reserved_module_ids, (
            "the reserved set is what makes this a citation compile"
        )
        assert any("beyond the effective ceiling" in w for w in r.manifest.warnings)
        assert any(
            str(COMPILE_TASKS["citation"].min_measured_budget) in w
            for w in r.manifest.warnings
        )

    def test_a_reserved_set_that_fits_reports_no_shortfall(self):
        """The warning is not a permanent fixture. When the converted ceiling covers the
        reserved set there is nothing to disclose, and saying otherwise would train readers to
        ignore it."""
        c = _compiler()
        r = c.compile(
            section="citation", token_budget=2500, task="citation", inject_exemplars=False
        )
        assert r.manifest.reserved_module_ids
        assert not any("beyond the effective ceiling" in w for w in r.manifest.warnings)


class TestGeneralTaskUnchanged:
    def test_reserves_nothing(self):
        c = _compiler()
        r = c.compile(domain="all", section="all", token_budget=2500, task="general")
        assert r.manifest.task == "general"
        assert r.manifest.reserved_module_ids == []

    def test_stays_budget_bounded(self):
        """`token_budget` is a declared budget, so the invariant is not `measured <= token_budget`
        — that compares two different units and was the original defect. The invariant is that a
        normal general compile comes out *whole* against its converted ceiling: starving it to a
        contract module and a domain stub is the failure mode this guards."""
        c = _compiler()
        r = c.compile(domain="all", section="all", token_budget=2500, task="general")
        assert set(r.manifest.layers_present) >= {
            "contract", "reasoning", "domain", "section", "citation",
        }, f"general compile collapsed to {r.manifest.layers_present}"
        assert r.manifest.measured_tokens <= c.budget_ceiling, (
            f"general compile measured {r.manifest.measured_tokens} against an effective ceiling "
            f"of {c.budget_ceiling}"
        )

    def test_only_warning_is_the_declared_overrun_from_the_mandatory_contract_module(self):
        """A contract module is admitted unconditionally, so declared tokens can sit just over a
        declared budget. That is true information and stays reported — but it must be the only
        thing a normal general compile has to say."""
        c = _compiler()
        r = c.compile(domain="all", section="all", token_budget=2500, task="general")
        unexpected = [w for w in r.manifest.warnings if "exceed budget ceiling" not in w]
        assert unexpected == [], f"unexpected warnings: {unexpected}"

    def test_default_task_is_general(self):
        c = _compiler()
        a = c.compile(domain="all", section="all", token_budget=2500)
        b = c.compile(domain="all", section="all", token_budget=2500, task="general")
        assert a.included_modules == b.included_modules
        assert a.prompt_digest == b.prompt_digest


class TestEvaluationLayerUntouched:
    """The audit/evaluation exclusion is intentional and must not be 'fixed'."""

    def test_audit_and_evaluation_layers_are_never_auto_admitted(self):
        c = _compiler()
        r = c.compile(domain="all", section="all", token_budget=2500, task="general")
        selected = set(r.included_modules)
        for module_id, mod in c.modules.items():
            if mod.layer in ("audit", "evaluation"):
                assert module_id not in selected, (
                    f"{module_id} ({mod.layer}) was admitted by the budget fill"
                )

    def test_omission_reason_is_still_evaluation_layer_decoupled(self):
        c = _compiler()
        r = c.compile(domain="all", section="all", token_budget=2500, task="general")
        reasons = {
            mid: reason for mid, reason in r.manifest.omitted_modules.items()
            if reason == "evaluation_layer_decoupled"
        }
        assert reasons, "expected audit/evaluation modules to report the decoupled reason"

    def test_reserved_citation_integrity_is_not_an_evaluation_layer(self):
        """`citation_integrity` is layer=citation, so reservation does not smuggle in the
        excluded evaluation layer."""
        c = _compiler()
        assert c.modules["arkais.citation.citation_integrity"].layer == "citation"
        assert c.modules["arkais.evaluation.citation_audit"].layer == "evaluation"


class TestMeasuredCostIsUsedForAdmission:
    def test_declared_cost_understates_measured(self):
        """The premise behind switching admission to measured cost."""
        c = _compiler()
        understated = 0
        for module_id, mod in c.modules.items():
            if c._measured_cost(mod) > mod.token_cost:
                understated += 1
        assert understated > len(c.modules) // 2, (
            "expected most modules to understate; the budget premise no longer holds"
        )

    def test_measured_cost_is_render_accurate(self):
        """Admission must count what compose emits, not what the module file contains.

        Measuring bare `mod.content` under-counts by the module header plus anything exemplar
        binding injects into the body, which let a `general` compile measure 2695 against a
        2500 ceiling while the compiler believed it was within budget.
        """
        c = _compiler()
        mod = c.modules["arkais.contract.system_directive"]
        content_only = round(len(mod.content.split()) * TOKEN_WORDS_TO_TOKENS)
        assert c._measured_cost(mod) >= content_only
        expected = round(
            len(f"<!-- MODULE: {mod.id} ({mod.layer}) -->\n{mod.content}".split())
            * TOKEN_WORDS_TO_TOKENS
        )
        assert c._measured_cost(mod) == expected

    def test_exemplar_binding_is_counted(self):
        """With exemplars on, binding inflates a module; the ceiling must know."""
        c = _compiler()
        mod = c.modules["arkais.contract.system_directive"]
        assert c._measured_cost(mod, inject_exemplars=True) > c._measured_cost(mod)

    def test_exemplar_block_is_reserved_once(self):
        c = _compiler()
        assert c._exemplar_block_cost(False, "all") == 0
        assert c._exemplar_block_cost(True, "all") > 0


class TestCompileRequestPath:
    def test_task_via_compile_request_is_honoured(self):
        """The dataclass path must behave identically to the kwarg path."""
        c = _compiler()
        req = CompileRequest(
            domain="all", section="citation", task="citation", inject_exemplars=False
        )
        r = c.compile(req)
        assert r.manifest.task == "citation"
        for module_id in RESERVED_CITATION_MODULES:
            assert module_id in r.included_modules