"""Import all ORM models so Alembic and the app discover them."""

from doc_assistant.app.models.user import User
from doc_assistant.app.models.document import Document
from doc_assistant.app.models.chunk import Chunk
from doc_assistant.app.models.conversation import Conversation, Message

__all__ = [
    "User",
    "Document",
    "Chunk",
    "Conversation",
    "Message",
]
