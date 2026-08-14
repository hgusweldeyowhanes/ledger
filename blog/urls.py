from django.urls import path

from . import web_views
from .feeds import LatestPostsFeed

app_name = "blog"

urlpatterns = [
    path("", web_views.HomeView.as_view(), name="home"),
    path("search/", web_views.SearchView.as_view(), name="search"),
    path("write/", web_views.post_create, name="post-create"),
    path("dashboard/", web_views.DashboardView.as_view(), name="dashboard"),
    path("login/", web_views.BlogLoginView.as_view(), name="login"),
    path("logout/", web_views.BlogLogoutView.as_view(), name="logout"),
    path("register/", web_views.register, name="register"),
    path("feed.xml", LatestPostsFeed(), name="rss"),
    path("category/<slug:slug>/", web_views.CategoryView.as_view(), name="category"),
    path("tag/<slug:slug>/", web_views.TagView.as_view(), name="tag"),
    path("author/<str:username>/", web_views.AuthorView.as_view(), name="author"),
    path("post/<slug:slug>/like/", web_views.toggle_like, name="like"),
    path("post/<slug:slug>/bookmark/", web_views.toggle_bookmark, name="bookmark"),
    path("post/<slug:slug>/comment/", web_views.add_comment, name="comment"),
    path("post/<slug:slug>/edit/", web_views.post_edit, name="post-edit"),
    path("post/<slug:slug>/", web_views.PostDetailView.as_view(), name="post-detail"),
]
