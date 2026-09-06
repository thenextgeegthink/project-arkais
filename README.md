<!-- Project Arkais Hero Banner (Custom Author Design) -->
<!-- <p align="center"><img src="assets/banner.png" alt="Project Arkais Banner" width="100%"></p> -->

<div align="center">

# Project Arkais

### Deterministic Scholarly Stylometrics, Citation Weaving & BYOK Verification Engine

[![Release: v1.0.0-beta.1](https://img.shields.io/badge/release-v1.0.0--beta.1-orange.svg)](https://github.com/thenextgeegthink/project-arkais/releases)
[![Status: Public Beta](https://img.shields.io/badge/status-public_beta-yellow.svg)](#public-beta-status)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-brightgreen.svg)](#zero-dependencies)
[![Architecture: BYOK](https://img.shields.io/badge/security-BYOK%20%7C%20POSIX%200600-purple.svg)](#byok-security)

**Project Arkais** is a scholarly cognitive infrastructure library developed by **The Next Geek Think (NGT)** and built by **Dreadnought Studio**. Grounded in empirical stylometric analysis of pre-LLM academic literature, Arkais provides tools to detect synthetic AI defects, format and rhetorically weave academic citations, and resolve DOI publication records without third-party API keys or centralized subscriptions.

[Website](https://geegthink.com/project-arkais) • [Documentation](docs/) • [Architecture](docs/architecture.md) • [Examples](examples/)

</div>

---

> [!NOTE]
> ### 🧪 PUBLIC BETA / DEVELOPER PREVIEW (Milestone 3)
> **Project Arkais is currently in active Public Beta.** The headless Python client SDK, deterministic 10-gate stylometric audit engine, and citation weaving engine are open for community evaluation, benchmarking, and developer integration.
> The dedicated visual workspace (**Arkais Studio / Whim Paper prototype**) is actively under development in Milestone 4.

---

## Key Capabilities

- ⚡ **Zero External Dependencies**: Pure standard library implementation. Installs in `<0.1s` and executes with sub-millisecond overhead. No heavyweight dependencies, no version conflicts.
- 🔬 **10-Gate Stylometric Audit Engine**: Evaluates manuscript drafts against empirical baselines derived from peer-reviewed literature across Sentence Variance ($\sigma \ge 15.0$), Nominalization ($4.0\%–8.5\%$), Epistemic Balance ($\ge 1.4:1$), Lexical Discipline ($0$ AI buzzwords), and Citation Topology.
- 📚 **Polite-Pool Reference Resolver**: Queries CrossRef and OpenAlex polite pools at 50 req/s with **zero user API keys** required. Includes an atomic disk cache (`<1ms` repeat lookups) and a Phantom Citation Detector (`REF-001`) that blocks fabricated AI literature.
- 🖋️ **CSL & Multi-Style Citation Engine**: Formats citations in APA 7th, IEEE, Nature (superscripts), Harvard, and Chicago, plus valid BibTeX generation.
- 🧬 **Rhetorical Citation Weaving**: Eliminates monotone AI parenthetical slop `(Author, Year)` by weaving citations across 5 authentic syntactic archetypes: Integral Subject, Passive Agent, Contrastive Tension, Methodological Anchor, and Consensus Cluster.
- 🛡️ **Standalone BYOK Security Sandbox**: Bring Your Own Key credentials manager with strict POSIX `0600` permission enforcement, memory masking (`RedactedSecret`), and strict zero-telemetry egress enforcement.
- 💻 **Terminal CLI**: Run `arkais audit`, `arkais verify-doi`, `arkais verify-citation`, and `arkais signatures` directly in your terminal or in automated CI/CD pipelines.

---

## Installation

```bash
pip install project-arkais
```

Arkais requires Python 3.10+ and has **zero third-party dependencies**.

---

## Command-Line Interface (CLI)

Arkais provides a built-in CLI for terminal and CI/CD pipeline execution:

```bash
# Audit an academic paper draft against calibrated stylometrics
arkais audit manuscript.md

# Machine-readable JSON output for pre-commit hooks or GitHub Actions
arkais audit manuscript.md --json

# Resolve paper metadata and authenticity via DOI (zero keys needed)
arkais verify-doi 10.1016/j.joule.2018.05.006

# Guard against AI hallucinated citations
arkais verify-citation --title "Direct Air Capture of CO2" --author "David Keith"

# Inspect available calibration baselines
arkais signatures
```

---

## Python SDK Quickstart

### 1. Stylometric Manuscript Audit

```python
from arkais import ArkaisClient

client = ArkaisClient()

manuscript = """
The capture of atmospheric carbon dioxide represents an asymptotic thermodynamic challenge.
While early conceptual models posited severe energetic penalties, recent pilot contactor data
demonstrates that packing geometry dictates mass transfer rates.
"""

# Audit text against calibrated signature
scorecard = client.audit(manuscript)

print(f"Compliant: {scorecard.passed}")
print(f"Composite Score: {scorecard.overall_score}/100")
for metric, result in scorecard.metrics.items():
    print(f"  [{'PASS' if result['passed'] else 'FAIL'}] {metric}: {result['value']}")
```

### 2. Zero-Key DOI Resolution & Phantom Citation Guard

```python
from arkais import ArkaisClient

client = ArkaisClient()

# Resolve paper metadata via CrossRef / OpenAlex polite pool
ref = client.resolve_doi("10.1016/j.joule.2018.05.006")

print(f"Title: {ref.title}")
print(f"Authors: {ref.authors}")
print(f"Journal: {ref.journal} ({ref.year})")

# Verify citation authenticity against fabricated LLM hallucinations
is_authentic = client.verify_citation(
    title="A Process for Capturing CO2 from the Atmosphere",
    author="David Keith"
)
print(f"Authentic Record: {is_authentic}")
```

### 3. Multi-Style Citation Formatting & Rhetorical Weaving

```python
from arkais import ArkaisClient
from arkais.citation import CitationStyle, SyntacticRole

client = ArkaisClient()
ref = client.resolve_doi("10.1016/j.joule.2018.05.006")

# In-Text Citation Formats
print(client.format_citation(ref, style=CitationStyle.APA))    # (Keith et al., 2018)
print(client.format_citation(ref, style=CitationStyle.IEEE))   # [1]
print(client.format_citation(ref, style=CitationStyle.NATURE)) # ¹

# Authentically weave citation into narrative prose
sentence = client.weave_citation(
    ref,
    role=SyntacticRole.INTEGRAL_SUBJECT,
    claim="demonstrated that contactor packing dictates mass transfer rates."
)
print(sentence)
# Output: "Keith and colleagues (2018) demonstrated that contactor packing dictates mass transfer rates."
```

### 4. Standalone BYOK Credentials Manager

```python
from arkais import ArkaisClient

# Auto-discovers from explicit args > env vars > .env > ~/.config/arkais/credentials.json
client = ArkaisClient()

# Credentials are protected by RedactedSecret masking in memory and logs
secret = client.get_credential("OPENAI_API_KEY")
if secret:
    print(f"Discovered: {secret}")  # Prints: sk-proj-****...3f8a
    raw_key = secret.reveal()        # Explicit reveal only when building HTTP headers
```

---

## Stylometric 10-Gate Quality Assurance

| Gate | Category | Calibrated Target | Purpose |
| :---: | :--- | :---: | :--- |
| **S1** | Sentence Length Variance | $\sigma \ge 15.0$ words | Eliminates robotic, monotonic rhythm |
| **S2** | Subordination & Depth | Hypo/Parataxis balance | Enforces complex academic clause depth |
| **D1** | Nominalization Density | $4.0\% - 8.5\%$ | Matches empirical academic density |
| **D2** | Lexical Anti-Pattern Guard | $0$ AI buzzwords | Eradicates *delve, testament, pivotal, beacon* |
| **D3** | Promotional Modifiers | $0$ adverbs/adjectives | Prohibits marketing language in science |
| **E1** | Epistemic Ratio | $\ge 1.4:1$ (Hedges:Certainty) | Prohibits ungrounded authoritative claims |
| **E2** | Boundary Qualification | Qualified scope | Prevents ungrounded universal generalizations |
| **C1** | Citation Topology | $\ge 2.0 / 1\text{k words}$ | Guarantees foundational literature grounding |
| **C2** | Phantom Citation Guard | $100\%$ verified DOIs | Blocks fabricated hallucinated references |
| **P1** | Structural Progression | Deductive / Empirical | Preserves formal section rhetorical arcs |

---

## Star History

<a href="https://star-history.com/#thenextgeegthink/project-arkais&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=thenextgeegthink/project-arkais&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=thenextgeegthink/project-arkais&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=thenextgeegthink/project-arkais&type=Date" width="100%" />
 </picture>
</a>

---

## Governance & Ecosystem

- **Brand**: [The Next Geek Think (NGT)](https://geegthink.com)
- **Builder**: Dreadnought Studio
- **Architecture**: Sovereign Client-Side Runtime, Bring Your Own Key (BYOK)
- **Zero-Telemetry**: No user text, search queries, or API keys are ever transmitted to NGT servers.

## License

The Project Arkais Client SDK is licensed under the [Apache License 2.0](LICENSE).
Proprietary historical training corpora, behavioral foundations, and generation signatures are protected cognitive infrastructure assets of The Next Geek Think.
