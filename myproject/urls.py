from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from blog.sitemaps import PostSitemap
from myproject.spa import spa_index

sitemaps = {"posts": PostSitemap}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("blog.api_urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api-auth/", include("rest_framework.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]

if settings.SERVE_SPA:
    # React SPA at site root; API/admin/media stay above.
    urlpatterns += [
        re_path(
            r"^(?!api/|admin/|media/|static/|sitemap\.xml).*$",
            spa_index,
            name="spa",
        ),
    ]
else:
    urlpatterns += [
        path("", include("blog.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
