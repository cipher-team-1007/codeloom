"""
Checkpoint: Verify SQLite persistence layer.
"""
import sys
import os
import tempfile
from pathlib import Path
from rich.console import Console

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from engine.storage.sqlite_store import SQLiteStore
from engine.models import Cluster, Fix, SimulationResult

console = Console()

def run_checks():
    console.print("\n[bold blue]Running Checkpoint: Storage[/bold blue]")
    
    # Use temp file database for tests so connections can close without losing data
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = SQLiteStore(db_path=temp_path)
    
    try:
        # Test 1: Scan
        store.save_scan("test-scan-01", 10, 5, {"total": 50})
        scan = store.get_scan("test-scan-01")
        assert scan is not None, "Failed to get scan"
        assert scan["total_findings"] == 10, "Wrong total findings"
        console.print("✅ Scan persistence working")

        # Test 2: Cluster
        cluster = Cluster(
            cluster_id="clst_123",
            title="Test Cluster",
            rule_id="test-rule",
            category="accessibility",
            severity="critical",
            instance_count=2,
            affected_selectors=[".test"],
            likely_root_cause="test",
            impact="test"
        )
        store.save_cluster("test-scan-01", cluster)
        saved_c = store.get_cluster("clst_123")
        assert saved_c is not None, "Failed to get cluster"
        assert saved_c.title == "Test Cluster", "Wrong cluster title"
        
        clusters = store.get_clusters_for_scan("test-scan-01")
        assert len(clusters) == 1, "Wrong number of clusters for scan"
        console.print("✅ Cluster persistence working")

        # Test 3: Fix
        fix = Fix(
            fix_id="fix_123",
            cluster_id="clst_123",
            title="Test Fix",
            explanation="test",
            root_cause="test",
            suggested_before="<a/>",
            suggested_after="<a>b</a>",
            confidence=0.9,
            tier="template",
            tokens_used=0
        )
        store.save_fix(fix)
        saved_f = store.get_fix("fix_123")
        assert saved_f is not None, "Failed to get fix"
        assert saved_f.title == "Test Fix", "Wrong fix title"
        
        fixes = store.get_fixes_for_scan("test-scan-01")
        assert len(fixes) == 1, "Wrong number of fixes for scan"
        console.print("✅ Fix persistence working")
        
        # Test 4: Simulation
        sim = SimulationResult(
            simulation_id="sim_123",
            fix_id="fix_123",
            before_violations=2,
            after_violations=0,
            rule_passed=True,
            score_before=80.0,
            score_after=100.0,
            score_improvement=20.0,
            is_sandbox=True
        )
        store.save_simulation(sim)
        saved_s = store.get_simulation_for_fix("fix_123")
        assert saved_s is not None, "Failed to get simulation"
        assert saved_s.score_improvement == 20.0, "Wrong score improvement"
        console.print("✅ Simulation persistence working")
        
        os.unlink(temp_path)
        return True
    except Exception as e:
        console.print(f"❌ Storage check failed: {str(e)}", style="red")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False

if __name__ == "__main__":
    if run_checks():
        sys.exit(0)
    sys.exit(1)
