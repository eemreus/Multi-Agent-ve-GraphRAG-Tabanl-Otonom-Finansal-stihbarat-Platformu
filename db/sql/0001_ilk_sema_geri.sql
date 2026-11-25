DROP TRIGGER IF EXISTS trg_citation_source_retrieved ON citations;
DROP FUNCTION IF EXISTS citation_source_retrieved();
DROP TABLE IF EXISTS agent_logs, circular_group_members, circular_groups, contradictions, citations,
    claims, reports, extraction_runs, retrievals, sources, publishers, sub_queries,
    research_sessions, user_settings, api_keys, users CASCADE;
