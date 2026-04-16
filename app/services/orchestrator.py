from fastapi import BackgroundTasks

from app.core.config import Settings
from app.schemas.signal import NormalizedSignalMessage
from app.services.agent import AgentService
from app.services.memory import MemoryService
from app.services.policy_engine import PolicyEngine
from app.services.repositories import Repository
from app.services.rate_limiter import RateLimiter
from app.services.signal_gateway import SignalGateway


class InboundMessageOrchestrator:
    def __init__(
        self,
        settings: Settings,
        repository: Repository,
        policy_engine: PolicyEngine,
        memory: MemoryService,
        agent: AgentService,
        signal_gateway: SignalGateway,
        rate_limiter: RateLimiter,
    ):
        self.settings = settings
        self.repository = repository
        self.policy_engine = policy_engine
        self.memory = memory
        self.agent = agent
        self.signal_gateway = signal_gateway
        self.rate_limiter = rate_limiter

    def handle(self, message: NormalizedSignalMessage, background_tasks: BackgroundTasks | None = None) -> dict:
        if message.sender_id == self.settings.signal_bot_number:
            return {"status": "ignored", "reason": "self_message"}

        decision = self.policy_engine.evaluate(message)
        self.repository.log_audit(
            category="policy",
            action="evaluate_message",
            actor=message.sender_id,
            payload={"chat_type": message.chat_type.value, "group_id": message.group_id, "decision": decision.reason},
        )

        if decision.ingest:
            stored = self.memory.store_message(message)
            if stored and message.group_id:
                if self.settings.ingestion_worker_enabled:
                    self.repository.ensure_ingestion_job(
                        job_type="ingest_group",
                        scope_id=message.group_id,
                        details={"source": "webhook"},
                    )
                elif background_tasks:
                    background_tasks.add_task(self.memory.ingest_group_messages, message.group_id)
                else:
                    self.memory.ingest_group_messages(message.group_id)

        if message.chat_type.value == "direct":
            if not decision.respond:
                refusal = "Access is limited to members of an authorized Signal group. Contact an admin if needed."
                self.signal_gateway.send_message(recipient=message.sender_id, message=refusal)
                return {"status": "denied", "reason": decision.reason}

            if not self.rate_limiter.allow(
                key=f"dm:{message.sender_id}",
                limit=self.settings.dm_rate_limit_count,
                window_seconds=self.settings.dm_rate_limit_window_seconds,
            ):
                refusal = "Rate limit exceeded. Please wait before sending another request."
                self.signal_gateway.send_message(recipient=message.sender_id, message=refusal)
                return {"status": "rate_limited"}

            group_context = self.memory.retrieve_group_context(query=message.body, group_ids=decision.authorized_group_ids)
            knowledge_context = self.memory.retrieve_knowledge_context(
                query=message.body,
                scopes=["global", "group", "admin_only"],
                group_ids=decision.authorized_group_ids,
            )
            answer = self.agent.answer(
                question=message.body,
                group_context=group_context,
                knowledge_context=knowledge_context,
                authorized_group_ids=decision.authorized_group_ids,
                privacy_mode=self.settings.enable_dm_ephemeral_memory,
            )
            self.repository.log_audit(
                category="openai",
                action="dm_response_generated",
                actor=message.sender_id,
                payload={"usage": answer["usage"], "source_count": len(answer["sources"])},
            )
            self.signal_gateway.send_message(recipient=message.sender_id, message=answer["text"])
            if self.settings.enable_dm_storage_minimal:
                self.memory.store_message(message)
            return {"status": "replied", "sources": answer["sources"]}

        if decision.respond and message.group_id:
            if self.settings.group_auto_reply_require_question and "?" not in message.body:
                return {"status": "ingested", "reason": "group_auto_reply_skipped"}
            if not self.rate_limiter.allow(
                key=f"group:{message.group_id}",
                limit=self.settings.group_rate_limit_count,
                window_seconds=self.settings.group_rate_limit_window_seconds,
            ):
                return {"status": "rate_limited", "reason": "group_rate_limited"}
            group_context = self.memory.retrieve_group_context(query=message.body, group_ids=[message.group_id])
            knowledge_context = self.memory.retrieve_knowledge_context(
                query=message.body,
                scopes=self.settings.group_auto_reply_scopes(),
                group_ids=[message.group_id],
            )
            answer = self.agent.answer(
                question=message.body,
                group_context=group_context,
                knowledge_context=knowledge_context,
                authorized_group_ids=decision.authorized_group_ids or [message.group_id],
                privacy_mode=False,
            )
            self.repository.log_audit(
                category="openai",
                action="group_response_generated",
                actor=message.sender_id,
                payload={"usage": answer["usage"], "source_count": len(answer["sources"])},
            )
            self.signal_gateway.send_message(
                recipient=message.sender_id, message=answer["text"], group_id=message.group_id
            )
            return {"status": "replied", "sources": answer["sources"]}

        return {"status": "ingested" if decision.ingest else "ignored", "reason": decision.reason}
