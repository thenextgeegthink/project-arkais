"""Schema migration 0001 — the full Attestation Spine identity graph (THE-77 / P1-S1).

Twenty-six tables in dependency order. The ordering is not cosmetic: ``source`` must exist
before ``source_identifier`` can reference it, and so on down the chain. A migration that
creates tables out of order fails at apply time, not at review time.

Generated from ``docs/ways-of-work/plan/arkais-reference-manager/spec.md`` §4. Do not edit by
hand: change the spec, then regenerate.
"""


def up(conn) -> None:
    """Apply the schema. Takes a DB-API connection; issues no DDL of its own."""
    conn.executescript(SCHEMA_SQL)


SCHEMA_SQL = """
CREATE TABLE tenant (

    tenant_id     TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workspace (

    workspace_id      TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL REFERENCES tenant(tenant_id),
    citation_style    TEXT NOT NULL DEFAULT 'apa',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE source (

    source_id      TEXT PRIMARY KEY,    -- UUIDv4 or v7. Never ULID: its embedded
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE content_blob (

    blob_id      TEXT PRIMARY KEY,
    sha256       TEXT NOT NULL,
    byte_size    BIGINT,
    mime_type    TEXT,
    local_path   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE source_identifier (

    source_id       TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    scheme          TEXT NOT NULL,   -- doi|pmid|pmcid|arxiv|isbn|issn|handle
    value           TEXT NOT NULL,
    value_normalized TEXT NOT NULL,  -- lowercased, resolver-prefix-stripped
    is_primary      BOOLEAN NOT NULL DEFAULT false,
    verified_at     TIMESTAMPTZ,
    verification    TEXT NOT NULL DEFAULT 'not-evaluated',
    PRIMARY KEY (scheme, value_normalized)   -- REGISTRY-ASSERTED SCHEMES ONLY
);

CREATE TABLE provider_identifier (

    source_id       TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,   -- openalex|s2|core|biorxiv
    provider_key    TEXT NOT NULL,
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, provider_key)   -- no uniqueness constrains source_id
);

CREATE TABLE source_creator (

    source_id     TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    family        TEXT,
    given         TEXT,
    literal       TEXT,              -- corporate/institutional authors
    orcid         TEXT,
    PRIMARY KEY (source_id, seq)
);

CREATE TABLE source_version (

    version_id     TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    version_type   TEXT NOT NULL,    -- preprint|correction|retraction|expression_of_concern
    version_label  TEXT,
    doi            TEXT,
    url            TEXT,
    observed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE metadata_snapshot (

    snapshot_id    TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    provider       TEXT NOT NULL,   -- crossref|openalex|arxiv|epmc|s2|core|biorxiv|zotero|user
    provider_key   TEXT,            -- that provider's native identifier
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload        JSONB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    UNIQUE (source_id, provider, payload_sha256)
);

CREATE TABLE source_revision (

    source_id      TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    revision       INTEGER NOT NULL,
    built_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    builder        TEXT NOT NULL,      -- resolver version + policy id
    csl_json       JSONB NOT NULL,
    csl_digest     TEXT NOT NULL,
    title          TEXT NOT NULL,      -- denormalized for list views
    is_retracted   BOOLEAN NOT NULL DEFAULT false,
    is_current     BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (source_id, revision)
);

CREATE TABLE source_revision_field (

    source_id       TEXT NOT NULL,
    revision        INTEGER NOT NULL,
    field_path      TEXT NOT NULL,   -- RFC 6901 pointer into source_revision.csl_json
    field_class     TEXT NOT NULL,   -- identity_bearing | presentational
    chosen_snapshot TEXT REFERENCES metadata_snapshot(snapshot_id),
    chosen_provider TEXT,
    provider_state  TEXT NOT NULL,   -- present|absent|empty|unavailable|conflicting
    alternatives    JSONB NOT NULL DEFAULT '[]',  -- [{provider, value, snapshot_id}]
    conflict        TEXT,            -- NULL | material | normalized
    superseded_by   INTEGER,         -- set when a later revision changes this field
    PRIMARY KEY (source_id, revision, field_path),
    FOREIGN KEY (source_id, revision)
        REFERENCES source_revision (source_id, revision) ON DELETE CASCADE
);

CREATE TABLE source_alias (

    alias_id       TEXT PRIMARY KEY,
    from_source_id TEXT NOT NULL REFERENCES source(source_id) ON DELETE RESTRICT,
    to_source_id   TEXT NOT NULL REFERENCES source(source_id),
    workspace_id   TEXT NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
    basis          TEXT NOT NULL,      -- human_decision|candidate_resolved
    decided_by     TEXT NOT NULL,
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    reverted_at    TIMESTAMPTZ          -- un-merge: row stays, resolution stops applying
);

CREATE TABLE merge_signal (

    signal_id       TEXT PRIMARY KEY,
    left_source_id  TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    right_source_id TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    signal_kind     TEXT NOT NULL,   -- title_year|coauthor|openalex_s2_agreement
    score           REAL NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (left_source_id, right_source_id, signal_kind)
);

CREATE TABLE merge_candidate (

    candidate_id    TEXT PRIMARY KEY,
    left_source_id  TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    right_source_id TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    basis           TEXT NOT NULL,   -- title_year_fuzzy|coauthor_birthyear|shared_url
    score           REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'proposed',  -- proposed|approved|rejected
    resolved_by     TEXT,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (left_source_id, right_source_id),
    CHECK (left_source_id <> right_source_id)
);

CREATE TABLE source_acquisition (

    source_id     TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    blob_id       TEXT NOT NULL REFERENCES content_blob(blob_id),
    locator_url   TEXT,
    oa_status     TEXT NOT NULL DEFAULT 'unknown',  -- open|closed|bronze|unknown
    license       TEXT,
    rights_tier   TEXT,
    acquired_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, blob_id)
);

CREATE TABLE extraction (

    extraction_id  TEXT PRIMARY KEY,
    blob_id        TEXT NOT NULL REFERENCES content_blob(blob_id),
    page_count     INTEGER,
    extractor      TEXT NOT NULL,
    text_sha256    TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE page_map (

    extraction_id   TEXT NOT NULL REFERENCES extraction(extraction_id) ON DELETE CASCADE,
    page_number     INTEGER NOT NULL,
    section_label   TEXT,
    char_start      INTEGER NOT NULL,
    char_end        INTEGER NOT NULL,
    PRIMARY KEY (extraction_id, page_number)
);

CREATE TABLE evidence_span (

    span_id        TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES source(source_id),
    extraction_id  TEXT NOT NULL REFERENCES extraction(extraction_id),
    page_number    INTEGER NOT NULL,
    section_label  TEXT,
    char_start     INTEGER NOT NULL,
    char_end       INTEGER NOT NULL,
    text           TEXT NOT NULL,
    text_sha256    TEXT NOT NULL,
    UNIQUE (span_id, source_id)          -- target of citation_event's composite FK
);

CREATE TABLE library_entry (

    workspace_id   TEXT NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
    source_id      TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    cite_key       TEXT,
    collection     TEXT,
    added_by       TEXT NOT NULL,       -- 'user' | 'agent:<agent_id>'
    approval       TEXT NOT NULL,       -- 'pending' | 'approved' | 'rejected'
    added_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source_id)
);

CREATE TABLE library_field_override (

    workspace_id  TEXT NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
    source_id     TEXT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
    field_path    TEXT NOT NULL,   -- RFC 6901 JSON pointer into revision.csl_json
    value         JSONB NOT NULL,
    reason        TEXT,
    set_by        TEXT NOT NULL,   -- 'user' | 'agent:<agent_id>'
    set_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source_id, field_path)
);

CREATE TABLE document (

    document_id   TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
    label         TEXT NOT NULL,
    locale        TEXT NOT NULL DEFAULT 'en-US',
    style_id      TEXT NOT NULL DEFAULT 'apa',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE citation_event (

    event_id       TEXT PRIMARY KEY,
    document_id    TEXT NOT NULL REFERENCES document(document_id) ON DELETE CASCADE,
    seq            INTEGER NOT NULL,  -- document order; drives IEEE/Vancouver numbering
    cluster_id     TEXT NOT NULL,     -- CSL's unit is the CLUSTER: several cites sharing
                                      -- one parenthetical. Without this, "(A, 2019)(B, 2020)"
                                      -- and "(A, 2019; B, 2020)" are indistinguishable.
    block_index    INTEGER NOT NULL,
    source_id      TEXT NOT NULL REFERENCES source(source_id),
    -- PINNED, and a COMPOSITE FK: is_current is a global flag that flips, so a
    -- render is reproducible only if it records the revision it saw.
    revision_id    INTEGER NOT NULL,
    -- span must belong to THIS source: an event citing X with a span from Y is
    -- a silent-wrong-evidence path, the exact failure this design prevents.
    span_id        TEXT,
    locator        TEXT,               -- 'p. 42', '§3.1'
    locator_label  TEXT,               -- 'page'|'section'|'paragraph'|'chapter'
    prefix         TEXT,               -- 'see '
    suffix         TEXT,               -- ', emphasis added'
    note_id        TEXT,               -- which citations SHARE a footnote. The NUMBER is
                                      -- positional and derived at render; storing it would
                                      -- contradict invariant 14 and go stale on first edit.
    author_only    BOOLEAN NOT NULL DEFAULT false,  -- 'Fama (1970) demonstrated',
    UNIQUE (document_id, seq),
    FOREIGN KEY (source_id, revision_id)
        REFERENCES source_revision (source_id, revision),
    FOREIGN KEY (span_id, source_id)
        REFERENCES evidence_span (span_id, source_id)
);

CREATE TABLE claim_source_link (

    link_id      TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
    source_id    TEXT NOT NULL REFERENCES source(source_id),
    span_id      TEXT REFERENCES evidence_span(span_id),
    claim_text   TEXT NOT NULL,
    support      TEXT NOT NULL,   -- support|contrast|method|definition|background
    verdict      TEXT NOT NULL,   -- verified|partial|unresolved|contradicted|not-evaluated
    method       TEXT NOT NULL,   -- deterministic | model-evaluated
    observed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE verification_run (

    run_id        TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenant(tenant_id),
    scope         TEXT NOT NULL,   -- source | workspace | manuscript
    -- The revision set this run verified against. Same rationale as
    -- citation_event.revision_id: a verdict is only meaningful against the
    -- exact metadata it inspected.
    pinned_revisions JSONB NOT NULL,   -- [{source_id, revision_id}, ...]
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    verdict       TEXT NOT NULL    -- pass | revise | block | not-evaluated
);

CREATE TABLE verification_finding (

    finding_id    TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES verification_run(run_id) ON DELETE CASCADE,
    status        TEXT NOT NULL,
    severity      TEXT NOT NULL,
    location      TEXT,
    rule_id       TEXT NOT NULL,
    module_id     TEXT,
    check_type    TEXT NOT NULL,
    evidence      JSONB,
    minimum_repair TEXT
);

CREATE TABLE credential (

    credential_id  TEXT PRIMARY KEY,
    tenant_id      TEXT REFERENCES tenant(tenant_id),  -- NULL = deployment scope
    scope_class    TEXT NOT NULL,   -- platform_scholarly | tenant_byok_model | user_grant
    provider       TEXT NOT NULL,
    secret_ref     TEXT NOT NULL,   -- pointer into the vault, never the secret
    egress_allowlist TEXT[] NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

"""