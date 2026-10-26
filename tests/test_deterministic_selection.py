"""Signature compiler module selection must be reproducible across clones (ticket 16).

The defect: `discover()` walked the module tree with `Path.rglob("*.md")`, which returns
filesystem (inode) order, and `budget()` broke ties by taking the first candidate in
iteration order. Two clones of the same commit therefore compiled different prompts.

Measured on byte-identical trees before the fix:

    project-arkais -> arkais.domain.cs_systems  (4418 measured tokens, within ceiling)
    wt-methodology -> arkais.domain.biomedical  (4543 measured tokens, over ceiling)

which made `test_compile_task.py::test_stays_budget_bounded` flaky by construction.

The fix sorts discovery *and* pins each layer default explicitly, so selection never
depends on sort order. These tests pin both halves: determinism, and byte-identical
output with the original checkout's selection.
"""

import random
import sys
from pathlib import Path

import pytest

SDK_SRC = Path(__file__).resolve().parent.parent / "packages" / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais.signature.compiler import (  # noqa: E402
    DEFAULT_CONTRACT_MODULE_ID,
    DEFAULT_DOMAIN_MODULE_ID,
    DEFAULT_LAYER_MODULE_IDS,
    SignatureCompiler,
)

GENERAL_COMPILE = dict(domain="all", section="all", token_budget=2500, task="general")


def _compiler():
    c = SignatureCompiler()
    c.discover()
    return c


def _selection():
    r = _compiler().compile(**GENERAL_COMPILE)
    return tuple(r.manifest.selected_module_ids), r.manifest.measured_tokens


# --- the defaults are declared, not accidental --------------------------------

def test_default_domain_is_an_explicit_named_constant():
    assert DEFAULT_DOMAIN_MODULE_ID == "arkais.domain.cs_systems"
    assert DEFAULT_CONTRACT_MODULE_ID == "arkais.contract.system_directive"


def test_every_pinned_layer_default_exists_in_the_catalog():
    c = _compiler()
    for layer, mod_id in DEFAULT_LAYER_MODULE_IDS.items():
        assert mod_id in c.modules, f"{layer} pins a module absent from the catalog: {mod_id}"
        assert c.modules[mod_id].layer == layer, (
            f"{mod_id} is pinned as the {layer} default but declares layer "
            f"{c.modules[mod_id].layer!r}"
        )


def test_pinned_domain_is_the_canonical_stem_module():
    """`cs_systems` is the canonical STEM domain per the legacy alias map."""
    assert DEFAULT_DOMAIN_MODULE_ID == "arkais.domain.cs_systems"


# --- determinism -------------------------------------------------------------

def test_general_compile_selects_the_pinned_defaults():
    """Only the domain and section tiers are pinned; reasoning/citation are score outcomes."""
    assert set(DEFAULT_LAYER_MODULE_IDS) == {"domain", "section"}
    ids, _ = _selection()
    assert DEFAULT_CONTRACT_MODULE_ID in ids
    for layer, mod_id in DEFAULT_LAYER_MODULE_IDS.items():
        assert mod_id in ids, f"pinned {layer} default {mod_id} missing from {ids}"


def test_targeted_compile_resolves_the_discipline_it_asked_for():
    """A targeted compile must not inherit the untargeted default.

    `domain="stem"` selects cs_systems because that is what stem means here; the section
    pin must not drag `methodology` into a compile that asked for `introduction`.
    """
    c = _compiler()
    r = c.compile(domain="stem", section="introduction", token_budget=3000, task="general")
    ids = r.manifest.selected_module_ids
    assert DEFAULT_DOMAIN_MODULE_ID in ids
    assert "arkais.section.introduction" in ids
    assert DEFAULT_LAYER_MODULE_IDS["section"] not in ids


def test_stem_and_untargeted_compiles_choose_different_reasoning_modules():
    """Reasoning is a score outcome, not a pin -- guard against re-pinning it."""
    stem = _compiler().compile(domain="stem", section="methodology", token_budget=2500, task="general")
    untargeted = _compiler().compile(domain="all", section="all", token_budget=2500, task="general")
    stem_reasoning = [m for m in stem.manifest.selected_module_ids if ".reasoning." in m]
    all_reasoning = [m for m in untargeted.manifest.selected_module_ids if ".reasoning." in m]
    assert stem_reasoning and all_reasoning
    assert stem_reasoning != all_reasoning


def test_selection_is_stable_when_directory_order_is_shuffled():
    """The core regression: rglob order must not reach the result.

    Monkeypatches `Path.rglob` to return the same files in several random orders. Before
    the fix each order could yield a different domain module.
    """
    real_rglob = Path.rglob
    baseline, baseline_tokens = _selection()

    # Three seeds: enough to expose an order-dependent pick (one of these lands
    # `biomedical` first on a fresh clone), without making the suite crawl.
    for seed in (0, 1, 7):
        rng = random.Random(seed)

        def shuffled_rglob(self, pattern, _rng=rng, _real=real_rglob):
            items = list(_real(self, pattern))
            _rng.shuffle(items)
            return iter(items)

        Path.rglob = shuffled_rglob
        try:
            ids, tokens = _selection()
        finally:
            Path.rglob = real_rglob

        assert ids == baseline, f"seed {seed}: {ids} != {baseline}"
        assert tokens == baseline_tokens


def test_repeated_compiles_are_identical():
    a_ids, a_tokens = _selection()
    b_ids, b_tokens = _selection()
    assert a_ids == b_ids
    assert a_tokens == b_tokens


# --- behaviour preservation --------------------------------------------------

def test_general_compile_stays_within_its_ceiling():
    """The assertion that was flaky before: now it holds because selection is pinned."""
    c = _compiler()
    r = c.compile(**GENERAL_COMPILE)
    assert r.manifest.measured_tokens <= c.budget_ceiling, (
        f"general compile measured {r.manifest.measured_tokens} against ceiling "
        f"{c.budget_ceiling}"
    )


def test_selection_is_unchanged_by_this_fix():
    """Behaviour-preserving: reproduces the original checkout's compiled module set.

    Captured from `project-arkais` at 4790c1c7 before any ticket-16 change. If a future
    edit to the compiler legitimately changes the compiled signature, this test is the
    tripwire that says so, and the change belongs in the changelog with a version bump --
    it must not happen silently.
    """
    EXPECTED = (
        "arkais.contract.system_directive",
        "arkais.reasoning.argument_architecture",
        "arkais.domain.cs_systems",
        "arkais.section.methodology",
        "arkais.citation.citation_integrity",
    )
    ids, tokens = _selection()
    assert ids == EXPECTED
    assert tokens == 4418


def test_golden_prompt_digest_is_reproduced():
    """The strongest continuity check available: a byte-exact compiled prompt.

    `test_phase7_signature_vertical_integration.py` pins this digest against a promoted
    golden. Asserting it here means ticket 16 cannot be "made green" by regenerating the
    golden to match a changed selection.
    """
    import hashlib

    GOLDEN = "71f722fef4bea6a5390b6e0747c7fb025bab243af15305aa3f5b0b6a933c5745"
    r = _compiler().compile(domain="stem", section="methodology", token_budget=2500,
                           task="general", citation_style="all")
    digest = hashlib.sha256(r.prompt_text.encode()).hexdigest()
    assert digest == GOLDEN


@pytest.mark.parametrize("task", ["general", "citation", "audit"])
def test_other_tasks_are_also_deterministic(task):
    c = _compiler()
    r = c.compile(domain="all", section="all", token_budget=2500, task=task)
    ids = tuple(r.manifest.selected_module_ids)
    c2 = _compiler()
    r2 = c2.compile(domain="all", section="all", token_budget=2500, task=task)
    assert ids == tuple(r2.manifest.selected_module_ids)