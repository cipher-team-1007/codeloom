from typing import Optional
import logging
from engine.orchestrator.models import RemediationWorkflowResult
from engine.models.report import (
    RemediationReport, ReportIdentity, ReportFinding, ReportRootCause,
    ReportSourceLocation, ReportPatch, ReportValidation,
    ReportValidationCheck, ReportSandbox, ReportBeforeAfter
)

logger = logging.getLogger("codeloom.report_builder")

class RemediationReportBuilder:
    """
    Transforms internal orchestration evidence into a stable, UI-facing RemediationReport contract.
    """
    
    @staticmethod
    def build(result: RemediationWorkflowResult) -> RemediationReport:
        identity = ReportIdentity(
            workflow_id=result.workflow_id,
            repository=result.repository_identity,
            commit_sha=result.commit_sha,
            plan_id=result.plan_id,
            patch_id=result.patch_id
        )
        
        finding = ReportFinding(
            rule_id=result.target_rule,
            description=result.finding.description if result.finding else "Unknown description",
            impact=result.finding.severity if result.finding else "Unknown impact",
            target_selector=result.finding.selectors[0] if (result.finding and result.finding.selectors) else "Unknown selector"
        )
        
        root_cause = None
        if result.cluster and result.cluster.likely_root_cause:
            root_cause = ReportRootCause(description=result.cluster.likely_root_cause)
            
        source_location = None
        if result.source_mapping_result and result.source_mapping_result.candidates:
            # We assume the first candidate is the chosen one, or we take from PatchPlan
            candidate = result.source_mapping_result.candidates[0]
            if result.patch_plan:
                candidate_file = result.patch_plan.target.file_path
                candidate_start = result.patch_plan.target.start_line
                candidate_end = result.patch_plan.target.end_line
                candidate_component = result.patch_plan.target.component_name
            else:
                candidate_file = candidate.file
                candidate_start = candidate.sourceRange.start.line
                candidate_end = candidate.sourceRange.start.line + 20
                candidate_component = candidate.component
                
            source_location = ReportSourceLocation(
                file=candidate_file,
                start_line=candidate_start,
                end_line=candidate_end,
                component=candidate_component,
                match_status=result.source_mapping_result.status
            )
        elif result.source_mapping_status != "PENDING":
            # Failed mapping
            source_location = ReportSourceLocation(
                file="unknown",
                start_line=0,
                end_line=0,
                match_status=result.source_mapping_status
            )
            
        patch = None
        if result.patch_candidate:
            patch = ReportPatch(
                patch_id=result.patch_candidate.patch_id,
                files_changed=result.patch_candidate.files_changed,
                unified_diff=result.patch_candidate.unified_diff,
                rationale=result.patch_candidate.rationale
            )
            
        validation = None
        if result.validation_result:
            checks = [
                ReportValidationCheck(
                    name=c.name,
                    status=c.status,
                    message=c.message
                ) for c in result.validation_result.checks
            ]
            validation = ReportValidation(
                status=result.validation_result.status,
                checks=checks
            )
            
        sandbox_execution = None
        before_after = None
        if result.sandbox_result:
            sandbox_execution = ReportSandbox(
                status=result.sandbox_result.status,
                verification_reason=result.sandbox_result.verification_reason
            )
            
            before_status = "VIOLATION_PRESENT" if result.sandbox_result.baseline_finding else "UNKNOWN"
            # If the status is VERIFIED, the after finding is None/empty meaning it disappeared
            # If the status is NOT_VERIFIED, the after finding is present meaning it failed to resolve
            if result.sandbox_result.status == "VERIFIED":
                after_status = "VIOLATION_RESOLVED"
            elif result.sandbox_result.status == "NOT_VERIFIED":
                after_status = "VIOLATION_PRESENT"
            else:
                after_status = "UNKNOWN"
                
            before_after = ReportBeforeAfter(
                rule_id=result.target_rule,
                target_selector=finding.target_selector,
                before_status=before_status,
                after_status=after_status
            )
            
        return RemediationReport(
            identity=identity,
            finding=finding,
            root_cause=root_cause,
            source_location=source_location,
            patch=patch,
            validation=validation,
            sandbox_execution=sandbox_execution,
            before_after=before_after,
            final_status=result.final_status,
            failure_stage=result.failure_stage,
            error_message=result.error_message
        )
