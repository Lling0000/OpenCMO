"""Additive schema, also installed on existing databases."""
SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_documents (
 id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
 scope TEXT NOT NULL DEFAULT 'project' CHECK(scope IN ('project','account')),
 external_use INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL, kind TEXT NOT NULL,
 source_key TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]',
 generated INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0,
 active_version_id TEXT, status TEXT NOT NULL DEFAULT 'queued', error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now')),
 UNIQUE(account_id, source_key)
);
CREATE INDEX IF NOT EXISTS rag_document_scope ON rag_documents(account_id, project_id, scope, deleted);
CREATE TABLE IF NOT EXISTS rag_versions (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
 number INTEGER NOT NULL, content_hash TEXT NOT NULL, original_path TEXT NOT NULL,
 mime TEXT NOT NULL, text TEXT NOT NULL DEFAULT '', blocks_json TEXT NOT NULL DEFAULT '[]',
 parser_version TEXT NOT NULL DEFAULT '1', created_at TEXT NOT NULL DEFAULT (datetime('now')),
 UNIQUE(document_id, number)
);
CREATE TABLE IF NOT EXISTS rag_profiles (
 id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 fingerprint TEXT NOT NULL, dimensions INTEGER NOT NULL, collection_name TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'building', created_at TEXT NOT NULL DEFAULT (datetime('now')),
 UNIQUE(account_id, fingerprint)
);
CREATE TABLE IF NOT EXISTS rag_account_state (
 account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
 active_profile_id TEXT REFERENCES rag_profiles(id), pending_profile_id TEXT REFERENCES rag_profiles(id)
);
CREATE TABLE IF NOT EXISTS rag_generations (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
 version_id TEXT NOT NULL REFERENCES rag_versions(id) ON DELETE CASCADE,
 profile_id TEXT NOT NULL REFERENCES rag_profiles(id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'building', config_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 UNIQUE(version_id, profile_id)
);
CREATE TABLE IF NOT EXISTS rag_chunks (
 id TEXT PRIMARY KEY, generation_id TEXT NOT NULL REFERENCES rag_generations(id) ON DELETE CASCADE,
 parent_id TEXT, level TEXT NOT NULL, start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL,
 text TEXT NOT NULL, heading TEXT NOT NULL DEFAULT '', page INTEGER, prefix TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS rag_chunk_generation ON rag_chunks(generation_id, level);
CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(chunk_id UNINDEXED, title, body, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS rag_retrievals (
 id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 project_id INTEGER, purpose TEXT NOT NULL, query_hash TEXT NOT NULL, result_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS rag_citations (
 id TEXT PRIMARY KEY, retrieval_id TEXT NOT NULL REFERENCES rag_retrievals(id) ON DELETE CASCADE,
 document_id TEXT NOT NULL, version_id TEXT NOT NULL, chunk_id TEXT NOT NULL,
 data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rag_message_evidence (
 session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
 message_key TEXT NOT NULL, retrieval_id TEXT NOT NULL REFERENCES rag_retrievals(id) ON DELETE CASCADE,
 PRIMARY KEY(session_id, message_key)
);
CREATE TABLE IF NOT EXISTS rag_task_owners (
 task_id TEXT PRIMARY KEY REFERENCES background_tasks(task_id) ON DELETE CASCADE,
 account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS rag_index_leases (
 account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
 task_id TEXT NOT NULL, expires_at REAL NOT NULL
);
"""
