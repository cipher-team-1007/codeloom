import logging
import uuid
from typing import Optional, Dict, Any

try:
    from github import Github
    from github.GithubException import GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

logger = logging.getLogger("codeloom.github.pr_generator")

class PRGenerator:
    """
    Handles creating branches, committing AI patches, and opening Pull Requests via GitHub API.
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        if GITHUB_AVAILABLE:
            self.gh = Github(access_token)
        else:
            self.gh = None
            logger.warning("PyGithub is not installed. PR Generation will be mocked.")

    def create_pull_request(
        self, 
        repo_full_name: str, 
        base_branch: str, 
        file_path: str, 
        new_content: str, 
        commit_message: str, 
        pr_title: str, 
        pr_body: str
    ) -> Dict[str, Any]:
        """
        Creates a branch, commits the file, and opens a PR.
        Returns a dict with the PR URL and branch name.
        """
        if not GITHUB_AVAILABLE:
            logger.info(f"[MOCK] Created PR on {repo_full_name} for file {file_path}")
            return {
                "pr_url": f"https://github.com/{repo_full_name}/pull/mock",
                "branch_name": "codeloom-patch-mock",
                "status": "success"
            }
            
        try:
            repo = self.gh.get_repo(repo_full_name)
            
            # 1. Get base branch HEAD
            base_ref = repo.get_branch(base_branch)
            
            # 2. Create new branch
            branch_name = f"codeloom-patch-{uuid.uuid4().hex[:6]}"
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.commit.sha)
            logger.info(f"Created branch {branch_name} on {repo_full_name}")
            
            # 3. Get existing file to get its blob SHA
            try:
                contents = repo.get_contents(file_path, ref=base_branch)
                file_sha = contents.sha
            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist? We are patching an existing file, this shouldn't happen usually
                    file_sha = None
                else:
                    raise

            # 4. Create commit
            if file_sha:
                repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=new_content,
                    sha=file_sha,
                    branch=branch_name
                )
            else:
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=new_content,
                    branch=branch_name
                )
            logger.info(f"Committed changes to {file_path} on {branch_name}")
            
            # 5. Create Pull Request
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=base_branch
            )
            logger.info(f"Created Pull Request: {pr.html_url}")
            
            return {
                "pr_url": pr.html_url,
                "branch_name": branch_name,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
