# Project Arkais — Developer Quickstart

Welcome to **Project Arkais**, the deterministic scholarly stylometrics, citation weaving, and BYOK verification engine developed by **The Next Geek Think (NGT)** and built by **Dreadnought Studio**.

---

## 1. Installation

Project Arkais requires Python 3.10+ and relies exclusively on standard library primitives for sub-millisecond execution and zero dependency footprint:

```bash
pip install project-arkais
```

To verify the installation:
```bash
arkais --version
```

---

## 2. Command-Line Usage

### Auditing Academic Drafts
You can audit any markdown or plain text file to evaluate compliance against empirical pre-LLM scholarly baselines:

```bash
arkais audit draft.md
```

To integrate with automated CI/CD pipelines (e.g. GitHub Actions or pre-commit hooks), use `--json`:
```bash
arkais audit draft.md --json
```
Exit code is `0` when compliant and `1` on gate violations.

### Resolving Paper Authenticity & DOI Metadata
Lookup scholarly publication records via CrossRef and OpenAlex polite pools without setting up any API keys:

```bash
arkais verify-doi 10.1016/j.joule.2018.05.006
```

### Guarding Against Phantom Citations
Verify whether an author and paper title correspond to an authentic peer-reviewed publication:

```bash
arkais verify-citation --title "A Process for Capturing CO2 from the Atmosphere" --author "David Keith"
```

---

## 3. Python SDK Usage

### Basic Client Initialization
```python
from arkais import ArkaisClient

client = ArkaisClient()
```

### Auditing Prose
```python
scorecard = client.audit("""
The regeneration of potassium hydroxide solutions presents a substantial thermodynamic challenge.
While early models posited severe energetic penalties, empirical measurements indicate that mass
transfer rates depend predominantly on liquid-phase boundary dynamics.
""")

print("Score:", scorecard.overall_score)
print("Compliant:", scorecard.passed)
```

### Formatting Citations
```python
from arkais.models import ReferenceItem
from arkais.citation import CitationStyle, SyntacticRole

ref = client.resolve_doi("10.1016/j.joule.2018.05.006")

# In-Text Citation
apa = client.format_citation(ref, style=CitationStyle.APA)       # (Keith et al., 2018)
ieee = client.format_citation(ref, style=CitationStyle.IEEE, citation_number=1)  # [1]
nature = client.format_citation(ref, style=CitationStyle.NATURE, citation_number=1) # ¹

# Rhetorical Prose Weaving
narrative = client.weave_citation(
    ref,
    role=SyntacticRole.INTEGRAL_SUBJECT,
    claim="empirically demonstrated that structured contactor packing accelerates CO2 mass transfer.",
    style=CitationStyle.APA
)
print(narrative)
```

---

## 4. BYOK Security Configuration

Arkais operates under a zero-telemetry, client-side Bring Your Own Key (BYOK) paradigm. No API keys or queries are ever routed to NGT servers.

Keys are resolved in the following priority:
1. Explicit constructor argument (`ArkaisClient(api_keys={"OPENAI_API_KEY": "..."})`)
2. Environment variables (`export ANTHROPIC_API_KEY="sk-ant-..."`)
3. Project `.env` file (gitignored)
4. Local configuration file: `~/.config/arkais/credentials.json` (POSIX `0600` permissions enforced)
