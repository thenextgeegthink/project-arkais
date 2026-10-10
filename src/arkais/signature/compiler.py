"""
SignatureCompiler — Dynamic modular competency compiler for Project Arkais v3.0.

Implements the compiler lifecycle:
DISCOVER -> SCORE -> PRIORITIZE -> BUDGET -> ORDER -> COMPOSE -> VALIDATE

Enforces the core invariant: 'Reasoning precedes realization'.
(Core -> Reasoning -> Evidence -> Domain -> Section -> Citation -> Style -> Exemplars)
"""

import os
import re
import json
import random
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any, Tuple, Union


LAYER_ORDER = [
    "contract",
    "core",
    "reasoning",
    "research",
    "evidence",
    "rhetoric",
    "domain",
    "section",
    "citation",
    "style",
    "failure",
    "evaluation",
    "audit",
    "exemplar",
    "runtime"
]

#: Words per token used for every *measured* figure in this module. Must match the factor used
#: for `CompilationManifest.measured_tokens`, otherwise admission and reporting disagree.
TOKEN_WORDS_TO_TOKENS = 1.33

LAYER_BUDGET_WEIGHTS = {
    "contract": 0.15,
    "core": 0.15,
    "reasoning": 0.20,
    "research": 0.10,
    "evidence": 0.10,
    "rhetoric": 0.10,
    "domain": 0.10,
    "section": 0.10,
    "citation": 0.10,
    "style": 0.10,
    "failure": 0.05,
    "evaluation": 0.05,
    "audit": 0.05,
    "runtime": 0.05,
}



#: Task contract (D-2 / THE-76).
#:
#: `task` was threaded from the CLI through `client.compile` and `loader.compile` into
#: `SignatureCompiler.compile`, read at line 690 — and then never used. A compile with
#: `citation_style="apa"` produced a prompt containing no APA module, because style matching only
#: ever added 80 points to a score while every citation module competed on declared `token_cost`,
#: which understates the real size by 1.5x-2.25x.
#:
#: A task names the modules that must be present for the compile to mean anything, and the minimum
#: measured budget at which that set fits. Reserved modules are admitted unconditionally: dropping
#: `citation_integrity` from a citation compile produces a prompt that is silently not a citation
#: compile, which is the failure this contract exists to prevent.
COMPILE_TASKS: Dict[str, "TaskSpec"] = {}


@dataclass(frozen=True)
class TaskSpec:
    """The reserved-module contract for one compile task."""

    name: str
    required_modules: Tuple[str, ...]
    #: Measured-token floor at which the reserved set plus the contract module and exemplars fit.
    min_measured_budget: int
    description: str

    def required_for(self, citation_style: str) -> Tuple[str, ...]:
        """Required module ids for this task, including the requested style module."""
        ids = list(self.required_modules)
        if citation_style and citation_style != "all":
            style_id = f"arkais.citation.{citation_style.lower()}"
            if style_id not in ids:
                ids.append(style_id)
        return tuple(ids)


#: Measured against the live corpus: the three reserved citation modules measure ~3408 tokens and
#: the contract module plus exemplar block another ~1247, so a citation compile cannot honestly be
#: bounded below ~4600 measured tokens. See `test_compile_task.py`.
_RESERVED_CITATION_MODULES = (
    "arkais.research.source_hierarchy",
    "arkais.citation.citation_integrity",
    "arkais.rhetoric.citation_weaving",
)

COMPILE_TASKS["general"] = TaskSpec(
    name="general",
    required_modules=(),
    min_measured_budget=1250,
    description="Default writing pass. No reserved modules; behaviour is unchanged from before.",
)

COMPILE_TASKS["citation"] = TaskSpec(
    name="citation",
    required_modules=_RESERVED_CITATION_MODULES,
    min_measured_budget=4600,
    description=(
        "Citation-scoped pass. Reserves source hierarchy, citation integrity, citation weaving, "
        "and the requested style module."
    ),
)

COMPILE_TASKS["audit"] = TaskSpec(
    name="audit",
    required_modules=("arkais.citation.citation_integrity",),
    min_measured_budget=1600,
    description=(
        "Verification pass. Reserves citation integrity so an audit compile cannot be produced "
        "without the rules it is meant to apply."
    ),
)

DEFAULT_TASK = "general"


def normalize_task(task: Optional[str]) -> Tuple[str, Optional[str]]:
    """Resolve a task name to a known spec, falling back to `general` with a reason.

    A typo must not crash a caller mid-pipeline, but it must not pass silently either — the
    fallback reason is recorded in the manifest so the omission is visible.
    """
    if not task:
        return DEFAULT_TASK, None
    key = str(task).strip().lower()
    if key in COMPILE_TASKS:
        return key, None
    return DEFAULT_TASK, f"unknown_task:{task}"

@dataclass
class SignatureModule:
    id: str
    layer: str
    name: str
    description: str
    content: str
    token_cost: int = 250
    priority: int = 50
    domain: List[str] = field(default_factory=lambda: ["all"])
    section: List[str] = field(default_factory=lambda: ["all"])
    competencies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class CompileRequest:
    domain: str = "all"
    section: str = "all"
    token_budget: int = 2500
    competencies: Optional[List[str]] = None
    slots: Optional[Dict[str, str]] = None
    inject_exemplars: bool = True
    citation_style: str = "all"
    task: str = "general"
    level: Optional[int] = None


@dataclass
class CompilationManifest:
    selected_module_ids: List[str]
    omitted_modules: Dict[str, str]
    dependency_expansion: Dict[str, List[str]]
    aliases_used: Dict[str, str]
    declared_tokens: int
    measured_tokens: int
    prompt_digest: str
    warnings: List[str]
    domain: str = "all"
    section: str = "all"
    token_budget: int = 2500
    layers_present: List[str] = field(default_factory=list)
    #: D-2 task contract. `task` is what the compile was *asked* to be; `reserved_module_ids` is
    #: what the contract guaranteed, so a caller can verify the guarantee rather than assume it.
    task: str = DEFAULT_TASK
    reserved_module_ids: List[str] = field(default_factory=list)
    task_min_measured_budget: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_module_ids": self.selected_module_ids,
            "omitted_modules": self.omitted_modules,
            "dependency_expansion": self.dependency_expansion,
            "aliases_used": self.aliases_used,
            "declared_tokens": self.declared_tokens,
            "measured_tokens": self.measured_tokens,
            "prompt_digest": self.prompt_digest,
            "warnings": self.warnings,
            "domain": self.domain,
            "section": self.section,
            "token_budget": self.token_budget,
            "layers_present": self.layers_present,
            "task": self.task,
            "reserved_module_ids": self.reserved_module_ids,
            "task_min_measured_budget": self.task_min_measured_budget,
        }


@dataclass
class CompiledSignature:
    prompt_text: str
    total_tokens: int
    included_modules: List[str]
    domain: str
    section: str
    exemplar_count: int = 0
    manifest: Optional[CompilationManifest] = None
    validation_status: str = "valid"

    @property
    def prompt_digest(self) -> str:
        if self.manifest and self.manifest.prompt_digest:
            return self.manifest.prompt_digest
        return hashlib.sha256(self.prompt_text.encode("utf-8")).hexdigest()

    @property
    def selected_module_ids(self) -> List[str]:
        if self.manifest and self.manifest.selected_module_ids:
            return self.manifest.selected_module_ids
        return self.included_modules

    @property
    def omitted_modules(self) -> Dict[str, str]:
        if self.manifest:
            return self.manifest.omitted_modules
        return {}

    @property
    def declared_tokens(self) -> int:
        if self.manifest:
            return self.manifest.declared_tokens
        return self.total_tokens

    @property
    def measured_tokens(self) -> int:
        if self.manifest:
            return self.manifest.measured_tokens
        return self.total_tokens

    @property
    def layers_present(self) -> List[str]:
        if self.manifest:
            return self.manifest.layers_present
        return []


CompilationResult = CompiledSignature


def parse_frontmatter(file_content: str) -> Tuple[Dict[str, Any], str]:
    """Lightweight standard-library parser for YAML frontmatter."""
    if not file_content.startswith("---"):
        return {}, file_content

    parts = file_content.split("---", 2)
    if len(parts) < 3:
        return {}, file_content

    fm_text = parts[1]
    body = parts[2].strip()
    metadata: Dict[str, Any] = {}

    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        # Handle simple JSON-like lists [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items = val[1:-1].split(",")
            metadata[key] = [item.strip().strip("'\"") for item in items if item.strip()]
        elif val.isdigit():
            metadata[key] = int(val)
        else:
            metadata[key] = val.strip("'\"")

    return metadata, body


def find_repo_root() -> Path:
    """Traverses upward to find the repository root directory containing 04_SIGNATURES."""
    p = Path(__file__).resolve().parent
    for _ in range(8):
        if (p / "04_SIGNATURES").exists():
            return p
        p = p.parent
    return Path.cwd()


class ExemplarSelector:
    """Dynamically samples authentic mined pre-2000 exemplars from JSON fixtures."""

    def __init__(self, fixtures_dir: Optional[Path] = None, seed: int = 42):
        root = find_repo_root()
        self.fixtures_dir = fixtures_dir or (root / "04_SIGNATURES" / "active" / "v3.0" / "exemplars")
        if not self.fixtures_dir.exists():
            # Fallback to active/exemplars
            alt = root / "04_SIGNATURES" / "active" / "exemplars"
            if alt.exists():
                self.fixtures_dir = alt

        self.seed = seed
        self.rng = random.Random(seed)
        self.mined_data: Dict[str, Any] = {}
        self._load_fixtures()

    def reset_rng(self, seed: Optional[int] = None):
        """Resets the random generator for deterministic exemplar sampling."""
        self.rng = random.Random(seed if seed is not None else self.seed)

    def _load_fixtures(self):
        jsonl_path = self.fixtures_dir / "exemplars.jsonl"
        mined_path = self.fixtures_dir / "mined_exemplars.json"

        # 1. Primary: load from exemplars.jsonl if present
        if jsonl_path.exists():
            records = []
            try:
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
            except Exception:
                records = []

            if records:
                by_cat = {}
                for r in records:
                    cat = r.get("category")
                    data = r.get("data", {})
                    by_cat.setdefault(cat, []).append(data)
                self.mined_data = {"exemplars": by_cat}
                return

        # 2. Fallback: load from mined_exemplars.json
        if mined_path.exists():
            try:
                self.mined_data = json.loads(mined_path.read_text(encoding="utf-8"))
            except Exception:
                self.mined_data = {}

    @staticmethod
    def _compute_shingles(text: str, k: int = 8) -> Set[str]:
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", text)]
        if len(words) < k:
            return {" ".join(words)}
        return {" ".join(words[i:i+k]) for i in range(len(words) - k + 1)}

    @classmethod
    def _jaccard(cls, set1: Set[str], set2: Set[str]) -> float:
        if not set1 or not set2:
            return 0.0
        return len(set1.intersection(set2)) / len(set1.union(set2))

    def _deduplicate_pool(self, items: List[Dict], max_per_paper: int = 4, threshold: float = 0.6) -> List[Dict]:
        """Suppresses near-duplicates (8-word shingle Jaccard > threshold) and caps items per paper."""
        deduped = []
        paper_counts: Dict[str, int] = {}
        shingle_pool: List[Set[str]] = []

        for item in items:
            paper_id = item.get("source", {}).get("paper_id", "unknown")
            if paper_counts.get(paper_id, 0) >= max_per_paper:
                continue

            # Extract representative text
            if "text" in item and isinstance(item["text"], list):
                raw = " ".join(item["text"])
            else:
                raw = item.get("snippet", "")

            shingles = self._compute_shingles(raw)
            if any(self._jaccard(shingles, existing) > threshold for existing in shingle_pool):
                continue

            shingle_pool.append(shingles)
            paper_counts[paper_id] = paper_counts.get(paper_id, 0) + 1
            deduped.append(item)

        return deduped

    def sample_cadence_pairs(self, k: int = 1, domain: Optional[str] = None) -> List[Dict]:
        pool = self.mined_data.get("exemplars", {}).get("cadence_pairs", [])
        if not pool:
            return []
        pool = self._deduplicate_pool(pool)
        if domain and domain != "all":
            filtered = [
                e for e in pool
                if domain.lower() in e.get("source", {}).get("stratum", "").lower()
                or domain.lower() in e.get("source", {}).get("discipline", "").lower()
            ]
            if filtered:
                pool = filtered
        return self.rng.sample(pool, min(k, len(pool)))

    def sample_citation_archetypes(self, k: int = 2) -> List[Dict]:
        exs = self.mined_data.get("exemplars", {})
        candidates = []
        for key in ["citation_contrastive", "citation_consensus", "citation_integral", "citation_methodological", "citation_method", "citation_passive"]:
            pool = exs.get(key, [])
            if pool:
                candidates.append(self.rng.choice(self._deduplicate_pool(pool)))
        if not candidates:
            return []
        return self.rng.sample(candidates, min(k, len(candidates)))

    def sample_hedging_boundaries(self, k: int = 1) -> List[Dict]:
        pool = self.mined_data.get("exemplars", {}).get("hedging_boundaries", [])
        if not pool:
            return []
        pool = self._deduplicate_pool(pool)
        return self.rng.sample(pool, min(k, len(pool)))

    def render_exemplar_block(self, domain: Optional[str] = None) -> str:
        """Formats sampled exemplars with anti-leakage instructions."""
        cadence = self.sample_cadence_pairs(k=1, domain=domain)
        citations = self.sample_citation_archetypes(k=2)
        hedges = self.sample_hedging_boundaries(k=1)

        if not (cadence or citations or hedges):
            return ""

        lines = [
            "## Authentic Corpus Exemplars",
            "",
            "> **Instruction**: Study the syntactic moves, rhythmic contrast, and grammatical attributions below. "
            "Calibrate your cadence and citation grammar to these authentic pre-2000 structures; "
            "do NOT copy their specific entities, facts, or findings.",
            ""
        ]

        if cadence:
            c = cadence[0]
            lines.append("### Exemplar: Cadence Contrast Pair")
            lines.append("<style-exemplar type=\"cadence_contrast\" source=\"pre-2000-corpus\">")
            lines.append(f"Condition: {c['text'][0]}")
            lines.append(f"Conclusion: {c['text'][1]}")
            lines.append("</style-exemplar>")
            lines.append("")

        if citations:
            lines.append("### Exemplars: Citation Weaving")
            for cite in citations:
                arch_name = cite.get("archetype", "archetype")
                lines.append(f"<style-exemplar type=\"citation_{arch_name}\" source=\"pre-2000-corpus\">")
                lines.append(cite.get("snippet", ""))
                lines.append("</style-exemplar>")
            lines.append("")

        if hedges:
            h = hedges[0]
            lines.append("### Exemplar: Hedging Boundary Condition")
            lines.append("<style-exemplar type=\"hedging_boundary\" source=\"pre-2000-corpus\">")
            lines.append(h.get("snippet", ""))
            lines.append("</style-exemplar>")
            lines.append("")

        return "\n".join(lines)

    def bind_module_slots(self, module_content: str, domain: Optional[str] = None) -> str:
        """Binds named <exemplar-slot name=\"...\"/> directives within module bodies."""
        if "<exemplar-slot" not in module_content:
            return module_content

        def _replacer(match):
            slot_name = match.group(1)
            if slot_name in ("cadence_pair", "hypotactic_subordination", "paragraph_progression"):
                sampled = self.sample_cadence_pairs(k=1, domain=domain)
                if sampled:
                    c = sampled[0]
                    return (
                        f"<style-exemplar type=\"cadence_contrast\" source=\"pre-2000-corpus\">\n"
                        f"Condition: {c['text'][0]}\n"
                        f"Conclusion: {c['text'][1]}\n"
                        f"</style-exemplar>"
                    )
            elif (
                slot_name.startswith("citation_")
                or slot_name in ("citation_archetype", "archetype_rotation", "integral_subject", "synthesis_patterns", "dispute_synthesis", "discussion_synthesis")
            ):
                sampled = self.sample_citation_archetypes(k=1)
                if sampled:
                    cite = sampled[0]
                    return (
                        f"<style-exemplar type=\"citation_{cite.get('archetype', 'archetype')}\" source=\"pre-2000-corpus\">\n"
                        f"{cite.get('snippet', '')}\n"
                        f"</style-exemplar>"
                    )
            elif slot_name in ("hedging_boundary", "boundary_condition", "gap_mechanics"):
                sampled = self.sample_hedging_boundaries(k=1)
                if sampled:
                    h = sampled[0]
                    return (
                        f"<style-exemplar type=\"hedging_boundary\" source=\"pre-2000-corpus\">\n"
                        f"{h.get('snippet', '')}\n"
                        f"</style-exemplar>"
                    )

            # Fallback for any other slot name: try citation archetype or cadence
            sampled = self.sample_citation_archetypes(k=1)
            if sampled:
                cite = sampled[0]
                return (
                    f"<style-exemplar type=\"citation_{cite.get('archetype', 'archetype')}\" source=\"pre-2000-corpus\">\n"
                    f"{cite.get('snippet', '')}\n"
                    f"</style-exemplar>"
                )
            return ""

        return re.sub(r'<exemplar-slot\s+name=["\']([^"\']+)["\']\s*/>', _replacer, module_content)


class SignatureCompiler:
    """Dynamic modular compiler implementing the ChatGPT-specified architecture."""

    def __init__(self, modules_dir: Optional[Path] = None, fixtures_dir: Optional[Path] = None):
        root = find_repo_root()
        self.modules_dir = modules_dir or (root / "04_SIGNATURES" / "candidate" / "v3.0")
        self.exemplar_selector = ExemplarSelector(fixtures_dir)
        self.modules: Dict[str, SignatureModule] = {}
        self.discover()

    #: Memoised measured cost per module. See `_measured_cost`.
    _measured_cache: Dict[tuple, int]
    _exemplar_cache: Dict[str, int]

    def _measured_cost(
        self,
        mod: SignatureModule,
        inject_exemplars: bool = False,
        target_domain: str = "all",
    ) -> int:
        """Size of a module **as compose will actually render it**.

        `token_cost` comes from module frontmatter and understates the composed size by
        1.5x-2.25x across the live corpus (declared 2450 vs measured 4827 for the reserved
        citation set). Budgeting on the declared figure is what let a citation compile silently
        shed its own citation modules.

        Measuring bare `mod.content` is not enough either: `compose()` also prepends a
        `<!-- MODULE: ... -->` header and, when exemplars are enabled, binds an exemplar block
        *into* the body. Ignoring that under-counts by ~350 tokens across three modules and
        overshoots the ceiling, so the render is measured rather than the source.

        Memoised on (module, exemplars, domain) because binding is deterministic.
        """
        cache = getattr(self, "_measured_cache", None)
        if cache is None:
            cache = self._measured_cache = {}
        key = (mod.id, bool(inject_exemplars), target_domain)
        if key not in cache:
            body = mod.content
            if inject_exemplars:
                body = self.exemplar_selector.bind_module_slots(body, domain=target_domain)
            rendered = f"<!-- MODULE: {mod.id} ({mod.layer}) -->\n" + body
            cache[key] = round(len(rendered.split()) * TOKEN_WORDS_TO_TOKENS)
        return cache[key]

    def _exemplar_block_cost(self, inject_exemplars: bool, target_domain: str) -> int:
        """Fixed cost of the dynamic exemplar block, reserved before module admission."""
        if not inject_exemplars:
            return 0
        cache = getattr(self, "_exemplar_cache", None)
        if cache is None:
            cache = self._exemplar_cache = {}
        if target_domain not in cache:
            block = self.exemplar_selector.render_exemplar_block(target_domain)
            cache[target_domain] = round(len(block.split()) * TOKEN_WORDS_TO_TOKENS) if block else 0
        return cache[target_domain]

    def discover(self) -> Dict[str, SignatureModule]:
        """Discovers and parses all modules under modules_dir."""
        self.modules.clear()
        if not self.modules_dir.exists():
            return self.modules

        for md_path in self.modules_dir.rglob("*.md"):
            try:
                content = md_path.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(content)
                mod_id = meta.get("id", md_path.stem)
                raw_layer = meta.get("layer") or re.sub(r"^\d+_", "", md_path.parent.name)
                layer_map = {
                    "citations": "citation",
                    "domains": "domain",
                    "sections": "section",
                    "contracts": "contract",
                }
                layer = layer_map.get(raw_layer, raw_layer)

                # Estimate token cost if missing (~4 chars per token)
                token_cost = meta.get("token_cost", max(int(len(body) / 4), 50))

                mod = SignatureModule(
                    id=mod_id,
                    layer=layer,
                    name=meta.get("name", mod_id),
                    description=meta.get("description", ""),
                    content=body,
                    token_cost=token_cost,
                    priority=meta.get("priority", 50),
                    domain=meta.get("domain", ["all"]),
                    section=meta.get("section", ["all"]),
                    competencies=meta.get("competencies", []),
                    dependencies=meta.get("dependencies", [])
                )
                self.modules[mod_id] = mod
            except Exception:
                continue

        # Register backward-compatibility aliases
        legacy_aliases = {
            "arkais.core.contract": "arkais.contract.system_directive",
            "arkais.reasoning.interrogation": "arkais.reasoning.argument_architecture",
            "arkais.citations.archetypes": "arkais.rhetoric.citation_weaving",
            "arkais.domain.stem": "arkais.domain.cs_systems",
            "arkais.domain.social": "arkais.domain.social_science",
            "arkais.domain.biomed": "arkais.domain.biomedical",
            "arkais.domain.humanities": "arkais.domain.formal_theory",
            "arkais.audit.gate": "arkais.evaluation.structural_audit",
        }
        for legacy_id, canonical_id in legacy_aliases.items():
            if canonical_id in self.modules and legacy_id not in self.modules:
                c = self.modules[canonical_id]
                self.modules[legacy_id] = SignatureModule(
                    id=legacy_id,
                    layer=c.layer,
                    name=c.name,
                    description=f"[Legacy Alias -> {canonical_id}] {c.description}",
                    content=c.content,
                    token_cost=c.token_cost,
                    priority=c.priority,
                    domain=c.domain,
                    section=c.section,
                    competencies=c.competencies,
                    dependencies=c.dependencies,
                )

        return self.modules

    def score(
        self,
        module: SignatureModule,
        target_domain: str,
        target_section: str,
        requested_competencies: Optional[List[str]] = None,
        citation_style: str = "all",
        task: str = DEFAULT_TASK
    ) -> float:
        """Scores a module based on layer centrality, domain/section fit, and competencies."""
        score = float(module.priority)

        # Reserved modules for this task outrank everything else. Without this the citation
        # modules compete on priority alone and lose to domain modules on measured size.
        if task in COMPILE_TASKS and module.id in COMPILE_TASKS[task].required_for(citation_style):
            score += 10_000.0

        # Invariant baseline bonuses
        if module.layer in ("contract", "core"):
            score += 100.0
        elif module.layer == "reasoning":
            score += 50.0

        # Domain fit - reward explicit disciplinary specificity
        if target_domain != "all" and target_domain in module.domain and "all" not in module.domain:
            score += 60.0
        elif "all" in module.domain or target_domain in module.domain:
            score += 20.0
        else:
            score -= 60.0

        # Section fit - reward explicit section specificity
        if target_section != "all" and target_section in module.section and "all" not in module.section:
            score += 60.0
        elif "all" in module.section or target_section in module.section:
            score += 20.0
        else:
            score -= 60.0

        # Competency matching
        if requested_competencies:
            for c in requested_competencies:
                if c in module.competencies:
                    score += 15.0

        # Citation style matching
        if citation_style != "all" and module.layer == "citation":
            if citation_style.lower() in module.id.lower() or any(citation_style.lower() in c.lower() for c in module.competencies):
                score += 80.0

        return score

    def prioritize(
        self,
        target_domain: str = "all",
        target_section: str = "all",
        requested_competencies: Optional[List[str]] = None,
        citation_style: str = "all",
        task: str = DEFAULT_TASK
    ) -> List[SignatureModule]:
        """Scores and prioritizes modules while resolving dependencies."""
        scored = []
        for mod in self.modules.values():
            s = self.score(
                mod, target_domain, target_section, requested_competencies, citation_style, task
            )
            if s > 0:
                scored.append((s, mod))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected: Dict[str, SignatureModule] = {}
        dep_expansion: Dict[str, List[str]] = {}

        # Greedily include dependencies
        for _, mod in scored:
            selected[mod.id] = mod
            for dep_id in mod.dependencies:
                if dep_id in self.modules and dep_id not in selected:
                    selected[dep_id] = self.modules[dep_id]
                    dep_expansion.setdefault(mod.id, []).append(dep_id)

        self.last_dependency_expansion = dep_expansion
        return list(selected.values())

    def budget(
        self,
        modules: List[SignatureModule],
        token_budget: int = 2500,
        task: str = DEFAULT_TASK,
        citation_style: str = "all",
        inject_exemplars: bool = False,
        target_domain: str = "all",
    ) -> List[SignatureModule]:
        """Enforces token budgeting while ensuring multi-tier layer diversity.

        Admission is decided on **measured** cost, not the frontmatter `token_cost`, which
        understates composed size by 1.5x-2.25x. Budgeting on the declared figure is what let a
        citation compile shed its own citation modules without exceeding its stated ceiling.

        Reserved modules for `task` are admitted unconditionally, ahead of every other tier. A
        citation compile that omits `citation_integrity` is not a citation compile, so the ceiling
        is not allowed to decide that. `self.budget_shortfall` records when the reserved set alone
        exceeds the ceiling, so the caller can be told rather than silently over budget.
        """
        accepted_modules: List[SignatureModule] = []
        accepted_ids: set = set()

        cost_of = lambda mod: self._measured_cost(mod, inject_exemplars, target_domain)  # noqa: E731

        # `token_budget` is a **declared**-token budget. That is what callers have always passed
        # and what `declared_tokens` reports back, so it keeps meaning that here. Admission is
        # decided on measured cost, which is larger — frontmatter `token_cost` understates the
        # composed render by 1.5x-2.25x — so the ceiling is converted by the candidate pool's own
        # declared->measured ratio before being compared. Measuring the pool rather than pinning a
        # constant keeps the conversion honest as modules and corpus change, which is the whole
        # reason D-2 moved admission onto measured cost in the first place.
        declared_total = sum(mod.token_cost for mod in modules)
        measured_total = sum(cost_of(mod) for mod in modules)
        scale = (measured_total / declared_total) if declared_total else 1.0
        ceiling = int(round(token_budget * scale))
        #: The ceiling admission actually applied, in measured tokens. `token_budget` is the
        #: caller's declared figure; reporting one while comparing against the other would be
        #: the same unit confusion this conversion exists to remove.
        self.budget_ceiling = ceiling

        # The dynamic exemplar block is appended once, after every module, so reserve it up front
        # rather than discovering at compose time that the ceiling was already spent.
        allocated_tokens = self._exemplar_block_cost(inject_exemplars, target_domain)

        spec = COMPILE_TASKS.get(task)
        reserved = spec.required_for(citation_style) if spec else ()
        reserved_present = [mid for mid in reserved if mid in self.modules]
        reserved_modules = [self.modules[mid] for mid in reserved_present]

        # Tier 0: Reserved modules for this task, admitted before the budget is consulted.
        for mod in reserved_modules:
            if mod.id not in accepted_ids:
                accepted_modules.append(mod)
                accepted_ids.add(mod.id)
                allocated_tokens += cost_of(mod)

        reserved_cost = allocated_tokens
        self.budget_shortfall = max(0, reserved_cost - ceiling) if reserved_modules else 0
        self.reserved_module_ids = list(reserved_present)

        # Tier 1: Include foundational contract / core (first contract module)
        for mod in modules:
            if mod.layer in ("contract", "core") and mod.id not in accepted_ids:
                accepted_modules.append(mod)
                accepted_ids.add(mod.id)
                allocated_tokens += cost_of(mod)
                break

        # Tier 2: Layer diversity pass (ensure at least 1 module from key realization tiers)
        key_tiers = ["domain", "reasoning", "citation", "section", "research", "rhetoric", "style"]
        for tier in key_tiers:
            for mod in modules:
                if mod.layer == tier and mod.id not in accepted_ids:
                    cost = cost_of(mod)
                    if allocated_tokens + cost <= ceiling:
                        accepted_modules.append(mod)
                        accepted_ids.add(mod.id)
                        allocated_tokens += cost
                        break

        # Tier 3: Greedily fill remaining budget with highest-priority modules (audit gate decoupled)
        for mod in modules:
            if mod.layer in ("audit", "evaluation"):
                continue
            if mod.id not in accepted_ids:
                cost = self._measured_cost(mod)
                if allocated_tokens + cost <= ceiling:
                    accepted_modules.append(mod)
                    accepted_ids.add(mod.id)
                    allocated_tokens += cost

        return accepted_modules

    def order(self, modules: List[SignatureModule]) -> List[SignatureModule]:
        """Enforces the strict ordering rule: 'Reasoning precedes realization'."""
        layer_indices = {layer: i for i, layer in enumerate(LAYER_ORDER)}

        def sort_key(mod: SignatureModule):
            layer_idx = layer_indices.get(mod.layer, 99)
            return (layer_idx, -mod.priority)

        return sorted(modules, key=sort_key)

    def compose(
        self,
        ordered_modules: List[SignatureModule],
        slots: Optional[Dict[str, str]] = None,
        inject_exemplars: bool = True,
        target_domain: str = "all"
    ) -> Tuple[str, int]:
        """Assembles prompt text and injects slot values and exemplars."""
        self.exemplar_selector.reset_rng(42)
        slots = slots or {}
        chunks = []
        total_tokens = sum(m.token_cost for m in ordered_modules)

        for mod in ordered_modules:
            body = mod.content
            # Slot substitution
            for slot_key, slot_val in slots.items():
                body = body.replace(f"{{{{{slot_key}}}}}", slot_val)
            # Bind module-level exemplar slots if enabled
            if inject_exemplars:
                body = self.exemplar_selector.bind_module_slots(body, domain=target_domain)
            chunks.append(f"<!-- MODULE: {mod.id} ({mod.layer}) -->\n" + body)

        # Inject exemplars before audit
        if inject_exemplars:
            exemplar_text = self.exemplar_selector.render_exemplar_block(target_domain)
            if exemplar_text:
                chunks.append("<!-- MODULE: arkais.exemplars.dynamic -->\n" + exemplar_text)
                total_tokens += 150

        full_prompt = "\n\n---\n\n".join(chunks)
        return full_prompt, total_tokens

    def compile(
        self,
        domain: Union[str, CompileRequest] = "all",
        section: str = "all",
        token_budget: int = 2500,
        competencies: Optional[List[str]] = None,
        slots: Optional[Dict[str, str]] = None,
        inject_exemplars: bool = True,
        citation_style: str = "all",
        task: str = "general"
    ) -> CompiledSignature:
        """Executes full compilation pipeline."""
        if isinstance(domain, CompileRequest):
            req = domain
            domain = req.domain
            section = req.section
            token_budget = req.token_budget
            competencies = req.competencies
            slots = req.slots
            inject_exemplars = req.inject_exemplars
            citation_style = req.citation_style
            task = req.task

        task, task_note = normalize_task(task)
        self.budget_shortfall = 0
        self.reserved_module_ids = []

        prioritized = self.prioritize(domain, section, competencies, citation_style, task)
        budgeted = self.budget(
            prioritized,
            token_budget,
            task,
            citation_style,
            inject_exemplars=inject_exemplars,
            target_domain=domain,
        )
        ordered = self.order(budgeted)
        prompt_text, total_tokens = self.compose(
            ordered,
            slots=slots,
            inject_exemplars=inject_exemplars,
            target_domain=domain
        )

        selected_ids = [m.id for m in ordered]
        prioritized_ids = {m.id for m in prioritized}

        # Calculate omissions for all available modules
        omissions: Dict[str, str] = {}
        for mod_id, mod in self.modules.items():
            if mod_id not in selected_ids:
                if mod_id in prioritized_ids:
                    if mod.layer in ("audit", "evaluation"):
                        omissions[mod_id] = "evaluation_layer_decoupled"
                    else:
                        omissions[mod_id] = "budget_exceeded"
                else:
                    if domain != "all" and domain not in mod.domain and "all" not in mod.domain:
                        omissions[mod_id] = "domain_mismatch"
                    elif section != "all" and section not in mod.section and "all" not in mod.section:
                        omissions[mod_id] = "section_mismatch"
                    elif mod.layer in ("audit", "evaluation"):
                        omissions[mod_id] = "evaluation_layer_decoupled"
                    else:
                        omissions[mod_id] = "priority_low"

        prompt_digest = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        measured_tokens = round(len(prompt_text.split()) * TOKEN_WORDS_TO_TOKENS)
        layers_present = list(dict.fromkeys(m.layer for m in ordered))

        warnings: List[str] = []
        if task_note:
            warnings.append(
                f"Unknown compile task {task_note.split(':', 1)[1]!r}; fell back to "
                f"{DEFAULT_TASK!r}, so no modules were reserved for it."
            )
        if total_tokens > token_budget:
            warnings.append(f"Prompt declared tokens ({total_tokens}) exceed budget ceiling ({token_budget})")

        spec = COMPILE_TASKS[task]
        shortfall = getattr(self, "budget_shortfall", 0)
        if shortfall:
            ceiling = getattr(self, "budget_ceiling", token_budget)
            warnings.append(
                f"Reserved modules for task {task!r} measure {shortfall} tokens beyond the "
                f"effective ceiling ({ceiling} measured, converted from a declared budget of "
                f"{token_budget}). They were admitted anyway: omitting them would make this "
                f"compile silently not a {task} compile. Measured floor for {task!r} is "
                f"{spec.min_measured_budget}."
            )
        reserved_ids = set(getattr(self, "reserved_module_ids", []))
        dropped_reserved = sorted(reserved_ids - set(selected_ids))
        if dropped_reserved:
            # Should be impossible — reserved modules are admitted ahead of the budget — but if a
            # future refactor breaks that, the compile must say so rather than look fine.
            warnings.append(f"Reserved modules missing from the compile: {dropped_reserved}")

        manifest = CompilationManifest(
            selected_module_ids=selected_ids,
            omitted_modules=omissions,
            dependency_expansion=getattr(self, "last_dependency_expansion", {}),
            aliases_used={},
            declared_tokens=total_tokens,
            measured_tokens=measured_tokens,
            prompt_digest=prompt_digest,
            warnings=warnings,
            domain=domain,
            section=section,
            token_budget=token_budget,
            layers_present=layers_present,
            task=task,
            reserved_module_ids=sorted(reserved_ids),
            task_min_measured_budget=spec.min_measured_budget
        )

        return CompiledSignature(
            prompt_text=prompt_text,
            total_tokens=total_tokens,
            included_modules=selected_ids,
            domain=domain,
            section=section,
            exemplar_count=4 if inject_exemplars else 0,
            manifest=manifest,
            validation_status="valid"
        )

    def compile_ladder(
        self,
        level: int,
        domain: str = "all",
        section: str = "all",
        token_budget: int = 2500,
        slots: Optional[Dict[str, str]] = None
    ) -> CompiledSignature:
        """
        Compiles prompts along Claude's Empirical Evaluation Ladder (L0 to L5):
        - L0: Baseline 17-line negative prompt (legacy negative constraints only)
        - L1: Core authoring contract (00_contract + 01_reasoning)
        - L2: L1 + authentic mined exemplars (02_research + pre-2000 corpus exemplars)
        - L3: L2 + section blueprint (06_sections + 03_rhetoric)
        - L4: L3 + domain scaffold (05_domains + 04_style)
        - L5: L4 + citation archetypes (07_citations) + failure boundary + factored verification
        """
        if level <= 0:
            baseline_prompt = (
                "# ARKAIS BASELINE v1.0: NEGATIVE CONSTRAINTS DIRECTIVE\n\n"
                "You are an academic writing assistant. You must write rigorous scholarly prose "
                "while strictly avoiding the generic hallmarks of artificial intelligence writing.\n\n"
                "## BANNED BUZZWORDS & FILLER PHRASES\n"
                "Do not use: delve, delving, tapestry, revolutionize, testament, multifaceted, "
                "pivotal, game-changing, paramount, beacon, plethora, interplay, cornerstone, "
                "synergy, orchestrate, foster, seamlessly, holistic, cutting-edge, vibrant, illuminating.\n\n"
                "## BANNED OPENERS\n"
                "Never open sentences with:\n"
                "- 'In order to understand...'\n"
                "- 'It is important to remember/note that...'\n"
                "- 'Furthermore, the role of...'\n"
                "- 'In today's rapidly evolving...'\n"
                "- 'This is not only X but also Y...'\n"
                "- 'Delving into...'\n\n"
                "## BANNED METAPHORS & FALSE DICHOTOMIES\n"
                "- Never use patronizing didactic analogies ('imagine a library', 'at its core', 'simply put').\n"
                "- Never use synthetic contrast pairs or false dichotomies ('is not merely X, but rather Y').\n"
            )
            prompt_clean = baseline_prompt.strip()
            prompt_digest = hashlib.sha256(prompt_clean.encode("utf-8")).hexdigest()
            manifest = CompilationManifest(
                selected_module_ids=["baseline.negative_prompt"],
                omitted_modules={mid: "ladder_level_0_all_omitted" for mid in self.modules},
                dependency_expansion={},
                aliases_used={},
                declared_tokens=150,
                measured_tokens=round(len(prompt_clean.split()) * 1.33),
                prompt_digest=prompt_digest,
                warnings=[],
                domain=domain,
                section=section,
                token_budget=token_budget,
                layers_present=["baseline"]
            )
            return CompiledSignature(
                prompt_text=prompt_clean,
                total_tokens=150,
                included_modules=["baseline.negative_prompt"],
                domain=domain,
                section=section,
                exemplar_count=0,
                manifest=manifest,
                validation_status="valid"
            )

        ladder_allowed_layers = {
            1: {"contract", "core", "reasoning"},
            2: {"contract", "core", "reasoning", "research", "evidence"},
            3: {"contract", "core", "reasoning", "research", "evidence", "rhetoric", "section"},
            4: {"contract", "core", "reasoning", "research", "evidence", "rhetoric", "section", "domain", "style"},
            5: {"contract", "core", "reasoning", "research", "evidence", "rhetoric", "section", "domain", "style", "citation", "failure"}
        }

        allowed_layers = ladder_allowed_layers.get(level, ladder_allowed_layers[5])
        inject_exemplars = (level >= 2)

        # Prioritize with layer filtering
        prioritized = [
            m for m in self.prioritize(domain, section)
            if m.layer in allowed_layers
        ]
        budgeted = self.budget(prioritized, token_budget)
        ordered = self.order(budgeted)
        prompt_text, total_tokens = self.compose(
            ordered,
            slots=slots,
            inject_exemplars=inject_exemplars,
            target_domain=domain
        )

        if level >= 5:
            verification_directive = (
                "\n\n---\n\n<!-- PROTOCOL: Factored Verification & Toulmin Interrogation -->\n"
                "## Factored Claim Verification & Toulmin Interrogation Protocol\n\n"
                "1. **Isolated Verification**: Every empirical number, performance metric, and citation "
                "must be independently verifiable against provided source manifests. If unverified, "
                "you MUST register a visible gap tag: `[AUTHOR: verify ...]` or `[CITE: ...]`. "
                "Never invent plausible-sounding values or citations.\n"
                "2. **Toulmin Completeness**: Every substantive claim requires explicit Grounds (empirical data), "
                "Warrant (connecting mechanism), Backing (theoretical framework), and Qualifier (scope of validity).\n"
                "3. **Inference Boundaries**: Mark exact epistemic limits using calibrated modals ('suggests', "
                "'is consistent with') rather than ungrounded flat certainty."
            )
            prompt_text += verification_directive
            total_tokens += 120

        selected_ids = [m.id for m in ordered]
        prioritized_ids = {m.id for m in prioritized}
        omissions = {}
        for mod_id, mod in self.modules.items():
            if mod_id not in selected_ids:
                if mod.layer not in allowed_layers:
                    omissions[mod_id] = "ladder_layer_filtered"
                elif mod_id in prioritized_ids:
                    omissions[mod_id] = "budget_exceeded"
                else:
                    omissions[mod_id] = "priority_low"

        prompt_digest = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        manifest = CompilationManifest(
            selected_module_ids=selected_ids,
            omitted_modules=omissions,
            dependency_expansion={},
            aliases_used={},
            declared_tokens=total_tokens,
            measured_tokens=round(len(prompt_text.split()) * 1.33),
            prompt_digest=prompt_digest,
            warnings=[],
            domain=domain,
            section=section,
            token_budget=token_budget,
            layers_present=list(dict.fromkeys(m.layer for m in ordered))
        )

        return CompiledSignature(
            prompt_text=prompt_text,
            total_tokens=total_tokens,
            included_modules=selected_ids,
            domain=domain,
            section=section,
            exemplar_count=4 if inject_exemplars else 0,
            manifest=manifest,
            validation_status="valid"
        )

