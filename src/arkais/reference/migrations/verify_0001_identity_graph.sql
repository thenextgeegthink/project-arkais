-- Schema verification for m0001_identity_graph.sql (THE-77 / P1-S1).
--
-- Run against a real PostgreSQL instance:
--   psql -U postgres -d arkais -v ON_ERROR_STOP=1 -f verify_0001_identity_graph.sql
--
-- The positive block asserts the THE-77 acceptance criterion — an ISBN-only book and a
-- user-uploaded PDF with no identifier both persist as `source`. The negative block asserts the
-- invariants that must FAIL, because an invariant that cannot fail is not an invariant.
--
-- Verified against PostgreSQL 16.15.

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------------
-- Structural: 26 tables, and the shape invariants from spec §4.1
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    n int;
BEGIN
    SELECT count(*) INTO n FROM information_schema.tables WHERE table_schema = 'public';
    IF n <> 26 THEN
        RAISE EXCEPTION 'expected 26 tables, found %', n;
    END IF;

    -- inv 1: `source` is global and carries no tenant_id.
    SELECT count(*) INTO n FROM information_schema.columns
     WHERE table_name = 'source' AND column_name = 'tenant_id';
    IF n <> 0 THEN
        RAISE EXCEPTION 'inv 1 violated: source must not carry tenant_id';
    END IF;

    -- inv 16: no free-text citation field on citation_event, anywhere.
    SELECT count(*) INTO n FROM information_schema.columns
     WHERE table_name = 'citation_event'
       AND column_name IN ('citation_text','rendered','formatted','citation_string');
    IF n <> 0 THEN
        RAISE EXCEPTION 'inv 16 violated: free-text citation field present';
    END IF;

    -- inv 13: cluster_id is the ordering unit of citation_event.
    SELECT count(*) INTO n FROM information_schema.columns
     WHERE table_name = 'citation_event' AND column_name = 'cluster_id';
    IF n <> 1 THEN
        RAISE EXCEPTION 'inv 13 violated: citation_event has no cluster_id';
    END IF;

    RAISE NOTICE 'structural invariants OK';
END $$;

-- ---------------------------------------------------------------------------
-- Fixtures
-- ---------------------------------------------------------------------------
INSERT INTO tenant (tenant_id, display_name) VALUES ('t1','Test Org');
INSERT INTO workspace (workspace_id, tenant_id, citation_style) VALUES ('w1','t1','apa');
INSERT INTO content_blob (blob_id, sha256, byte_size)
  VALUES ('b1', repeat('a',64), 1024);

-- Acceptance #1: ISBN-only book, no DOI anywhere.
INSERT INTO source (source_id) VALUES ('s-isbn-1');
INSERT INTO source_identifier (source_id, scheme, value, value_normalized)
  VALUES ('s-isbn-1','isbn','978-0-262-04452-8','9780262044528');
INSERT INTO source_revision (source_id, revision, builder, csl_json, csl_digest, title)
  VALUES ('s-isbn-1',1,'test','{"title":"A Mathematical Theory of Communication"}','d1',
          'A Mathematical Theory of Communication');

-- Acceptance #2: user-uploaded PDF carrying no identifier at all.
INSERT INTO source (source_id) VALUES ('s-pdf-1');
INSERT INTO source_acquisition (source_id, blob_id, oa_status, rights_tier)
  VALUES ('s-pdf-1','b1','closed','unknown');
INSERT INTO source_revision (source_id, revision, builder, csl_json, csl_digest, title)
  VALUES ('s-pdf-1',1,'test','{"title":"Scanned seminar notes"}','d2','Scanned seminar notes');

-- The ordinary DOI path.
INSERT INTO source (source_id) VALUES ('s-doi-1');
INSERT INTO source_identifier (source_id, scheme, value, value_normalized, is_primary)
  VALUES ('s-doi-1','doi','10.1038/nature12373','10.1038/nature12373', true);
INSERT INTO source_revision (source_id, revision, builder, csl_json, csl_digest, title)
  VALUES ('s-doi-1',1,'test','{"title":"Nanometre-scale thermometry"}','d3',
          'Nanometre-scale thermometry');

-- A second tenant converges on the same source through the global identifier key (inv 1).
INSERT INTO tenant (tenant_id, display_name) VALUES ('t2','Second Org');
INSERT INTO workspace (workspace_id, tenant_id, citation_style) VALUES ('w2','t2','mla');
INSERT INTO library_entry (workspace_id, source_id, cite_key, added_by, approval)
  SELECT 'w2', i.source_id, 'kim2024deep', 'human', 'approved'
    FROM source_identifier i
   WHERE i.value_normalized = '10.1038/nature12373' AND i.is_primary;

INSERT INTO document (document_id, workspace_id, label) VALUES ('doc1','w1','Test Draft');

-- inv 20: a bound-from-text event pins the revision but carries no span.
INSERT INTO citation_event (event_id, document_id, seq, cluster_id, block_index,
                            source_id, revision_id)
  VALUES ('ev1','doc1',1,'c1',0,'s-doi-1',1);

-- ---------------------------------------------------------------------------
-- Assertions
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    n int;
BEGIN
    SELECT count(*) INTO n FROM source;                                   IF n <> 3 THEN
        RAISE EXCEPTION 'expected 3 sources, found %', n; END IF;

    -- THE-77 acceptance: identifier-free and identifier-only-but-no-DOI both persist.
    SELECT count(*) INTO n FROM source s
      WHERE NOT EXISTS (SELECT 1 FROM source_identifier i WHERE i.source_id = s.source_id);
    IF n <> 1 THEN
        RAISE EXCEPTION 'expected 1 identifier-free source (the user PDF), found %', n;
    END IF;

    SELECT count(*) INTO n FROM source_identifier WHERE scheme = 'isbn';
    IF n <> 1 THEN
        RAISE EXCEPTION 'expected 1 ISBN identifier, found %', n;
    END IF;

    -- inv 1: two tenants, one source_id.
    SELECT count(DISTINCT workspace_id) INTO n FROM library_entry WHERE source_id = 's-doi-1';
    IF n <> 1 THEN
        RAISE EXCEPTION 'inv 1: cross-tenant convergence failed';
    END IF;

    -- inv 20: the bound event has no span.
    SELECT count(*) INTO n FROM citation_event WHERE span_id IS NOT NULL;
    IF n <> 0 THEN
        RAISE EXCEPTION 'inv 20 violated: a bound-from-text event must carry span_id NULL';
    END IF;

    RAISE NOTICE 'positive assertions OK';
END $$;

ROLLBACK;

-- ---------------------------------------------------------------------------
-- Negative assertions. Each of these MUST fail; run individually.
-- ---------------------------------------------------------------------------
-- \set ON_ERROR_STOP on
-- 1. inv 1 — a duplicate normalized identifier cannot be claimed by a second source.
--    INSERT INTO source (source_id) VALUES ('s-dup');
--    INSERT INTO source_identifier (source_id, scheme, value, value_normalized)
--      VALUES ('s-dup','doi','10.1038/NATURE12373','10.1038/nature12373');
--    -- expected: duplicate key value violates unique constraint "source_identifier_pkey"
--
-- 2. inv 3 — a citation_event cannot pin a revision that does not exist.
--    INSERT INTO citation_event (event_id, document_id, seq, cluster_id, block_index,
--                                source_id, revision_id)
--      VALUES ('ev2','doc1',1,'c1',0,'s-doi-1',999);
--    -- expected: violates foreign key constraint
--      "citation_event_source_id_revision_id_fkey"
--
-- 3. inv 16 — there is no column in which to store pre-formatted citation text.
--    INSERT INTO citation_event (..., citation_text) VALUES (...);
--    -- expected: column "citation_text" does not exist