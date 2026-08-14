import secrets
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, Query, Header, Depends
from fastapi.responses import RedirectResponse, JSONResponse

from engine.github.config import GitHubConfig
from engine.github.vault import TokenVault
from engine.github.auth import GitHubAuthManager
from engine.github.exceptions import (
    GitHubAuthNotConfiguredError,
    GitHubAuthorizationDeniedError,
    GitHubInvalidStateError,
    GitHubStateExpiredError,
    GitHubTokenExchangeError,
    GitHubIdentityLookupError,
    GitHubOpenRedirectError,
)

logger = logging.getLogger("codeloom.api.github")

router = APIRouter(prefix="/api/v1/github", tags=["github"])

# Shared singleton instance of GitHubAuthManager for the application lifecycle
_config = GitHubConfig()
_vault = TokenVault(encryption_key=_config.encryption_key)
_auth_manager = GitHubAuthManager(config=_config, vault=_vault)

def get_auth_manager() -> GitHubAuthManager:
    return _auth_manager

SESSION_COOKIE_NAME = "codeloom_session"

def _get_or_create_session_id(request: Request, response: Optional[Response] = None) -> str:
    """Extracts existing session ID from cookies/headers or generates a new secure session ID."""
    session_id = request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = secrets.token_urlsafe(24)
        if response:
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                max_age=86400 * 30, # 30 days
            )
    return session_id

@router.get("/authorize", summary="Initiate GitHub OAuth Authorization Flow")
async def authorize(
    request: Request,
    response: Response,
    redirect_url: Optional[str] = Query(None, description="Optional custom frontend redirect destination"),
    json_mode: bool = Query(False, alias="json", description="If true, returns JSON payload instead of HTTP redirect"),
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Generates a secure OAuth authorization URL with CSRF state and redirects the user to GitHub.
    """
    session_id = _get_or_create_session_id(request, response)

    # Capture calling page from Referer header if redirect_url not explicitly supplied
    referer = request.headers.get("Referer")
    if referer and not redirect_url:
        redirect_url = referer

    # Fallback if OAuth is unconfigured or configured with test placeholder
    if not auth_mgr.config.is_oauth_configured() or auth_mgr.config.client_id.startswith("test_") or auth_mgr.config.client_id in ("placeholder", "demo"):
        if json_mode or "application/json" in request.headers.get("Accept", ""):
            return JSONResponse(status_code=400, content={"error": "oauth_unconfigured", "detail": "GitHub OAuth App is not configured. Please use Personal Access Token (PAT) or configure GITHUB_CLIENT_ID in .env."})
        target_redir = redirect_url or auth_mgr.config.frontend_redirect_url or "/audit-code.html"
        sep = "&" if "?" in target_redir else "?"
        final_url = f"{target_redir}{sep}github=unconfigured"
        return RedirectResponse(url=final_url, status_code=307)

    try:
        auth_url = auth_mgr.generate_authorization_url(session_id=session_id, custom_redirect=redirect_url)
    except GitHubAuthNotConfiguredError as e:
        raise HTTPException(status_code=400, detail="GitHub OAuth App is unconfigured.") from e
    except GitHubOpenRedirectError as e:
        logger.warning("Open redirect rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    if json_mode or "application/json" in request.headers.get("Accept", ""):
        res = JSONResponse(content={"authorization_url": auth_url, "session_id": session_id})
        res.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True, samesite="lax", max_age=86400 * 30)
        return res

    redirect_resp = RedirectResponse(url=auth_url, status_code=307)
    redirect_resp.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True, samesite="lax", max_age=86400 * 30)
    return redirect_resp

@router.post("/connect-pat", summary="Connect GitHub via Personal Access Token (PAT)")
async def connect_pat(
    request: Request,
    response: Response,
    payload: dict,
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Authenticates a user via GitHub Personal Access Token (PAT) or OAuth Token.
    Queries profile from GitHub REST API, encrypts token into vault, and sets session cookie.
    """
    raw_token = payload.get("token", "").strip()
    if not raw_token:
        raise HTTPException(status_code=400, detail="GitHub Personal Access Token is required.")

    session_id = _get_or_create_session_id(request, response)

    try:
        credential, profile = await auth_mgr.connect_with_token(session_id, raw_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    res = JSONResponse(content={
        "connected": True,
        "account_login": profile["login"],
        "avatar_url": profile["avatar_url"],
        "user_id": profile["user_id"],
        "message": f"Successfully connected as @{profile['login']}"
    })
    res.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True, samesite="lax", max_age=86400 * 30)
    return res

@router.get("/callback", summary="GitHub OAuth Redirect Callback")
async def callback(
    request: Request,
    code: Optional[str] = Query(None, description="GitHub authorization code"),
    state: Optional[str] = Query(None, description="OAuth CSRF state"),
    error: Optional[str] = Query(None, description="OAuth error code if authorization was denied"),
    error_description: Optional[str] = Query(None, description="Description of OAuth failure"),
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Handles the redirect from GitHub: verifies state, exchanges code for access token,
    queries user identity, encrypts token into vault, and redirects to frontend.
    """
    if error:
        logger.warning("User denied GitHub authorization: %s - %s", error, error_description)
        redirect_target = f"{auth_mgr.config.frontend_redirect_url}?github=denied&error={error}"
        return RedirectResponse(url=redirect_target, status_code=307)

    if not code or not state:
        logger.warning("Callback received with missing code or state.")
        raise HTTPException(status_code=400, detail="Missing required OAuth code or state parameter.")

    try:
        credential, target_redirect = await auth_mgr.process_callback(
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )
    except GitHubInvalidStateError as e:
        logger.warning("State validation error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid or unrecognized OAuth state parameter.") from e
    except GitHubStateExpiredError as e:
        logger.warning("State expired error: %s", e)
        raise HTTPException(status_code=400, detail="OAuth state expired. Please re-initiate authorization.") from e
    except (GitHubTokenExchangeError, GitHubIdentityLookupError) as e:
        logger.error("Authentication exchange error: %s", e)
        redirect_url = getattr(auth_mgr.config, 'frontend_redirect_url', '/audit-code.html')
        sep = "&" if "?" in redirect_url else "?"
        import urllib.parse
        err_param = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"{redirect_url}{sep}github=error&message={err_param}", status_code=307)

    # Build safe redirect URL with connection status indicator (NO secrets/tokens in URL)
    sep = "&" if "?" in target_redirect else "?"
    final_url = f"{target_redirect}{sep}github=connected"

    resp = RedirectResponse(url=final_url, status_code=307)
    resp.set_cookie(key=SESSION_COOKIE_NAME, value=credential.credential_id, httponly=True, samesite="lax", max_age=86400 * 30)
    return resp

@router.get("/status", summary="Check GitHub Connection Status")
async def status(
    request: Request,
    session_id: Optional[str] = Query(None),
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Returns non-sensitive connection status metadata for the current session.
    """
    target_session = session_id or request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    return auth_mgr.get_connection_status(target_session)

@router.post("/disconnect", summary="Disconnect GitHub Account")
async def disconnect(
    request: Request,
    response: Response,
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Removes the stored GitHub credential and disconnects the account for the current session.
    """
    session_id = request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    was_connected = auth_mgr.disconnect(session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {
        "connected": False,
        "disconnected": was_connected,
        "message": "GitHub account disconnected successfully.",
    }

@router.get("/repositories", summary="List Connected User Repositories")
async def list_repositories(
    request: Request,
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Returns authentic GitHub repositories owned or accessible by the connected user.
    """
    session_id = request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    repos = await auth_mgr.get_user_repositories(session_id)
    return {"repositories": repos, "count": len(repos)}

@router.post("/config", summary="Configure GitHub OAuth Credentials Runtime")
async def update_oauth_config(
    payload: dict,
    auth_mgr: GitHubAuthManager = Depends(get_auth_manager),
):
    """
    Dynamically updates GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in engine memory.
    """
    client_id = payload.get("client_id", "").strip()
    client_secret = payload.get("client_secret", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Both client_id and client_secret are required.")
    
    auth_mgr.config.client_id = client_id
    auth_mgr.config.client_secret = client_secret
    import os
    os.environ["GITHUB_CLIENT_ID"] = client_id
    os.environ["GITHUB_CLIENT_SECRET"] = client_secret
    return {"status": "configured", "client_id": client_id}

from engine.github.publisher import GitHubPublisher
from engine.github.models import PublicationResult
from engine.github.exceptions import (
    GitHubError,
    GitHubAuthenticationError,
    PublicationError,
    RemediationNotFoundError,
    RemediationNotVerifiedError,
    InvalidPatchFingerprintError,
    BaseCommitStaleError,
    PatchApplicationError,
    GitHubBranchCreationError,
    GitHubCommitCreationError,
    GitHubPullRequestCreationError,
)

_publisher = GitHubPublisher(config=_config, vault=_vault)

def get_publisher() -> GitHubPublisher:
    return _publisher

@router.post("/remediations/{remediation_id}/publish", response_model=PublicationResult, summary="Publish Verified Patch as GitHub Pull Request")
async def publish_remediation(
    remediation_id: str,
    request: Request,
    publisher: GitHubPublisher = Depends(get_publisher),
):
    """
    Publishes an already verified remediation patch to GitHub as an automated Pull Request.
    Enforces all 8 verification gates and TOCTOU base commit integrity checks.
    """
    session_id = request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "GITHUB_NOT_CONNECTED", "message": "GitHub account is not connected. Please authenticate first."}
        )

    try:
        result = await publisher.publish_verified_remediation(
            remediation_id=remediation_id,
            session_id=session_id,
        )
        return result
    except RemediationNotFoundError as e:
        logger.warning("Publication rejected: %s", e)
        raise HTTPException(status_code=404, detail={"error": "REMEDIATION_NOT_FOUND", "message": str(e)}) from e
    except GitHubAuthenticationError as e:
        logger.warning("Publication rejected: %s", e)
        raise HTTPException(status_code=401, detail={"error": "GITHUB_NOT_CONNECTED", "message": str(e)}) from e
    except RemediationNotVerifiedError as e:
        logger.warning("Publication rejected: %s", e)
        raise HTTPException(status_code=422, detail={"error": "NOT_VERIFIED", "message": str(e)}) from e
    except InvalidPatchFingerprintError as e:
        logger.error("Publication rejected: %s", e)
        raise HTTPException(status_code=400, detail={"error": "INVALID_PATCH_FINGERPRINT", "message": str(e)}) from e
    except BaseCommitStaleError as e:
        logger.warning("Publication rejected: %s", e)
        raise HTTPException(status_code=409, detail={"error": "BASE_COMMIT_STALE", "message": str(e)}) from e
    except PatchApplicationError as e:
        logger.error("Publication rejected: %s", e)
        raise HTTPException(status_code=400, detail={"error": "PATCH_APPLICATION_FAILED", "message": str(e)}) from e
    except (GitHubBranchCreationError, GitHubCommitCreationError, GitHubPullRequestCreationError, GitHubError) as e:
        logger.error("GitHub API publication error: %s", e)
        raise HTTPException(status_code=502, detail={"error": "GITHUB_API_ERROR", "message": str(e)}) from e
    except Exception as e:
        logger.error("Unexpected publication error: %s", e)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": f"Unexpected error during publication: {e}"}) from e


@router.post("/queues/{queue_id}/publish", response_model=PublicationResult, summary="Publish Verified Multi-Finding Batch as GitHub Pull Request")
async def publish_queue(
    queue_id: str,
    request: Request,
    publisher: GitHubPublisher = Depends(get_publisher),
):
    """
    Publishes all verified remediations in a completed batch queue to GitHub as a single cumulative Pull Request.
    Enforces single-file boundary, TOCTOU base SHA checks, and fingerprint verification for every verified finding.
    """
    session_id = request.headers.get("X-Session-ID") or request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "GITHUB_NOT_CONNECTED", "message": "GitHub account is not connected. Please authenticate first."}
        )

    try:
        result = await publisher.publish_verified_batch(
            queue_id=queue_id,
            session_id=session_id,
        )
        return result
    except RemediationNotFoundError as e:
        logger.warning("Batch publication rejected: %s", e)
        raise HTTPException(status_code=404, detail={"error": "REMEDIATION_NOT_FOUND", "message": str(e)}) from e
    except GitHubAuthenticationError as e:
        logger.warning("Batch publication rejected: %s", e)
        raise HTTPException(status_code=401, detail={"error": "GITHUB_NOT_CONNECTED", "message": str(e)}) from e
    except RemediationNotVerifiedError as e:
        logger.warning("Batch publication rejected: %s", e)
        raise HTTPException(status_code=422, detail={"error": "NOT_VERIFIED", "message": str(e)}) from e
    except InvalidPatchFingerprintError as e:
        logger.error("Batch publication rejected: %s", e)
        raise HTTPException(status_code=400, detail={"error": "INVALID_PATCH_FINGERPRINT", "message": str(e)}) from e
    except BaseCommitStaleError as e:
        logger.warning("Batch publication rejected: %s", e)
        raise HTTPException(status_code=409, detail={"error": "BASE_COMMIT_STALE", "message": str(e)}) from e
    except PatchApplicationError as e:
        logger.error("Batch publication rejected: %s", e)
        raise HTTPException(status_code=400, detail={"error": "PATCH_APPLICATION_FAILED", "message": str(e)}) from e
    except (GitHubBranchCreationError, GitHubCommitCreationError, GitHubPullRequestCreationError, GitHubError) as e:
        logger.error("GitHub API batch publication error: %s", e)
        raise HTTPException(status_code=502, detail={"error": "GITHUB_API_ERROR", "message": str(e)}) from e
    except Exception as e:
        logger.error("Unexpected batch publication error: %s", e)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": f"Unexpected error during batch publication: {e}"}) from e


