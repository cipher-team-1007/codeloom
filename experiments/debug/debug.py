import asyncio
from tests.integration.test_master_workflow import *
from engine.orchestrator.master_workflow import MasterOrchestrator

async def run():
    acquirer = mock_acquirer()
    intel = mock_source_intel()
    generator = mock_patch_generator()
    
    orch = MasterOrchestrator()
    orch.repo_acquirer = acquirer
    orch.source_intel = intel
    orch.patch_generator = generator

    r = await orch.run_remediation_workflow(baseline_finding(), 'https://github.com/example/repo', 'dummy-sha')
    print("FINAL STATUS:", r.final_status)
    print("FAILURE STAGE:", r.failure_stage)
    print("ERROR MSG:", r.error_message)

asyncio.run(run())
