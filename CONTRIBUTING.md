# Contributing to Project Arkais

Thank you for your interest in contributing to **Project Arkais**!

Project Arkais follows a **Proprietary Core with Community Extensions** architecture (analogous to the Figma or Unreal Engine ecosystem model). This document outlines where and how the community can contribute.

---

## 1. Governance & Boundary Architecture

Project Arkais is maintained and governed by **The Next Geek Think (NGT)**.

| Component | License / Governance | Open to Community PRs? |
| :--- | :--- | :--- |
| **Arkais Signature Core** | Proprietary (NGT Internal) | No (In-house R&D) |
| **Arkais Studio UI / IDE** | Proprietary (Astryx Core) | No (Internal design system) |
| **Scientific Figure Templates** | MIT / Community | **Yes** (Charts, Vega-Lite specs) |
| **Quarto Filters & Extensions** | MIT / Community | **Yes** (Lua filters, format converters) |
| **CSL Citation Profiles** | MIT / Community | **Yes** (Journal citation styles) |
| **Public Benchmarks & Datasets** | CC-BY-4.0 / Open Data | **Yes** (Evaluation metrics & test scripts) |
| **Thin Client CLI & SDK** | Evaluation License | **Yes** (Bug fixes, CLI flags, DX improvements) |

---

## 2. Areas for Community Contribution

### A. Scientific Figure & Chart Templates
We welcome publication-grade chart templates (Vega-Lite, Matplotlib, Seaborn, TikZ):
- Must be clean, accessible, and high-DPI publication ready.
- Must include sample JSON data and render scripts.
- Location: `examples/figures/`

### B. Quarto & Document Formatting Extensions
- Custom Quarto filters (`_extensions/`) for journal-specific LaTeX/PDF rendering.
- Cross-reference styling and typst/pandoc post-processors.

### C. Public Benchmark Scenarios
- Stylometric robustness tests across disciplines (physics, economics, computational biology).
- Reproducible benchmark notebooks under `benchmarks/`.

---

## 3. Contribution Guidelines

1. **Clean Code & Commits**: Use semantic commits (`feat:`, `fix:`, `docs:`, `test:`).
2. **Security & Provenance**:
   - **ZERO Copyrighted Full Texts**: Never upload proprietary journal PDFs or unfree corpus books.
   - **ZERO Secrets**: Never commit `.env` files, API keys, or private tokens.
3. **Tests**: All Python PRs must pass `pytest tests/` and `ruff check .`.
4. **License Agreement**: By submitting contributions, you agree that your figure templates, benchmark scripts, and documentation extensions are licensed under the MIT License and may be distributed alongside Project Arkais.

For inquiries regarding commercial licensing, custom enterprise deployments, or research partnerships, contact `engineering@geegthink.com`.
