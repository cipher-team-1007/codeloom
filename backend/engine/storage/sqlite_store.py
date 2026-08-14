"""
SQLite-based persistent storage for CodeLoom Engine.
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import contextlib
from engine.models import Cluster, Fix, SimulationResult

class SQLiteStore:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            # Default to codeloom_engine.db in the engine directory
            engine_dir = Path(__file__).resolve().parent.parent
            db_path = str(engine_dir / "codeloom_engine.db")
        
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                # Enable Write-Ahead Logging for better concurrency
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
                        data TEXT NOT NULL,
                        FOREIGN KEY(scan_id) REFERENCES scans(scan_id)
                    );

                    CREATE TABLE IF NOT EXISTS fixes (
                        fix_id TEXT PRIMARY KEY,
                        cluster_id TEXT NOT NULL,
                        data TEXT NOT NULL,
                        FOREIGN KEY(cluster_id) REFERENCES clusters(cluster_id)
                    );

                    CREATE TABLE IF NOT EXISTS simulations (
                        simulation_id TEXT PRIMARY KEY,
                        fix_id TEXT NOT NULL,
                        data TEXT NOT NULL,
                        FOREIGN KEY(fix_id) REFERENCES fixes(fix_id)
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
                # Existing installations may predate the richer scan metadata.
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(scans)")}
                for name, declaration in {
                    "url": "TEXT", "scores": "TEXT", "screenshot_ref": "TEXT"
                }.items():
                    if name not in columns:
                        conn.execute(f"ALTER TABLE scans ADD COLUMN {name} {declaration}")

    # --- Scans ---
    def save_scan(self, scan_id: str, total_findings: int, deduplicated_findings: int,
                  token_usage: Dict[str, Any], url: Optional[str] = None,
                  scores: Optional[Dict[str, Any]] = None, screenshot_ref: Optional[str] = None):
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO scans (scan_id, url, total_findings, deduplicated_findings, token_usage, scores, screenshot_ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (scan_id, url, total_findings, deduplicated_findings, json.dumps(token_usage), json.dumps(scores or {}), screenshot_ref)
                )

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        with contextlib.closing(self._get_conn()) as conn:
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
                "created_at": row["created_at"],
            }

    def get_all_scans(self, limit: int = 50, offset: int = 0, search: Optional[str] = None) -> Dict[str, Any]:
        with contextlib.closing(self._get_conn()) as conn:
            if search:
                query_filter = "%" + search + "%"
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM scans WHERE scan_id LIKE ? OR url LIKE ?",
                    (query_filter, query_filter)
                ).fetchone()["count"]
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
                    "created_at": row["created_at"],
                })

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items,
            }

    def delete_scan(self, scan_id: str) -> bool:
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                # Get cluster IDs for this scan to delete associated fixes & simulations
                cluster_rows = conn.execute("SELECT cluster_id FROM clusters WHERE scan_id = ?", (scan_id,)).fetchall()
                cluster_ids = [r["cluster_id"] for r in cluster_rows]

                if cluster_ids:
                    placeholders = ",".join(["?"] * len(cluster_ids))
                    # Get fix IDs
                    fix_rows = conn.execute(f"SELECT fix_id FROM fixes WHERE cluster_id IN ({placeholders})", cluster_ids).fetchall()
                    fix_ids = [r["fix_id"] for r in fix_rows]

                    if fix_ids:
                        fix_placeholders = ",".join(["?"] * len(fix_ids))
                        conn.execute(f"DELETE FROM simulations WHERE fix_id IN ({fix_placeholders})", fix_ids)

                    conn.execute(f"DELETE FROM fixes WHERE cluster_id IN ({placeholders})", cluster_ids)
                    conn.execute("DELETE FROM clusters WHERE scan_id = ?", (scan_id,))

                cur = conn.execute("DELETE FROM scans WHERE scan_id = ?", (scan_id,))
                return cur.rowcount > 0

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
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO clusters (cluster_id, scan_id, data) VALUES (?, ?, ?)",
                    (cluster.cluster_id, scan_id, cluster.model_dump_json())
                )

    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        with contextlib.closing(self._get_conn()) as conn:
            row = conn.execute("SELECT data FROM clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
            if not row:
                return None
            return Cluster.model_validate_json(row["data"])

    def get_clusters_for_scan(self, scan_id: str) -> List[Cluster]:
        with contextlib.closing(self._get_conn()) as conn:
            rows = conn.execute("SELECT data FROM clusters WHERE scan_id = ?", (scan_id,)).fetchall()
            return [Cluster.model_validate_json(row["data"]) for row in rows]

    # --- Fixes ---
    def save_fix(self, fix: Fix):
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO fixes (fix_id, cluster_id, data) VALUES (?, ?, ?)",
                    (fix.fix_id, fix.cluster_id, fix.model_dump_json())
                )

    def get_fix(self, fix_id: str) -> Optional[Fix]:
        with contextlib.closing(self._get_conn()) as conn:
            row = conn.execute("SELECT data FROM fixes WHERE fix_id = ?", (fix_id,)).fetchone()
            if not row:
                return None
            return Fix.model_validate_json(row["data"])

    def get_fixes_for_scan(self, scan_id: str) -> List[Fix]:
        with contextlib.closing(self._get_conn()) as conn:
            # Join fixes with clusters to get fixes for a specific scan
            rows = conn.execute('''
                SELECT f.data FROM fixes f
                JOIN clusters c ON f.cluster_id = c.cluster_id
                WHERE c.scan_id = ?
            ''', (scan_id,)).fetchall()
            return [Fix.model_validate_json(row["data"]) for row in rows]

    # --- Simulations ---
    def save_simulation(self, simulation: SimulationResult):
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO simulations (simulation_id, fix_id, data) VALUES (?, ?, ?)",
                    (simulation.simulation_id, simulation.fix_id, simulation.model_dump_json())
                )

    def get_simulation_for_fix(self, fix_id: str) -> Optional[SimulationResult]:
        with contextlib.closing(self._get_conn()) as conn:
            row = conn.execute("SELECT data FROM simulations WHERE fix_id = ?", (fix_id,)).fetchone()
            if not row:
                return None
            return SimulationResult.model_validate_json(row["data"])

    # --- Projects ---
    def save_project(self, project_id: str, name: str, repository_url: str, default_branch: str = "main") -> Dict[str, Any]:
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO projects (project_id, name, repository_url, default_branch, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (project_id, name, repository_url, default_branch)
                )
        return self.get_project(project_id) or {}

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with contextlib.closing(self._get_conn()) as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def get_all_projects(self) -> List[Dict[str, Any]]:
        with contextlib.closing(self._get_conn()) as conn:
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
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO remediations 
                    (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, details_json) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (remediation_id, project_id, scan_id, rule_id, target_file, final_status, pull_request_url, pull_request_number, json.dumps(details or {}))
                )

    def get_all_remediations(self, limit: int = 50) -> List[Dict[str, Any]]:
        with contextlib.closing(self._get_conn()) as conn:
            rows = conn.execute("SELECT * FROM remediations ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            items = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item.get("details_json") or "{}")
                items.append(item)
            return items

from engine.storage.supabase_store import supabase_store

# Global singleton store instance with Supabase Postgres primary & SQLite fallback
store = supabase_store

