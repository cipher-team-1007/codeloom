"""
Main engine orchestrator coordinating deduplication, clustering, specialists, and fix generation.
"""
from typing import List, Dict, Any
import logging
from pydantic import BaseModel

logger = logging.getLogger("codeloom.orchestrator")

from engine.config import EngineConfig
from engine.models import Finding, Cluster, Fix
from engine.dedup.deduplicator import Deduplicator
from engine.clustering.clusterer import ClusterEngine
from engine.clustering.enrichment import ClusterEnricher
from engine.knowledge.registry import KnowledgeRegistry
from engine.specialists.accessibility import AccessibilitySpecialist
from engine.specialists.seo import SEOSpecialist
from engine.specialists.performance import PerformanceSpecialist
from engine.orchestrator.token_budget import TokenBudgetManager
from engine.ai.context_builder import ContextBuilder
from engine.ai.prompt_templates import PROMPTS
from engine.ai.llm_gateway import LLMGateway
from engine.ai.output_validator import OutputValidator
from engine.ai.fallback import FallbackGenerator
from engine.scanner.score_calculator import ScoreCalculator
from engine.source_intelligence.client import SourceIntelligenceClient
from engine.source_intelligence.models import SourceMappingRequest, RuntimeEvidence
from engine.source_intelligence.exceptions import SourceIntelligenceError
from engine.repository.acquirer import RepositoryAcquirer
from engine.repository.models import RepositoryCoordinate

class EngineResult(BaseModel):
    total_findings: int
    deduplicated_findings: int
    scores: Dict[str, int]
    clusters: List[Cluster]
    fixes: List[Fix]
    token_usage: Dict[str, Any]


class EngineOrchestrator:
    """
    Central brain of the CodeLoom Engine.
    Executes tiered resolution pipeline with minimal token burn.
    """

    def __init__(self, config: EngineConfig = None):
        self.config = config or EngineConfig()
        self.deduplicator = Deduplicator()
        self.clusterer = ClusterEngine()
        self.knowledge = KnowledgeRegistry()
        self.enricher = ClusterEnricher(self.knowledge)
        self.token_budget = TokenBudgetManager(self.config.max_tokens_per_scan)
        self.score_calculator = ScoreCalculator()
        self.source_intel_client = SourceIntelligenceClient()
        self.repo_acquirer = RepositoryAcquirer()

        self.specialists = {
            "accessibility": AccessibilitySpecialist(self.knowledge),
            "seo": SEOSpecialist(self.knowledge),
            "performance": PerformanceSpecialist(self.knowledge),
        }

        self.context_builder = ContextBuilder()
        self.llm_gateway = LLMGateway(self.config)
        self.output_validator = OutputValidator()
        self.fallback = FallbackGenerator()

    async def process_scan(self, findings: List[Finding], repo_url: str = None, commit_sha: str = None) -> EngineResult:
        logger.info(f"Orchestrator starting process for {len(findings)} findings")
        self.token_budget = TokenBudgetManager(self.config.max_tokens_per_scan)
        # Step 1: Deduplicate across tools
        dedup_res = self.deduplicator.deduplicate(findings)
        clean_findings = dedup_res.findings
        logger.info(f"Deduplication removed {dedup_res.original_count - dedup_res.deduped_count} duplicates")

        # Step 2: Calculate scores
        scores_obj = self.score_calculator.calculate(clean_findings)
        scores_dict = scores_obj.model_dump()

        # Step 3: Cluster findings
        clusters = self.clusterer.cluster(clean_findings)
        logger.info(f"Clustered into {len(clusters)} root causes")

        # Step 4: Enrich with domain knowledge
        for cluster in clusters:
            self.enricher.enrich(cluster, len(clean_findings))

        # Step 4b: Source Intelligence Mapping (if repository context provided)
        if repo_url and commit_sha:
            snapshot = None
            try:
                coord = RepositoryCoordinate(repository_url=repo_url, requested_commit_sha=commit_sha)
                snapshot = self.repo_acquirer.acquire(coord)
                
                for i, cluster in enumerate(clusters):
                    try:
                        logger.info(f"Mapping source for cluster {cluster.cluster_id}")
                        request = SourceMappingRequest(
                            repositoryPath=snapshot.local_path,
                            commitSha=snapshot.commit_sha,
                            runtimeEvidence=RuntimeEvidence(
                                ruleId=cluster.rule_id,
                                targetSelector=cluster.affected_selectors[0] if cluster.affected_selectors else "body",
                                htmlSnippet=cluster.representative_snippet
                            )
                        )
                        result = await self.source_intel_client.map_source(request)
                        if result.status == "MATCHED" and result.candidates:
                            # Store source context on the cluster for the fix generator
                            cluster.likely_root_cause += f"\nSource mapped to {result.candidates[0].file} ({result.candidates[0].component})"
                        elif result.status == "AMBIGUOUS":
                            cluster.likely_root_cause += "\nSource mapping ambiguous (multiple candidates)."
                        else:
                            cluster.likely_root_cause += "\nSource mapping not found in repository."
                    except SourceIntelligenceError as e:
                        logger.warning(f"Source intelligence failed for cluster {cluster.cluster_id}: {e}")
                        
            except Exception as e:
                logger.error(f"Repository acquisition failed: {e}")
                for cluster in clusters:
                    cluster.likely_root_cause += f"\nFailed to acquire repository for source mapping."
            
            finally:
                if snapshot:
                    self.repo_acquirer._cleanup_workspace(snapshot.local_path)

        # Step 5: Prioritize clusters by domain severity
        clusters = self._prioritize(clusters)

        # Step 6: Generate initial cluster preview fixes using domain specialists (0 tokens, instant response)
        fixes: List[Fix] = []
        for cluster in clusters:
            specialist = self.specialists.get(cluster.category, self.specialists["accessibility"])
            fix = specialist.generate_template_fix(cluster) or self.fallback.create_fallback(cluster)
            if fix:
                fixes.append(fix)
                cluster.fix_status = "generated"

        logger.info(f"Orchestration complete. Token usage: {self.token_budget.get_usage()}")
        return EngineResult(
            total_findings=len(findings),
            deduplicated_findings=len(clean_findings),
            scores=scores_dict,
            clusters=clusters,
            fixes=fixes,
            token_usage=self.token_budget.get_usage(),
        )

    async def _generate_fix(
        self,
        cluster: Cluster,
        provider: str = None,
        model: str = None,
        api_key: str = None,
        framework: str = "vanilla",
        custom_instructions: str = ""
    ) -> Fix:
        specialist = self.specialists.get(cluster.category, self.specialists["accessibility"])

        # Tier 1: Try template fix (0 tokens) if no custom prompt overrides requested
        if not custom_instructions and not provider:
            template_fix = specialist.generate_template_fix(cluster)
            if template_fix:
                logger.debug(f"Template fix applied for cluster {cluster.cluster_id}")
                self.token_budget.record_usage(0, "template")
                return template_fix

        # Tier 2/3: AI Fix
        tier = cluster.fix_tier or "light_ai"
        if not self.token_budget.can_afford(tier):
            logger.warning(f"Token budget exhausted for {tier}. Using fallback for cluster {cluster.cluster_id}")
            return self.fallback.create_fallback(cluster)

        # Build context
        base_ctx = self.context_builder.build(
            cluster,
            framework=framework,
            custom_instructions=custom_instructions
        )
        domain_ctx = specialist.enhance_context(cluster)
        full_ctx = {**base_ctx, **domain_ctx}

        # Prompt selection
        prompt_key = "light_ai_v1" if tier == "light_ai" else "full_ai_v1"
        if cluster.category == "seo":
            prompt_key = "seo_ai_v1"
        elif cluster.category == "performance":
            prompt_key = "perf_ai_v1"
        elif "contrast" in cluster.rule_id.lower():
            prompt_key = "contrast_v2"
        elif "keyboard" in cluster.rule_id.lower() or "focus" in cluster.rule_id.lower():
            prompt_key = "keyboard_v2"

        prompt_template = PROMPTS.get(prompt_key, PROMPTS["light_ai_v1"])

        max_attempts = 2
        validation_feedback = ""

        for attempt in range(max_attempts):
            try:
                curr_template = prompt_template
                if validation_feedback:
                    curr_template += f"\n\nCRITICAL FIX REQUIRED: Previous attempt failed validation with errors:\n{validation_feedback}\nEnsure all HTML tags are balanced and JSON is valid."

                llm_response = await self.llm_gateway.generate(
                    prompt_template=curr_template,
                    context=full_ctx,
                    tier=tier,
                    provider_override=provider,
                    model_override=model,
                    api_key_override=api_key,
                )
                self.token_budget.record_usage(llm_response.tokens_used, tier)

                val_report = self.output_validator.validate_report(llm_response.parsed, cluster)
                if val_report.is_valid:
                    fix = self.output_validator.validate_and_parse(
                        llm_response.parsed, cluster, tier, llm_response.tokens_used
                    )
                    if fix and specialist.validate_fix(fix, cluster):
                        return fix
                else:
                    validation_feedback = "; ".join(val_report.errors)
                    logger.warning(f"Validation failed for cluster {cluster.cluster_id} on attempt {attempt+1}: {validation_feedback}")

            except Exception as e:
                logger.error(f"AI generation failed for cluster {cluster.cluster_id} on attempt {attempt+1}: {str(e)}")

        logger.warning(f"All attempts failed for cluster {cluster.cluster_id}. Using fallback.")
        # Fallback if AI fails or invalid
        return self.fallback.create_fallback(cluster)

    def _prioritize(self, clusters: List[Cluster]) -> List[Cluster]:
        for cluster in clusters:
            spec = self.specialists.get(cluster.category)
            if spec:
                cluster_priority = spec.get_priority_score(cluster)
                setattr(cluster, "_priority", cluster_priority)

        return sorted(clusters, key=lambda c: getattr(c, "_priority", 0.5), reverse=True)
