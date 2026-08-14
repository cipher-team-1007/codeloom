import os
import pytest
from engine.github.client import GitHubClient
from engine.github.config import GitHubConfig

SKIP_REASON = "Live GitHub integration tests disabled. Set RUN_GITHUB_INTEGRATION_TESTS=1 to run."

@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("RUN_GITHUB_INTEGRATION_TESTS"), reason=SKIP_REASON)
async def test_live_public_repository_lookup():
    """
    Optional live integration test querying a public GitHub repository.
    Read-only operation only.
    """
    config = GitHubConfig()
    client = GitHubClient(config=config)

    repo = await client.get_repository("octocat", "Hello-World")
    assert repo.name == "Hello-World"
    assert repo.owner_login == "octocat"
    assert "github.com/octocat/Hello-World" in repo.html_url

@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("RUN_GITHUB_INTEGRATION_TESTS"), reason=SKIP_REASON)
async def test_live_public_commit_lookup():
    """
    Optional live integration test querying a public commit.
    Read-only operation only.
    """
    config = GitHubConfig()
    client = GitHubClient(config=config)

    commit = await client.get_commit("octocat", "Hello-World", "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d")
    assert commit.sha == "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
