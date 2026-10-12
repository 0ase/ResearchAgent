"""Optional Uvicorn entry point: evaluation.observed_app:app."""
from openai.resources.chat.completions import AsyncCompletions
from openai.resources.embeddings import AsyncEmbeddings

from backend.config import settings
from backend.core.observability import current_context
from backend.rag.vector_store import CollectionProxy
from evaluation.observer import ObservedApp, install_observers

install_observers(AsyncCompletions, AsyncEmbeddings, CollectionProxy, current_context)

from backend.main import app as backend_app  # Install before any agent creates clients.

app = ObservedApp(backend_app, retrieval_top_k=settings.retrieval_top_k)
