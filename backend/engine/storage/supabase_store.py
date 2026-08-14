"""
Supabase PostgreSQL & SQLite Hybrid Persistent Storage Engine for CodeLoom.
Supports live cloud persistence on Supabase with automatic local SQLite WAL fallback.
Full interface parity with SQLiteStore.
"""
import os
import json
import logging
import contextlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from engine.models import Cluster, Fix, SimulationResult

logger = logging.getLogger("codeloom.storage.supabase")

# Database URL with fallback
DEFAULT_SUPABASE_URL = "postgresql://postgres:cypher12345%40roman@db.kmksohqydbnbcwbneoiq.supabase.co:5432/postgres"

class SupabaseStore:
    """
    Production-grade database store with Supabase PostgreSQL primary and SQLite fallback.
    Provides complete interface compatibility with SQLiteStore.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL") or DEFAULT_SUPABASE_URL
        self._is_postgres_active = False
        self._init_sqlite_fallback()
        self._init_postgres()

    def _init_sqlite_fallback(self):
        import sqlite3
        engine_dir = Path(__file__).resolve().parent.parent
        self.sqlite_path = str(engine_dir / "codeloom_engine.db")
        with contextlib.closing(sqlite3.connect(self.sqlite_path)) as conn:
            with conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS scans (
                        scan_id TEXT PRIMARY KEY,
                        url TEXT,
                        total_findings INTEGER,
                        deduplicated_findings INTEGER,
                        token_usage TEXT,
                        scores TEXT,
                        screenshot_ref TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS clusters (
                        cluster_id TEXT PRIMARY KEY,
                        scan_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS fixes (
                        fix_id TEXT PRIMARY KEY,
                        cluster_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS simulations (
                        simulation_id TEXT PRIMARY KEY,
                        fix_id TEXT NOT NULL,
                        data TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        repository_url TEXT NOT NULL,
                        default_branch TEXT DEFAULT 'main',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS remediations (
                        remediation_id TEXT PRIMARY KEY,
                        project_id TEXT,
                        scan_id TEXT,
                        rule_id TEXT NOT NULL,
                        target_file TEXT,
                        final_status TEXT NOT NULL,
                        pull_request_url TEXT,
                        pull_request_number INTEGER,
                        details_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

    def _init_postgres(self):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.db_url, connect_timeout=5)
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS scans (
                            scan_id VARCHAR(64) PRIMARY KEY,
                            url TEXT,
                            total_findings INT DEFAULT 0,
                            deduplicated_findings INT DEFAULT 0,
                            token_usage JSONB DEFAULT '{}'::jsonb,
                            scores JSONB DEFAULT '{}'::jsonb,
                            screenshot_ref TEXT,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS clusters (
                            cluster_id VARCHAR(128) PRIMARY KEY,
                            scan_id VARCHAR(64) NOT NULL,
                            data JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS fixes (
                            fix_id VARCHAR(128) PRIMARY KEY,
                            cluster_id VARCHAR(128) NOT NULL,
                            data JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS simulations (
                            simulation_id VARCHAR(128) PRIMARY KEY,
                            fix_id VARCHAR(128) NOT NULL,
                            data JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS projects (
                            project_id VARCHAR(64) PRIMARY KEY,
                            name TEXT NOT NULL,
                            repository_url TEXT NOT NULL,
                            default_branch VARCHAR(64) DEFAULT 'main',
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS remediations (
                            remediation_id VARCHAR(128) PRIMARY KEY,
                            project_id VARCHAR(64),
                            scan_id VARCHAR(64),
                            rule_id VARCHAR(64) NOT NULL,
                            target_file TEXT,
                            final_status VARCHAR(32) NOT NULL,
                            pull_request_url TEXT,
                            pull_request_number INT,
                            details_json JSONB DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
            conn.close()
            self._is_postgres_active = True
            logger.info("Connected to Supabase PostgreSQL database successfully.")
        except Exception as e:
            logger.warning(f"PostgreSQL connection to Supabase failed ({e}). Operating in SQLite local mode.")
            self._is_postgres_active = False

    def _get_pg_conn(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor, connect_timeout=5)

    def _get_sqlite_conn(self):
        import sqlite3
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Scans ---
    def save_scan(self, scan_id: str, total_findings: int, deduplicated_findings: int,
                  token_usage: Dict[str, Any], url: Optional[str] = None,
                  scores: Optional[Dict[str, Any]] = None, screenshot_ref: Optional[str] = None):
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO scans (scan_id, url, total_findings, deduplicated_findings, token_usage, scores, screenshot_ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (scan_id, url, total_findings, deduplicated_findings, json.dumps(token_usage), json.dumps(scores or {}), screenshot_ref)
                )

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO scans (scan_id, url, total_findings, deduplicated_findings, token_usage, scores, screenshot_ref)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (scan_id) DO UPDATE SET
                                    url = EXCLUDED.url,
                                    total_findings = EXCLUDED.total_findings,
                                    deduplicated_findings = EXCLUDED.deduplicated_findings,
                                    token_usage = EXCLUDED.token_usage,
                                    scores = EXCLUDED.scores,
                                    screenshot_ref = EXCLUDED.screenshot_ref
                                """,
                                (scan_id, url, total_findings, deduplicated_findings, json.dumps(token_usage), json.dumps(scores or {}), screenshot_ref)
                            )
            except Exception as e:
                logger.warning(f"Supabase save_scan failed ({e}); recorded in SQLite fallback.")

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT * FROM scans WHERE scan_id = %s", (scan_id,))
                        row = cur.fetchone()
                        if row:
                            return {
                                "scan_id": row["scan_id"],
                                "url": row["url"],
                                "total_findings": row["total_findings"],
                                "deduplicated_findings": row["deduplicated_findings"],
                                "token_usage": row["token_usage"] if isinstance(row["token_usage"], dict) else json.loads(row["token_usage"] or "{}"),
                                "scores": row["scores"] if isinstance(row["scores"], dict) else json.loads(row["scores"] or "{}"),
                                "screenshot_ref": row["screenshot_ref"],
                                "created_at": str(row["created_at"]),
                            }
            except Exception as e:
                logger.warning(f"Supabase get_scan error: {e}")

        with contextlib.closing(self._get_sqlite_conn()) as conn:
            row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
            if not row:
                return None
            return {
                "scan_id": row["scan_id"],
                "url": row["url"],
                "total_findings": row["total_findings"],
                "deduplicated_findings": row["deduplicated_findings"],
                "token_usage": json.loads(row["token_usage"]) if row["token_usage"] else {},
                "scores": json.loads(row["scores"]) if row["scores"] else {},
                "screenshot_ref": row["screenshot_ref"],
                "created_at": str(row["created_at"]),
            }

    def get_all_scans(self, limit: int = 50, offset: int = 0, search: Optional[str] = None) -> Dict[str, Any]:
        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn.cursor() as cur:
                        if search:
                            q = f"%{search}%"
                            cur.execute("SELECT COUNT(*) as count FROM scans WHERE scan_id ILIKE %s OR url ILIKE %s", (q, q))
                            total = cur.fetchone()["count"]
                            cur.execute(
                                """
                                SELECT s.*, COUNT(c.cluster_id) as clusters_count
                                FROM scans s
                                LEFT JOIN clusters c ON s.scan_id = c.scan_id
                                WHERE s.scan_id ILIKE %s OR s.url ILIKE %s
                                GROUP BY s.scan_id
                                ORDER BY s.created_at DESC
                                LIMIT %s OFFSET %s
                                """,
                                (q, q, limit, offset)
                            )
                        else:
                            cur.execute("SELECT COUNT(*) as count FROM scans")
                            total = cur.fetchone()["count"]
                            cur.execute(
                                """
                                SELECT s.*, COUNT(c.cluster_id) as clusters_count
                                FROM scans s
                                LEFT JOIN clusters c ON s.scan_id = c.scan_id
                                GROUP BY s.scan_id
                                ORDER BY s.created_at DESC
                                LIMIT %s OFFSET %s
                                """,
                                (limit, offset)
                            )
                        rows = cur.fetchall()
                        items = []
                        for r in rows:
                            items.append({
                                "scan_id": r["scan_id"],
                                "url": r["url"],
                                "total_findings": r["total_findings"],
                                "deduplicated_findings": r["deduplicated_findings"],
                                "clusters_count": r["clusters_count"],
                                "token_usage": r["token_usage"] if isinstance(r["token_usage"], dict) else json.loads(r["token_usage"] or "{}"),
                                "scores": r["scores"] if isinstance(r["scores"], dict) else json.loads(r["scores"] or "{}"),
                                "screenshot_ref": r["screenshot_ref"],
                                "created_at": str(r["created_at"]),
                            })
                        return {"total": total, "limit": limit, "offset": offset, "items": items}
            except Exception as e:
                logger.warning(f"Supabase get_all_scans error: {e}")

        with contextlib.closing(self._get_sqlite_conn()) as conn:
            if search:
                query_filter = "%" + search + "%"
                total = conn.execute("SELECT COUNT(*) as count FROM scans WHERE scan_id LIKE ? OR url LIKE ?", (query_filter, query_filter)).fetchone()["count"]
                rows = conn.execute(
                    """
                    SELECT s.*, COUNT(c.cluster_id) as clusters_count
                    FROM scans s
                    LEFT JOIN clusters c ON s.scan_id = c.scan_id
                    WHERE s.scan_id LIKE ? OR s.url LIKE ?
                    GROUP BY s.scan_id
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (query_filter, query_filter, limit, offset)
                ).fetchall()
            else:
                total = conn.execute("SELECT COUNT(*) as count FROM scans").fetchone()["count"]
                rows = conn.execute(
                    """
                    SELECT s.*, COUNT(c.cluster_id) as clusters_count
                    FROM scans s
                    LEFT JOIN clusters c ON s.scan_id = c.scan_id
                    GROUP BY s.scan_id
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                ).fetchall()

            items = []
            for row in rows:
                items.append({
                    "scan_id": row["scan_id"],
                    "url": row["url"],
                    "total_findings": row["total_findings"],
                    "deduplicated_findings": row["deduplicated_findings"],
                    "clusters_count": row["clusters_count"],
                    "token_usage": json.loads(row["token_usage"]) if row["token_usage"] else {},
                    "scores": json.loads(row["scores"]) if row["scores"] else {},
                    "screenshot_ref": row["screenshot_ref"],
                    "created_at": str(row["created_at"]),
                })
            return {"total": total, "limit": limit, "offset": offset, "items": items}

    def delete_scan(self, scan_id: str) -> bool:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                cluster_rows = conn.execute("SELECT cluster_id FROM clusters WHERE scan_id = ?", (scan_id,)).fetchall()
                cluster_ids = [r["cluster_id"] for r in cluster_rows]
                if cluster_ids:
                    placeholders = ",".join(["?"] * len(cluster_ids))
                    fix_rows = conn.execute(f"SELECT fix_id FROM fixes WHERE cluster_id IN ({placeholders})", cluster_ids).fetchall()
                    fix_ids = [r["fix_id"] for r in fix_rows]
                    if fix_ids:
                        fix_placeholders = ",".join(["?"] * len(fix_ids))
                        conn.execute(f"DELETE FROM simulations WHERE fix_id IN ({fix_placeholders})", fix_ids)
                    conn.execute(f"DELETE FROM fixes WHERE cluster_id IN ({placeholders})", cluster_ids)
                    conn.execute("DELETE FROM clusters WHERE scan_id = ?", (scan_id,))
                cur = conn.execute("DELETE FROM scans WHERE scan_id = ?", (scan_id,))
                deleted = cur.rowcount > 0

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM scans WHERE scan_id = %s", (scan_id,))
            except Exception as e:
                logger.warning(f"Supabase delete_scan error: {e}")

        return deleted

    def get_scan_bundle(self, scan_id: str) -> Optional[Dict[str, Any]]:
        scan_meta = self.get_scan(scan_id)
        if not scan_meta:
            return None
        clusters = self.get_clusters_for_scan(scan_id)
        fixes = self.get_fixes_for_scan(scan_id)
        return {
            "meta": scan_meta,
            "clusters": clusters,
            "fixes": fixes,
        }

    def save_scan_result(self, scan_id: str, result, url: str, screenshot_ref: Optional[str] = None):
        """Persist one complete result set using scan-scoped IDs to prevent overwrites."""
        self.save_scan(scan_id, result.total_findings, result.deduplicated_findings,
                       result.token_usage, url=url, scores=result.scores, screenshot_ref=screenshot_ref)
        cluster_ids = {}
        clusters = []
        for cluster in result.clusters:
            persisted = cluster.model_copy(update={"cluster_id": f"{scan_id}__{cluster.cluster_id}"})
            cluster_ids[cluster.cluster_id] = persisted.cluster_id
            self.save_cluster(scan_id, persisted)
            clusters.append(persisted)
        fixes = []
        for fix in result.fixes:
            persisted = fix.model_copy(update={
                "fix_id": f"{scan_id}__{fix.fix_id}",
                "cluster_id": cluster_ids.get(fix.cluster_id, fix.cluster_id),
            })
            self.save_fix(persisted)
            fixes.append(persisted)
        return clusters, fixes

    # --- Clusters ---
    def save_cluster(self, scan_id: str, cluster: Cluster):
        data_json = cluster.model_dump_json() if hasattr(cluster, "model_dump_json") else json.dumps(cluster)
        c_id = getattr(cluster, "cluster_id", str(cluster))
        
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO clusters (cluster_id, scan_id, data) VALUES (?, ?, ?)", (c_id, scan_id, data_json))

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO clusters (cluster_id, scan_id, data) VALUES (%s, %s, %s) ON CONFLICT (cluster_id) DO UPDATE SET data = EXCLUDED.data",
                                (c_id, scan_id, data_json)
                            )
            except Exception as e:
                logger.warning(f"Supabase save_cluster error: {e}")

    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            row = conn.execute("SELECT data FROM clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
            if not row:
                return None
            return Cluster.model_validate_json(row["data"])

    def get_clusters_for_scan(self, scan_id: str) -> List[Cluster]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            rows = conn.execute("SELECT data FROM clusters WHERE scan_id = ?", (scan_id,)).fetchall()
            return [Cluster.model_validate_json(row["data"]) for row in rows]

    # --- Fixes ---
    def save_fix(self, fix: Fix):
        data_json = fix.model_dump_json() if hasattr(fix, "model_dump_json") else json.dumps(fix)
        f_id = getattr(fix, "fix_id", str(fix))
        c_id = getattr(fix, "cluster_id", "unknown")

        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO fixes (fix_id, cluster_id, data) VALUES (?, ?, ?)", (f_id, c_id, data_json))

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO fixes (fix_id, cluster_id, data) VALUES (%s, %s, %s) ON CONFLICT (fix_id) DO UPDATE SET data = EXCLUDED.data",
                                (f_id, c_id, data_json)
                            )
            except Exception as e:
                logger.warning(f"Supabase save_fix error: {e}")

    def get_fix(self, fix_id: str) -> Optional[Fix]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            row = conn.execute("SELECT data FROM fixes WHERE fix_id = ?", (fix_id,)).fetchone()
            if not row:
                return None
            return Fix.model_validate_json(row["data"])

    def get_fixes_for_scan(self, scan_id: str) -> List[Fix]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            rows = conn.execute('''
                SELECT f.data FROM fixes f
                JOIN clusters c ON f.cluster_id = c.cluster_id
                WHERE c.scan_id = ?
            ''', (scan_id,)).fetchall()
            return [Fix.model_validate_json(row["data"]) for row in rows]

    # --- Simulations ---
    def save_simulation(self, simulation: SimulationResult):
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO simulations (simulation_id, fix_id, data) VALUES (?, ?, ?)",
                    (simulation.simulation_id, simulation.fix_id, simulation.model_dump_json())
                )

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO simulations (simulation_id, fix_id, data) VALUES (%s, %s, %s) ON CONFLICT (simulation_id) DO UPDATE SET data = EXCLUDED.data",
                                (simulation.simulation_id, simulation.fix_id, simulation.model_dump_json())
                            )
            except Exception as e:
                logger.warning(f"Supabase save_simulation error: {e}")

    def get_simulation_for_fix(self, fix_id: str) -> Optional[SimulationResult]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            row = conn.execute("SELECT data FROM simulations WHERE fix_id = ?", (fix_id,)).fetchone()
            if not row:
                return None
            return SimulationResult.model_validate_json(row["data"])

    # --- Projects ---
    def save_project(self, project_id: str, name: str, repository_url: str, default_branch: str = "main") -> Dict[str, Any]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO projects (project_id, name, repository_url, default_branch, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (project_id, name, repository_url, default_branch)
                )

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO projects (project_id, name, repository_url, default_branch, updated_at)
                                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                                ON CONFLICT (project_id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    repository_url = EXCLUDED.repository_url,
                                    default_branch = EXCLUDED.default_branch,
                                    updated_at = CURRENT_TIMESTAMP
                                """,
                                (project_id, name, repository_url, default_branch)
                            )
            except Exception as e:
                logger.warning(f"Supabase save_project error: {e}")

        return self.get_project(project_id) or {}

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def get_all_projects(self) -> List[Dict[str, Any]]:
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            rows = conn.execute("""
                SELECT p.*, COUNT(s.scan_id) as total_scans
                FROM projects p
                LEFT JOIN scans s ON p.repository_url = s.url
                GROUP BY p.project_id
                ORDER BY p.updated_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    # --- Remediations ---
    def save_remediation(self, remediation_id: str, rule_id: str, final_status: str,
                         project_id: Optional[str] = None, scan_id: Optional[str] = None,
                         target_file: Optional[str] = None, pull_request_url: Optional[str] = None,
                         pull_request_number: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        details_json = json.dumps(details or {})
        with contextlib.closing(self._get_sqlite_conn()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO remediations 
                    (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, details_json) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, details_json)
                )

        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO remediations (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, details_json)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (remediation_id) DO UPDATE SET
                                    final_status = EXCLUDED.final_status,
                                    target_file = EXCLUDED.target_file,
                                    pull_request_url = EXCLUDED.pull_request_url,
                                    pull_request_number = EXCLUDED.pull_request_number,
                                    details_json = EXCLUDED.details_json
                                """,
                                (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, details_json)
                            )
            except Exception as e:
                logger.warning(f"Supabase save_remediation error: {e}")

    def get_all_remediations(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self._is_postgres_active:
            try:
                with contextlib.closing(self._get_pg_conn()) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT * FROM remediations ORDER BY created_at DESC LIMIT %s", (limit,))
                        rows = cur.fetchall()
                        items = []
                        for r in rows:
                            item = dict(r)
                            item["details"] = item.get("details_json") if isinstance(item.get("details_json"), dict) else json.loads(item.get("details_json") or "{}")
                            item["created_at"] = str(item.get("created_at"))
                            items.append(item)
                        return items
            except Exception as e:
                logger.warning(f"Supabase get_all_remediations error: {e}")

        with contextlib.closing(self._get_sqlite_conn()) as conn:
            rows = conn.execute("SELECT * FROM remediations ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            items = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item.get("details_json") or "{}")
                item["created_at"] = str(item.get("created_at"))
                items.append(item)
            return items

    # --- Patch Candidates & Plans ---
    def save_patch_candidate(self, candidate: Any):
        if not hasattr(self, "_patch_candidates"):
            self._patch_candidates = {}
        self._patch_candidates[candidate.patch_id] = candidate

    def get_patch_candidate(self, candidate_id: str) -> Optional[Any]:
        if not hasattr(self, "_patch_candidates"):
            self._patch_candidates = {}
        return self._patch_candidates.get(candidate_id)

    def get_patch_candidates_by_plan(self, plan_id: str) -> List[Any]:
        if not hasattr(self, "_patch_candidates"):
            self._patch_candidates = {}
        return [c for c in self._patch_candidates.values() if getattr(c, "plan_id", None) == plan_id]

    def save_patch_plan(self, plan: Any):
        if not hasattr(self, "_patch_plans"):
            self._patch_plans = {}
        self._patch_plans[plan.plan_id] = plan

    def get_patch_plan(self, plan_id: str) -> Optional[Any]:
        if not hasattr(self, "_patch_plans"):
            self._patch_plans = {}
        return self._patch_plans.get(plan_id)

# Global singleton store instance
supabase_store = SupabaseStore()

