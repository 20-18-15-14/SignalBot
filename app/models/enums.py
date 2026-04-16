from enum import Enum


class ChatType(str, Enum):
    GROUP = "group"
    DIRECT = "direct"


class GroupState(str, Enum):
    AUTHORIZED = "authorized"
    INGEST_ONLY = "ingest_only"
    IGNORED = "ignored"


class AccessConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeScope(str, Enum):
    GLOBAL = "global"
    GROUP = "group"
    ADMIN_ONLY = "admin_only"
