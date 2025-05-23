
import asyncio
import logging
import os

from django.core.asgi import get_asgi_application

from . import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capsul.server.settings')

logger = logging.getLogger(__name__)

_started = False

class PostStartupMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        global _started
        if not _started:
            _started = True
            asyncio.create_task(self.run_after_startup(f"{os.environ['BASE_URL']}?capsul_token={settings.SECRET_KEY}"))
        await self.app(scope, receive, send)

    async def run_after_startup(self, url):
        from . import settings
        await asyncio.sleep(0.1)  # Laisse Uvicorn terminer sa sortie console
        print(f"✅ Serveur prêt: {url}")

application = PostStartupMiddleware(get_asgi_application())

