from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from app.models.entities import (
    AuditLog,
    ConversationChunk,
    Group,
    GroupMembershipObservation,
    IngestionJob,
    KnowledgeChunk,
    KnowledgeDocument,
    RawMessage,
    User,
)
from app.models.enums import AccessConfidence, GroupState
from app.schemas.signal import NormalizedSignalMessage


class Repository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_group(self, group_id: str, title: str | None) -> Group:
        group = self.db.get(Group, group_id)
        if group is None:
            group = Group(id=group_id, title=title, state=GroupState.INGEST_ONLY.value)
            self.db.add(group)
            self.db.flush()
        else:
            group.title = title or group.title
        group.last_seen_at = datetime.now(timezone.utc)
        return group

    def upsert_user(self, user_id: str, display_name: str | None) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            user = User(id=user_id, display_name=display_name)
            self.db.add(user)
            self.db.flush()
        elif display_name:
            user.display_name = display_name
        return user

    def record_membership(self, user_id: str, group_id: str, evidence: dict | None = None) -> None:
        stmt = select(GroupMembershipObservation).where(
            GroupMembershipObservation.user_id == user_id,
            GroupMembershipObservation.group_id == group_id,
        )
        observation = self.db.execute(stmt).scalar_one_or_none()
        if observation is None:
            observation = GroupMembershipObservation(
                user_id=user_id,
                group_id=group_id,
                last_seen_at=datetime.now(timezone.utc),
                confidence=AccessConfidence.MEDIUM.value,
                evidence=evidence or {},
            )
            self.db.add(observation)
        else:
            observation.last_seen_at = datetime.now(timezone.utc)
            observation.evidence = {**observation.evidence, **(evidence or {})}

    def store_raw_message(self, message: NormalizedSignalMessage, debug_storage_enabled: bool) -> RawMessage:
        model = RawMessage(
            external_message_id=message.message_id,
            dedupe_key=message.dedupe_key(),
            chat_type=message.chat_type.value,
            group_id=message.group_id,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            body=message.body,
            quoted_message_id=message.quote.message_id if message.quote else None,
            quoted_text=message.quote.text if message.quote else None,
            received_at=message.timestamp,
            raw_payload=message.raw_payload,
            stored_for_debug=debug_storage_enabled,
        )
        self.db.add(model)
        return model

    def find_raw_message_by_dedupe(self, dedupe_key: str) -> RawMessage | None:
        stmt = select(RawMessage).where(RawMessage.dedupe_key == dedupe_key)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_groups(self) -> list[Group]:
        return list(self.db.execute(select(Group).order_by(Group.last_seen_at.desc())).scalars().all())

    def set_group_state(self, group_id: str, state: str) -> Group:
        group = self.db.get(Group, group_id)
        if group is None:
            group = Group(id=group_id, state=state)
            self.db.add(group)
            self.db.flush()
        else:
            group.state = state
        return group

    def get_recent_ingestion_jobs(self, limit: int = 20) -> list[IngestionJob]:
        stmt = select(IngestionJob).order_by(desc(IngestionJob.created_at)).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create_job(self, job_type: str, scope_id: str | None, details: dict | None = None) -> IngestionJob:
        job = IngestionJob(job_type=job_type, scope_id=scope_id, details=details or {})
        self.db.add(job)
        return job

    def ensure_ingestion_job(self, job_type: str, scope_id: str | None, details: dict | None = None) -> IngestionJob | None:
        if scope_id is None:
            return None
        stmt = select(IngestionJob).where(
            IngestionJob.job_type == job_type,
            IngestionJob.scope_id == scope_id,
            IngestionJob.status.in_(["pending", "in_progress"]),
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            return existing
        return self.create_job(job_type=job_type, scope_id=scope_id, details=details)

    def claim_pending_jobs(self, limit: int = 5) -> list[IngestionJob]:
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.status == "pending")
            .order_by(IngestionJob.created_at.asc())
            .limit(limit)
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        jobs = list(self.db.execute(stmt).scalars().all())
        if not jobs:
            return []
        now = datetime.now(timezone.utc)
        for job in jobs:
            job.status = "in_progress"
            job.started_at = now
        return jobs

    def mark_job_succeeded(self, job: IngestionJob) -> None:
        job.status = "succeeded"
        job.finished_at = datetime.now(timezone.utc)

    def mark_job_failed(self, job: IngestionJob, error: str) -> None:
        job.status = "failed"
        job.error = error[:1000]
        job.finished_at = datetime.now(timezone.utc)

    def create_chunk(
        self,
        group_id: str,
        content: str,
        source_message_ids: list[int],
        sender_ids: list[str],
        start_time,
        end_time,
        metadata_json: dict,
        embedding: list[float] | None,
    ) -> ConversationChunk:
        chunk = ConversationChunk(
            group_id=group_id,
            scope=f"group:{group_id}",
            content=content,
            source_message_ids=source_message_ids,
            sender_ids=sender_ids,
            start_time=start_time,
            end_time=end_time,
            metadata_json=metadata_json,
            embedding=embedding,
        )
        self.db.add(chunk)
        return chunk

    def list_group_messages_without_chunks(self, group_id: str, limit: int = 50) -> list[RawMessage]:
        stmt = (
            select(RawMessage)
            .where(RawMessage.group_id == group_id, RawMessage.chat_type == "group")
            .where(RawMessage.chunked_at.is_(None))
            .order_by(RawMessage.received_at.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def search_chunks(self, group_ids: list[str]) -> list[ConversationChunk]:
        stmt = (
            select(ConversationChunk)
            .where(ConversationChunk.group_id.in_(group_ids))
            .order_by(ConversationChunk.end_time.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search_chunks_by_embedding(
        self,
        query_embedding: list[float],
        group_ids: list[str],
        sender_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 5,
    ) -> list[tuple[ConversationChunk, float]]:
        if not group_ids:
            return []
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            score_expr = (1 - ConversationChunk.embedding.cosine_distance(query_embedding)).label("score")
            stmt = select(ConversationChunk, score_expr).where(ConversationChunk.group_id.in_(group_ids))
            if start_time is not None:
                stmt = stmt.where(ConversationChunk.end_time >= start_time)
            if end_time is not None:
                stmt = stmt.where(ConversationChunk.start_time <= end_time)
            stmt = stmt.order_by(score_expr.desc()).limit(limit * 5)
            rows = [
                (chunk, float(score or 0.0))
                for chunk, score in self.db.execute(stmt).all()
                if sender_id is None or sender_id in chunk.sender_ids
            ]
            return rows[:limit]

        rows = self.search_chunks(group_ids)
        filtered = []
        for chunk in rows:
            if start_time and chunk.end_time and chunk.end_time < start_time:
                continue
            if end_time and chunk.start_time and chunk.start_time > end_time:
                continue
            if sender_id and sender_id not in chunk.sender_ids:
                continue
            filtered.append((chunk, chunk.embedding))
        return [(chunk, 0.0) for chunk, _ in filtered]

    def clear_chunks_for_group(self, group_id: str) -> None:
        stmt = delete(ConversationChunk).where(ConversationChunk.group_id == group_id)
        self.db.execute(stmt)

    def reset_chunked_messages(self, group_id: str) -> None:
        stmt = (
            update(RawMessage)
            .where(RawMessage.group_id == group_id, RawMessage.chat_type == "group")
            .values(chunked_at=None)
        )
        self.db.execute(stmt)

    def mark_messages_chunked(self, message_ids: list[int]) -> None:
        if not message_ids:
            return
        stmt = (
            update(RawMessage)
            .where(RawMessage.id.in_(message_ids))
            .values(chunked_at=datetime.now(timezone.utc))
        )
        self.db.execute(stmt)

    def add_knowledge_document(
        self,
        file_name: str,
        source_type: str,
        classification_label: str | None,
        collection_scope: str,
        content: str,
        metadata_json: dict,
        group_id: str | None = None,
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            file_name=file_name,
            source_type=source_type,
            classification_label=classification_label,
            collection_scope=collection_scope,
            content=content,
            metadata_json=metadata_json,
            group_id=group_id,
        )
        self.db.add(doc)
        self.db.flush()
        return doc

    def add_knowledge_chunk(
        self,
        document_id: int,
        collection_scope: str,
        content: str,
        metadata_json: dict,
        embedding: list[float] | None,
        group_id: str | None = None,
    ) -> KnowledgeChunk:
        chunk = KnowledgeChunk(
            document_id=document_id,
            collection_scope=collection_scope,
            group_id=group_id,
            content=content,
            metadata_json=metadata_json,
            embedding=embedding,
        )
        self.db.add(chunk)
        return chunk

    def search_knowledge(self, scopes: list[str], group_ids: list[str]) -> list[KnowledgeChunk]:
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.collection_scope.in_(scopes))
        rows = list(self.db.execute(stmt).scalars().all())
        return [
            row
            for row in rows
            if row.collection_scope != "group" or (row.group_id is not None and row.group_id in group_ids)
        ]

    def search_knowledge_by_embedding(
        self,
        query_embedding: list[float],
        scopes: list[str],
        group_ids: list[str],
        limit: int = 5,
    ) -> list[tuple[KnowledgeChunk, float]]:
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            score_expr = (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding)).label("score")
            stmt = (
                select(KnowledgeChunk, score_expr)
                .where(KnowledgeChunk.collection_scope.in_(scopes))
                .order_by(score_expr.desc())
            )
            rows = [
                (chunk, float(score or 0.0))
                for chunk, score in self.db.execute(stmt.limit(limit * 3)).all()
                if chunk.collection_scope != "group" or (chunk.group_id is not None and chunk.group_id in group_ids)
            ]
            return rows[:limit]

        rows = self.search_knowledge(scopes, group_ids)
        return [(row, 0.0) for row in rows]

    def user_access_snapshot(self, user_id: str, membership_ttl_days: int) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=membership_ttl_days)
        stmt = (
            select(GroupMembershipObservation, Group)
            .join(Group, Group.id == GroupMembershipObservation.group_id)
            .where(
                GroupMembershipObservation.user_id == user_id,
                GroupMembershipObservation.last_seen_at >= cutoff,
            )
        )
        rows = self.db.execute(stmt).all()
        authorized = [group.id for _, group in rows if group.state == GroupState.AUTHORIZED.value]
        ingest_only = [group.id for _, group in rows if group.state == GroupState.INGEST_ONLY.value]
        confidence = AccessConfidence.LOW.value
        if authorized:
            confidence = AccessConfidence.HIGH.value
        elif ingest_only:
            confidence = AccessConfidence.MEDIUM.value
        return {
            "user_id": user_id,
            "eligible": bool(authorized),
            "authorized_group_ids": authorized,
            "ingest_only_group_ids": ingest_only,
            "confidence": confidence,
        }

    def log_audit(self, category: str, action: str, actor: str | None, payload: dict) -> None:
        self.db.add(AuditLog(category=category, action=action, actor=actor, payload=payload))
