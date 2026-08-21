from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache


def _index_path():
    return Path(settings.BASE_DIR) / "frontend" / "dist" / "index.html"


@never_cache
def spa_index(request, path=""):
    """Serve the React build for client-side routes."""
    index = _index_path()
    if not index.exists():
        raise Http404(
            "React build not found. Run: cd frontend && npm ci && npm run build"
        )
    return FileResponse(index.open("rb"), content_type="text/html")
