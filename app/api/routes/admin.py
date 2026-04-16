from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import admin_auth, knowledge_dependency, repository_dependency, settings_dependency
from app.schemas.admin import GroupResponse, UserAccessResponse
from app.services.repositories import Repository

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_auth)])


@router.get("/groups", response_model=list[GroupResponse])
def list_groups(repo: Repository = Depends(repository_dependency)) -> list[GroupResponse]:
    return [GroupResponse.model_validate(group, from_attributes=True) for group in repo.list_groups()]


def _change_group_state(repo: Repository, group_id: str, state: str) -> dict:
    group = repo.set_group_state(group_id, state)
    repo.log_audit(category="admin", action="set_group_state", actor="admin", payload={"group_id": group_id, "state": state})
    repo.db.commit()
    return {"group_id": group.id, "state": group.state}


@router.post("/groups/{group_id}/authorize")
def authorize_group(group_id: str, repo: Repository = Depends(repository_dependency)) -> dict:
    return _change_group_state(repo, group_id, "authorized")


@router.post("/groups/{group_id}/ingest-only")
def ingest_only_group(group_id: str, repo: Repository = Depends(repository_dependency)) -> dict:
    return _change_group_state(repo, group_id, "ingest_only")


@router.post("/groups/{group_id}/ignore")
def ignore_group(group_id: str, repo: Repository = Depends(repository_dependency)) -> dict:
    return _change_group_state(repo, group_id, "ignored")


@router.post("/reindex")
def reindex(repo: Repository = Depends(repository_dependency)) -> dict:
    groups = repo.list_groups()
    for group in groups:
        repo.ensure_ingestion_job(job_type="reindex", scope_id=group.id, details={"reason": "manual_reindex"})
    repo.db.commit()
    return {"queued_groups": [group.id for group in groups]}


@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    collection_scope: str = "global",
    classification_label: str | None = None,
    group_id: str | None = None,
    ingest_service=Depends(knowledge_dependency),
) -> dict:
    upload_dir = Path("knowledge")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / file.filename
    target.write_bytes(await file.read())
    chunk_count = ingest_service.ingest_file(
        target,
        collection_scope=collection_scope,
        classification_label=classification_label,
        group_id=group_id,
    )
    ingest_service.repository.db.commit()
    return {"file_name": file.filename, "chunk_count": chunk_count}


@router.get("/users/{user_id}/access", response_model=UserAccessResponse)
def user_access(user_id: str, repo: Repository = Depends(repository_dependency), settings=Depends(settings_dependency)) -> UserAccessResponse:
    snapshot = repo.user_access_snapshot(user_id, settings.auth_membership_ttl_days)
    return UserAccessResponse(**snapshot)


@router.get("/ingestion/health")
def ingestion_health(repo: Repository = Depends(repository_dependency)) -> dict:
    jobs = repo.get_recent_ingestion_jobs()
    return {
        "jobs": [
            {
                "id": job.id,
                "job_type": job.job_type,
                "status": job.status,
                "scope_id": job.scope_id,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
                "error": job.error,
            }
            for job in jobs
        ]
    }
