from django.urls import path

from . import web_views
from .feeds import LatestPostsFeed

app_name = "blog"

urlpatterns = [
    path("", web_views.HomeView.as_view(), name="home"),
    path("search/", web_views.SearchView.as_view(), name="search"),
    path("write/", web_views.post_create, name="post-create"),
    path("dashboard/", web_views.DashboardView.as_view(), name="dashboard"),
    path("following/", web_views.FollowingFeedView.as_view(), name="following"),
    path("notifications/", web_views.NotificationListView.as_view(), name="notifications"),
    path("series/", web_views.SeriesListView.as_view(), name="series-list"),
    path("series/create/", web_views.series_create, name="series-create"),
    path("series/<slug:slug>/", web_views.SeriesDetailView.as_view(), name="series-detail"),
    path("login/", web_views.BlogLoginView.as_view(), name="login"),
    path("logout/", web_views.BlogLogoutView.as_view(), name="logout"),
    path("register/", web_views.register, name="register"),
    path("feed.xml", LatestPostsFeed(), name="rss"),
    path("newsletter/subscribe/", web_views.newsletter_subscribe, name="newsletter-subscribe"),
    path("newsletter/confirm/<str:token>/", web_views.newsletter_confirm, name="newsletter-confirm"),
    path(
        "newsletter/unsubscribe/<str:token>/",
        web_views.newsletter_unsubscribe,
        name="newsletter-unsubscribe",
    ),
    path("category/<slug:slug>/", web_views.CategoryView.as_view(), name="category"),
    path("tag/<slug:slug>/", web_views.TagView.as_view(), name="tag"),
    path("author/<str:username>/", web_views.AuthorView.as_view(), name="author"),
    path("author/<str:username>/follow/", web_views.toggle_follow, name="follow"),
    path("post/<slug:slug>/like/", web_views.toggle_like, name="like"),
    path("post/<slug:slug>/bookmark/", web_views.toggle_bookmark, name="bookmark"),
    path("post/<slug:slug>/comment/", web_views.add_comment, name="comment"),
    path("post/<slug:slug>/edit/", web_views.post_edit, name="post-edit"),
    path("post/<slug:slug>/", web_views.PostDetailView.as_view(), name="post-detail"),
    path("comments/<int:comment_id>/moderate/", web_views.moderate_comment, name="moderate-comment"),
]
