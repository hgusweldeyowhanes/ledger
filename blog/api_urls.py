from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .feeds import LatestPostsFeed
from .views import (
    CategoryViewSet,
    CommentViewSet,
    MeView,
    NotificationViewSet,
    PostViewSet,
    RegisterView,
    SeriesViewSet,
    TagViewSet,
    following_feed_api,
    newsletter_confirm_api,
    newsletter_subscribe_api,
    newsletter_unsubscribe_api,
    toggle_follow_api,
)

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")
router.register("series", SeriesViewSet, basename="series")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="api-register"),
    path("me/", MeView.as_view(), name="api-me"),
    path("feed/", LatestPostsFeed(), name="api-rss"),
    path("feed/following/", following_feed_api, name="api-following-feed"),
    path("newsletter/subscribe/", newsletter_subscribe_api, name="api-newsletter-subscribe"),
    path("newsletter/confirm/<str:token>/", newsletter_confirm_api, name="api-newsletter-confirm"),
    path(
        "newsletter/unsubscribe/<str:token>/",
        newsletter_unsubscribe_api,
        name="api-newsletter-unsubscribe",
    ),
    path("authors/<str:username>/follow/", toggle_follow_api, name="api-follow"),
    path("", include(router.urls)),
]
