from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .feeds import LatestPostsFeed
from .views import (
    CategoryViewSet,
    CommentViewSet,
    MeView,
    PostViewSet,
    RegisterView,
    TagViewSet,
)

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="api-register"),
    path("me/", MeView.as_view(), name="api-me"),
    path("feed/", LatestPostsFeed(), name="api-rss"),
    path("", include(router.urls)),
]
