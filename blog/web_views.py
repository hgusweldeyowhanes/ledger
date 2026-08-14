from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView

from .forms import CommentForm, PostForm, RegisterForm
from .models import Bookmark, Category, Comment, Post, PostLike, Tag


def _annotated_posts(user):
    return (
        Post.objects.visible_to(user)
        .select_related("author")
        .prefetch_related("categories", "tags")
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count(
                "comments",
                filter=Q(comments__is_approved=True, comments__is_deleted=False),
                distinct=True,
            ),
        )
        .distinct()
        .order_by("-published_at", "-created_at")
    )


class HomeView(ListView):
    template_name = "blog/home.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        return _annotated_posts(self.request.user).published()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        published = Post.objects.published()
        ctx["featured"] = (
            _annotated_posts(self.request.user).published().filter(featured=True)[:1]
        )
        ctx["trending"] = published.order_by("-view_count")[:5]
        return ctx


class PostDetailView(DetailView):
    template_name = "blog/post_detail.html"
    slug_field = "slug"
    context_object_name = "post"

    def get_queryset(self):
        return _annotated_posts(self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        Post.objects.filter(pk=obj.pk).update(view_count=obj.view_count + 1)
        obj.view_count += 1
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = ctx["post"]
        ctx["comment_form"] = CommentForm()
        ctx["comments"] = post.comments.filter(
            parent__isnull=True, is_deleted=False, is_approved=True
        ).select_related("author").prefetch_related("replies__author")
        ctx["related"] = post.related_posts()
        user = self.request.user
        ctx["is_liked"] = user.is_authenticated and post.likes.filter(user=user).exists()
        ctx["is_bookmarked"] = user.is_authenticated and post.bookmarks.filter(user=user).exists()
        ctx["likes_count"] = post.likes.count()
        return ctx


class CategoryView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return _annotated_posts(self.request.user).published().filter(categories=self.category)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = self.category.name
        ctx["subheading"] = self.category.description
        return ctx


class TagView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def dispatch(self, request, *args, **kwargs):
        self.tag = get_object_or_404(Tag, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return _annotated_posts(self.request.user).published().filter(tags=self.tag)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = f"#{self.tag.name}"
        ctx["subheading"] = "Stories tagged with this topic"
        return ctx


class SearchView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        qs = _annotated_posts(self.request.user).published()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(excerpt__icontains=q)
                | Q(content__icontains=q)
                | Q(tags__name__icontains=q)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        ctx["heading"] = "Search"
        ctx["subheading"] = f'Results for “{q}”' if q else "Type a keyword to search the archive"
        ctx["query"] = q
        return ctx


class AuthorView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        return _annotated_posts(self.request.user).published().filter(author__username=self.kwargs["username"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = self.kwargs["username"]
        ctx["subheading"] = "Published work"
        return ctx


@method_decorator(login_required, name="dispatch")
class DashboardView(ListView):
    template_name = "blog/dashboard.html"
    context_object_name = "posts"

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).prefetch_related("categories")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bookmarks"] = (
            Post.objects.published()
            .filter(bookmarks__user=self.request.user)
            .select_related("author")
        )
        return ctx


def _save_post(request, instance=None):
    form = PostForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        form.save_m2m()
        names = [n.strip() for n in form.cleaned_data.get("tag_names", "").split(",") if n.strip()]
        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        if names:
            post.tags.set(tags)
        messages.success(request, "Post saved.")
        return redirect(post.get_absolute_url() if post.is_live() else "blog:dashboard")
    if instance:
        form.fields["tag_names"].initial = ", ".join(instance.tags.values_list("name", flat=True))
    return render(request, "blog/post_form.html", {"form": form, "editing": instance is not None})


@login_required
def post_create(request):
    return _save_post(request)


@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug, is_deleted=False)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You cannot edit this post.")
    return _save_post(request, instance=post)


@login_required
def toggle_like(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return redirect(post.get_absolute_url())


@login_required
def toggle_bookmark(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    mark, created = Bookmark.objects.get_or_create(post=post, user=request.user)
    if not created:
        mark.delete()
    return redirect(post.get_absolute_url())


@login_required
def add_comment(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    if not post.allow_comments:
        messages.error(request, "Comments are closed.")
        return redirect(post.get_absolute_url())
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        parent_id = request.POST.get("parent")
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, post=post, parent__isnull=True)
            comment.parent = parent
        comment.save()
        messages.success(request, "Comment posted.")
    return redirect(post.get_absolute_url())


class BlogLoginView(LoginView):
    template_name = "blog/login.html"


class BlogLogoutView(LogoutView):
    next_page = "blog:home"
    http_method_names = ["get", "post", "options"]


def register(request):
    if request.user.is_authenticated:
        return redirect("blog:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to Ledger.")
        return redirect("blog:home")
    return render(request, "blog/register.html", {"form": form})
