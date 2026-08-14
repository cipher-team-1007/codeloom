import uuid
import logging
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from engine.models import Finding, Cluster
from engine.clustering.clusterer import ClusterEngine
from engine.repository.acquirer import RepositoryAcquirer
from engine.source_intelligence.client import SourceIntelligenceClient
from engine.source_intelligence.models import SourceMappingRequest, RuntimeEvidence
from engine.orchestrator.master_workflow import MasterOrchestrator
from engine.orchestrator.report_builder import RemediationReportBuilder
from engine.models.report import RemediationReport
from engine.telemetry.event_bus import EventBus, global_event_bus
from engine.telemetry.models import TelemetryEventType, RemediationStage

from engine.queue.models import (
    CanonicalFinding,
    FindingStatus,
    QueueStatus,
    BatchStatus,
    RemediationQueue,
    RemediationBatchReport,
)
from engine.queue.snapshot import SnapshotManager

logger = logging.getLogger("codeloom.queue.engine")


class RemediationQueueEngine:
    """
    Sequential execution engine orchestrating multi-finding remediation queues.
    Enforces single-file patch boundaries, evolving working snapshot management,
    atomic reversion on failed attempts, and AST drift protection.
    """

    def __init__(
        self,
        repo_acquirer: Optional[RepositoryAcquirer] = None,
        source_intel: Optional[SourceIntelligenceClient] = None,
        orchestrator: Optional[MasterOrchestrator] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.repo_acquirer = repo_acquirer or RepositoryAcquirer()
        self.source_intel = source_intel or SourceIntelligenceClient()
        self.event_bus = event_bus if event_bus is not None else global_event_bus
        self.orchestrator = orchestrator or MasterOrchestrator(event_bus=self.event_bus)
        self.clusterer = ClusterEngine()
        self._lock = asyncio.Lock()

    def create_queue_from_findings(
        self,
        repository_url: str,
        base_commit_sha: str,
        raw_findings: List[Finding],
    ) -> RemediationQueue:
        """
        Deduplicates raw findings into canonical findings, sorts by deterministic priority,
        and initializes a new RemediationQueue.
        """
        queue_id = f"q_{uuid.uuid4().hex[:8]}"
        
        # 1. Deduplicate & cluster findings
        clusters = self.clusterer.cluster(raw_findings) if raw_findings else []
        
        canonical_findings: List[CanonicalFinding] = []
        for c in clusters:
            f_id = f"cf_{c.cluster_id}_{uuid.uuid4().hex[:6]}"
            wf_id = f"wf_{uuid.uuid4().hex[:8]}"
            canonical = CanonicalFinding(
                finding_id=f_id,
                rule_id=c.rule_id,
                category=c.category,
                severity=c.severity,
                title=c.title,
                description=c.likely_root_cause or c.title,
                selectors=c.affected_selectors,
                html_snippets=[c.representative_snippet] if c.representative_snippet else [],
                instance_count=c.instance_count,
                source_matches=getattr(c, "source_matches", []),
                status=FindingStatus.QUEUED,
                remediation_workflow_id=wf_id,
            )
            canonical_findings.append(canonical)

        # 2. Deterministic priority sort
        canonical_findings = self.prioritize_findings(canonical_findings)

        queue = RemediationQueue(
            queue_id=queue_id,
            repository_url=repository_url,
            base_commit_sha=base_commit_sha,
            current_working_sha=base_commit_sha,
            findings=canonical_findings,
            current_index=0,
            total_findings=len(canonical_findings),
            verified_count=0,
            failed_count=0,
            skipped_count=0,
            blocked_count=0,
            status=QueueStatus.CREATED,
        )
        return queue

    def prioritize_findings(self, findings: List[CanonicalFinding]) -> List[CanonicalFinding]:
        """
        Deterministically orders findings:
        1. Severity: critical (0) > serious (1) > moderate (2) > minor (3)
        2. Occurrence count: highest instance_count first
        3. Tie-breaker: rule_id, then selectors
        """
        severity_rank = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        return sorted(
            findings,
            key=lambda f: (
                severity_rank.get(f.severity.lower(), 4),
                -f.instance_count,
                f.rule_id,
                f.selectors[0] if f.selectors else ""
            )
        )

    async def run_queue(
        self,
        queue: RemediationQueue,
        max_retries_per_finding: int = 1,
    ) -> RemediationBatchReport:
        """
        Sequentially executes all findings in the queue.
        Enforces: MAX_CONCURRENT_REMEDIATIONS = 1.
        """
        async with self._lock:
            queue.status = QueueStatus.RUNNING
            queue.started_at = datetime.now(timezone.utc).isoformat()
            
            snapshot_mgr = SnapshotManager(repo_acquirer=self.repo_acquirer)
            batch_reports: Dict[str, Any] = {}

            try:
                # Initialize working snapshot from base commit
                snapshot_mgr.initialize(queue.repository_url, queue.base_commit_sha)

                for idx, finding in enumerate(queue.findings):
                    queue.current_index = idx

                    # Check for cancellation between jobs
                    if queue.status == QueueStatus.CANCELLED:
                        logger.info(f"[{queue.queue_id}] Queue cancelled by user. Skipping remaining findings.")
                        for remaining in queue.findings[idx:]:
                            remaining.status = FindingStatus.SKIPPED
                            queue.skipped_count += 1
                        break

                    finding.status = FindingStatus.RUNNING
                    logger.info(
                        f"[{queue.queue_id}] Processing finding {idx + 1}/{queue.total_findings}: "
                        f"{finding.rule_id} ({finding.severity})"
                    )

                    # Ensure snapshot is clean
                    snapshot_mgr.rollback_unverified_changes()

                    # Execute finding with retry policy
                    success, report = await self._execute_finding_with_retry(
                        queue=queue,
                        finding=finding,
                        snapshot_mgr=snapshot_mgr,
                        max_retries=max_retries_per_finding
                    )

                    if report:
                        batch_reports[finding.finding_id] = report.model_dump()
                        queue.reports[finding.finding_id] = report.identity.workflow_id
                        finding.report_id = report.identity.workflow_id

                    if success:
                        queue.verified_count += 1
                    elif finding.status == FindingStatus.BLOCKED:
                        queue.blocked_count += 1
                    else:
                        queue.failed_count += 1

                # Calculate final aggregate batch status
                if queue.status == QueueStatus.CANCELLED:
                    agg_status = BatchStatus.CANCELLED
                elif queue.verified_count == queue.total_findings and queue.total_findings > 0:
                    agg_status = BatchStatus.ALL_VERIFIED
                elif queue.verified_count > 0:
                    agg_status = BatchStatus.PARTIALLY_VERIFIED
                elif queue.total_findings == 0:
                    agg_status = BatchStatus.ALL_VERIFIED
                else:
                    agg_status = BatchStatus.NONE_VERIFIED

                queue.status = QueueStatus.COMPLETED
                queue.completed_at = datetime.now(timezone.utc).isoformat()

                batch_report = RemediationBatchReport(
                    batch_id=f"batch_{uuid.uuid4().hex[:8]}",
                    queue_id=queue.queue_id,
                    repository=queue.repository_url,
                    base_commit_sha=queue.base_commit_sha,
                    final_working_sha=snapshot_mgr.current_working_sha or queue.base_commit_sha,
                    aggregate_status=agg_status,
                    total_findings=queue.total_findings,
                    verified_count=queue.verified_count,
                    failed_count=queue.failed_count,
                    skipped_count=queue.skipped_count,
                    blocked_count=queue.blocked_count,
                    findings=queue.findings,
                    reports=batch_reports,
                    completed_at=queue.completed_at,
                )
                return batch_report

            except Exception as e:
                logger.error(f"[{queue.queue_id}] Fatal queue execution error: {e}", exc_info=True)
                queue.status = QueueStatus.FAILED
                queue.completed_at = datetime.now(timezone.utc).isoformat()
                return RemediationBatchReport(
                    batch_id=f"batch_{uuid.uuid4().hex[:8]}",
                    queue_id=queue.queue_id,
                    repository=queue.repository_url,
                    base_commit_sha=queue.base_commit_sha,
                    final_working_sha=snapshot_mgr.current_working_sha or queue.base_commit_sha,
                    aggregate_status=BatchStatus.FAILED,
                    total_findings=queue.total_findings,
                    verified_count=queue.verified_count,
                    failed_count=queue.failed_count,
                    skipped_count=queue.skipped_count,
                    blocked_count=queue.blocked_count,
                    findings=queue.findings,
                    reports=batch_reports,
                    completed_at=queue.completed_at,
                )

            finally:
                snapshot_mgr.cleanup()

    async def _execute_finding_with_retry(
        self,
        queue: RemediationQueue,
        finding: CanonicalFinding,
        snapshot_mgr: SnapshotManager,
        max_retries: int,
    ) -> tuple[bool, Optional[RemediationReport]]:
        """
        Executes a single CanonicalFinding against the current working snapshot.
        If unverified on first attempt and retries remain, re-evaluates AST mapping
        and retries with a fresh workflow.
        """
        attempts = 0
        last_report: Optional[RemediationReport] = None

        while attempts <= max_retries:
            attempts += 1
            finding.retry_count = attempts - 1
            workflow_id = finding.remediation_workflow_id if attempts == 1 and finding.remediation_workflow_id else f"wf_{uuid.uuid4().hex[:8]}"
            finding.remediation_workflow_id = workflow_id

            # 1. AST Line Drift Protection: Re-evaluate source mapping on updated working tree
            curr_snapshot = snapshot_mgr.current_snapshot
            if not curr_snapshot:
                finding.status = FindingStatus.BLOCKED
                finding.block_reason = "No active snapshot"
                return False, None

            target_sel = finding.selectors[0] if finding.selectors else "body"
            rep_snippet = finding.html_snippets[0] if finding.html_snippets else ""

            mapping_req = SourceMappingRequest(
                repositoryPath=curr_snapshot.local_path,
                commitSha=curr_snapshot.commit_sha,
                runtimeEvidence=RuntimeEvidence(
                    ruleId=finding.rule_id,
                    targetSelector=target_sel,
                    htmlSnippet=rep_snippet
                )
            )

            mapping_res = None
            try:
                mapping_res = await self.source_intel.map_source(mapping_req)
            except Exception as e:
                logger.warning(f"Source intelligence remapping error for {finding.rule_id}: {e}")

            # 2. Convert CanonicalFinding to Finding for MasterOrchestrator
            orch_finding = Finding(
                id=finding.finding_id,
                source="axe",
                category=finding.category,
                rule_id=finding.rule_id,
                title=finding.title,
                description=finding.description,
                severity=finding.severity,
                selectors=finding.selectors,
                html_snippets=finding.html_snippets,
                source_matches=getattr(finding, "source_matches", []),
            )

            if not mapping_res or mapping_res.status in ("NOT_FOUND", "AMBIGUOUS") or not mapping_res.candidates:
                logger.info(f"[{queue.queue_id}] Remote AST mapping returned {mapping_res.status if mapping_res else 'None'} for {finding.rule_id}. Trying local repository AST scanner fallback.")
                mapping_res = self.orchestrator._local_source_mapping_fallback(curr_snapshot.local_path, target_sel, rep_snippet, finding=orch_finding)

            if mapping_res and mapping_res.candidates:
                target_candidate = mapping_res.candidates[0]
                finding.source_file = target_candidate.file
                finding.source_component = target_candidate.component
            else:
                finding.status = FindingStatus.BLOCKED
                finding.block_reason = "Source intelligence could not locate target source file in working tree."
                snapshot_mgr.rollback_unverified_changes()
                return False, None

            # 3. Execute MasterOrchestrator against current working snapshot
            try:
                result = await self.orchestrator.run_remediation_workflow(
                    finding=orch_finding,
                    repo_url=queue.repository_url,
                    commit_sha=curr_snapshot.commit_sha,
                    workflow_id=workflow_id,
                    snapshot=curr_snapshot,
                    cleanup_snapshot=False,
                )
                report = RemediationReportBuilder.build(result)
                last_report = report

                # 4. Check authoritative verification
                if report.final_status == "VERIFIED" and result.patch_candidate:
                    # Apply verified patch to cumulative working snapshot
                    try:
                        target_file = target_candidate.file
                        new_sha = snapshot_mgr.apply_verified_patch(
                            unified_diff=result.patch_candidate.unified_diff,
                            target_file=target_file,
                            rule_id=finding.rule_id
                        )
                        queue.current_working_sha = new_sha
                        finding.status = FindingStatus.VERIFIED
                        finding.error_message = None
                        return True, report
                    except Exception as apply_err:
                        logger.error(f"Failed to advance working snapshot for {finding.rule_id}: {apply_err}")
                        finding.status = FindingStatus.NOT_VERIFIED
                        finding.error_message = f"Snapshot application error: {apply_err}"
                        snapshot_mgr.rollback_unverified_changes()
                        return False, report
                else:
                    # Unverified outcome: atomic rollback and mark NOT_VERIFIED
                    snapshot_mgr.rollback_unverified_changes()
                    finding.status = FindingStatus.NOT_VERIFIED
                    finding.error_message = report.error_message or "Sandbox verification failed"
                    logger.warning(f"[{queue.queue_id}] Finding {finding.rule_id} was NOT_VERIFIED. Rolling back snapshot and proceeding.")
                    return False, report

            except Exception as orch_err:
                logger.error(f"MasterOrchestrator error for {finding.rule_id}: {orch_err}")
                snapshot_mgr.rollback_unverified_changes()
                finding.status = FindingStatus.NOT_VERIFIED
                finding.error_message = str(orch_err)
                return False, last_report

        return False, last_report
