from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView

from .forms import CommentForm, NewsletterForm, PostForm, RegisterForm, SeriesForm
from .models import (
    AuthorFollow,
    Bookmark,
    Category,
    Comment,
    Notification,
    Post,
    PostRevision,
    PostLike,
    Series,
    SeriesMembership,
    Tag,
)
from .services import (
    comment_should_auto_approve,
    confirm_subscriber,
    create_post_revision,
    restore_post_revision,
    subscribe_newsletter,
    unsubscribe,
)

User = get_user_model()


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
        membership = post.series_membership()
        ctx["series_membership"] = membership
        if membership:
            siblings = list(
                SeriesMembership.objects.filter(series=membership.series)
                .select_related("post")
                .order_by("position")
            )
            idx = next((i for i, m in enumerate(siblings) if m.pk == membership.pk), None)
            ctx["series_prev"] = siblings[idx - 1].post if idx and idx > 0 else None
            ctx["series_next"] = (
                siblings[idx + 1].post if idx is not None and idx + 1 < len(siblings) else None
            )
            ctx["series"] = membership.series
        ctx["is_following_author"] = (
            user.is_authenticated
            and user.pk != post.author_id
            and AuthorFollow.objects.filter(follower=user, author=post.author).exists()
        )
        if user.is_authenticated and (user.pk == post.author_id or user.is_staff):
            ctx["pending_comments"] = post.comments.filter(
                is_approved=False, is_deleted=False
            ).count()
        ctx["absolute_url"] = self.request.build_absolute_uri(post.get_absolute_url())
        if post.cover_image:
            ctx["cover_absolute"] = self.request.build_absolute_uri(post.cover_image.url)
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
        tag = self.request.GET.get("tag", "").strip()
        category = self.request.GET.get("category", "").strip()
        min_read = self.request.GET.get("min_reading_time", "").strip()
        max_read = self.request.GET.get("max_reading_time", "").strip()
        order = self.request.GET.get("order", "").strip() or "-published_at"
        qs = _annotated_posts(self.request.user).published()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(excerpt__icontains=q)
                | Q(content__icontains=q)
                | Q(tags__name__icontains=q)
            ).distinct()
        if tag:
            qs = qs.filter(tags__slug=tag)
        if category:
            qs = qs.filter(categories__slug=category)
        if min_read.isdigit():
            qs = qs.filter(reading_time__gte=int(min_read))
        if max_read.isdigit():
            qs = qs.filter(reading_time__lte=int(max_read))
        allowed_orders = {"-published_at", "published_at", "-view_count", "-reading_time", "title"}
        if order in allowed_orders:
            qs = qs.order_by(order, "-created_at")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        ctx["heading"] = "Search"
        ctx["subheading"] = f'Results for “{q}”' if q else "Type a keyword to search the archive"
        ctx["query"] = q
        ctx["filter_tag"] = self.request.GET.get("tag", "").strip()
        ctx["filter_category"] = self.request.GET.get("category", "").strip()
        ctx["min_reading_time"] = self.request.GET.get("min_reading_time", "").strip()
        ctx["max_reading_time"] = self.request.GET.get("max_reading_time", "").strip()
        ctx["order"] = self.request.GET.get("order", "").strip() or "-published_at"
        ctx["all_tags"] = Tag.objects.all()
        ctx["all_categories"] = Category.objects.all()
        return ctx


class AuthorView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def dispatch(self, request, *args, **kwargs):
        self.author = get_object_or_404(User, username=kwargs["username"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return _annotated_posts(self.request.user).published().filter(author=self.author)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = self.author.username
        ctx["subheading"] = "Published work"
        ctx["profile_author"] = self.author
        user = self.request.user
        ctx["is_following_author"] = (
            user.is_authenticated
            and user.pk != self.author.pk
            and AuthorFollow.objects.filter(follower=user, author=self.author).exists()
        )
        ctx["follower_count"] = AuthorFollow.objects.filter(author=self.author).count()
        return ctx


@method_decorator(login_required, name="dispatch")
class FollowingFeedView(ListView):
    template_name = "blog/following.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        author_ids = AuthorFollow.objects.filter(follower=self.request.user).values_list(
            "author_id", flat=True
        )
        return _annotated_posts(self.request.user).published().filter(author_id__in=author_ids)


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
        ctx["pending_comments"] = (
            Comment.objects.filter(
                post__author=self.request.user,
                is_approved=False,
                is_deleted=False,
            )
            .select_related("author", "post")
            .order_by("-created_at")
        )
        ctx["series_list"] = Series.objects.filter(author=self.request.user)
        ctx["series_form"] = SeriesForm()
        authored = Post.objects.filter(author=self.request.user, is_deleted=False)
        published = authored.filter(status=Post.Status.PUBLISHED)
        total_views = sum(authored.values_list("view_count", flat=True))
        total_likes = PostLike.objects.filter(post__author=self.request.user).count()
        total_bookmarks = Bookmark.objects.filter(post__author=self.request.user).count()
        total_comments = Comment.objects.filter(
            post__author=self.request.user, is_approved=True, is_deleted=False
        ).count()
        total_followers = AuthorFollow.objects.filter(author=self.request.user).count()
        total_read_time = sum(
            (p.view_count or 0) * (p.reading_time or 1) for p in authored.only("view_count", "reading_time")
        )
        ctx["analytics"] = {
            "total_posts": authored.count(),
            "published_posts": published.count(),
            "total_views": total_views,
            "total_read_time_minutes": total_read_time,
            "avg_reading_time": round(
                sum(authored.values_list("reading_time", flat=True)) / max(1, authored.count()), 1
            ),
            "total_likes": total_likes,
            "total_bookmarks": total_bookmarks,
            "total_comments": total_comments,
            "total_followers": total_followers,
            "engagement_rate": (
                round(((total_likes + total_bookmarks + total_comments) / max(total_views, 1)) * 100, 1)
                if total_views > 0
                else 0.0
            ),
        }
        ctx["recent_revisions"] = (
            PostRevision.objects.filter(post__author=self.request.user)
            .select_related("post", "edited_by")
            .order_by("-created_at")[:12]
        )
        return ctx


@method_decorator(login_required, name="dispatch")
class NotificationListView(ListView):
    template_name = "blog/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("actor", "post", "comment")
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.GET.get("mark") == "all":
            Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
            return redirect("blog:notifications")
        return response


class SeriesListView(ListView):
    template_name = "blog/series_list.html"
    context_object_name = "series_list"
    paginate_by = 12

    def get_queryset(self):
        return Series.objects.select_related("author").annotate(
            post_count=Count("memberships", distinct=True)
        )


class SeriesDetailView(DetailView):
    template_name = "blog/series_detail.html"
    model = Series
    context_object_name = "series"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        memberships = (
            SeriesMembership.objects.filter(series=self.object)
            .select_related("post", "post__author")
            .order_by("position")
        )
        ctx["memberships"] = memberships
        return ctx


def _save_post(request, instance=None):
    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        if instance is not None:
            create_post_revision(instance, edited_by=request.user)
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
        series = form.cleaned_data.get("series")
        position = form.cleaned_data.get("series_position") or 1
        SeriesMembership.objects.filter(post=post).delete()
        if series and series.author_id == request.user.pk:
            while SeriesMembership.objects.filter(series=series, position=position).exists():
                position += 1
            SeriesMembership.objects.create(series=series, post=post, position=position)
        messages.success(request, "Post saved.")
        return redirect(post.get_absolute_url() if post.is_live() else "blog:dashboard")
    if instance:
        form.fields["tag_names"].initial = ", ".join(instance.tags.values_list("name", flat=True))
        membership = instance.series_membership()
        if membership:
            form.fields["series"].initial = membership.series_id
            form.fields["series_position"].initial = membership.position
    context = {"form": form, "editing": instance is not None}
    if instance is not None:
        context["revisions"] = instance.revisions.select_related("edited_by")[:10]
    return render(request, "blog/post_form.html", context)


@login_required
def rollback_post_revision(request, slug, revision_id):
    post = get_object_or_404(Post, slug=slug, is_deleted=False)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You cannot edit this post.")
    if request.method != "POST":
        return redirect("blog:post-edit", slug=slug)
    revision = get_object_or_404(PostRevision, pk=revision_id, post=post)
    create_post_revision(post, edited_by=request.user)
    restore_post_revision(post, revision)
    messages.success(request, "Post reverted to selected revision.")
    return redirect("blog:post-edit", slug=slug)


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
        comment.is_approved = comment_should_auto_approve(request.user, post)
        parent_id = request.POST.get("parent")
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, post=post, parent__isnull=True)
            comment.parent = parent
        comment.save()
        if comment.is_approved:
            messages.success(request, "Comment posted.")
        else:
            messages.success(request, "Comment submitted for review.")
    return redirect(post.get_absolute_url())


@login_required
def toggle_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author.pk == request.user.pk:
        messages.error(request, "You cannot follow yourself.")
        return redirect("blog:author", username=username)
    follow, created = AuthorFollow.objects.get_or_create(follower=request.user, author=author)
    if not created:
        follow.delete()
        messages.info(request, f"Unfollowed {author.username}.")
    else:
        messages.success(request, f"Following {author.username}.")
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("blog:author", username=username)


def newsletter_subscribe(request):
    if request.method != "POST":
        return redirect("blog:home")
    form = NewsletterForm(request.POST)
    if form.is_valid():
        _, state = subscribe_newsletter(form.cleaned_data["email"], request)
        if state == "already":
            messages.info(request, "You are already subscribed.")
        else:
            messages.success(request, "Check your email to confirm the subscription.")
    else:
        messages.error(request, "Enter a valid email address.")
    return redirect(request.POST.get("next") or "blog:home")


def newsletter_confirm(request, token):
    sub = confirm_subscriber(token)
    if sub:
        messages.success(request, "You are subscribed to the Ledger newsletter.")
    else:
        messages.error(request, "Invalid or expired confirmation link.")
    return redirect("blog:home")


def newsletter_unsubscribe(request, token):
    sub = unsubscribe(token)
    if sub:
        messages.info(request, "You have been unsubscribed.")
    else:
        messages.error(request, "Invalid unsubscribe link.")
    return redirect("blog:home")


@login_required
def moderate_comment(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related("post"),
        pk=comment_id,
        post__author=request.user,
        is_deleted=False,
    )
    action = request.POST.get("action")
    if action == "approve":
        comment.is_approved = True
        comment.save(update_fields=["is_approved", "updated_at"])
        messages.success(request, "Comment approved.")
    elif action == "reject":
        comment.is_deleted = True
        comment.save(update_fields=["is_deleted", "updated_at"])
        messages.info(request, "Comment rejected.")
    return redirect(request.POST.get("next") or "blog:dashboard")


@login_required
def series_create(request):
    form = SeriesForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        series = form.save(commit=False)
        series.author = request.user
        series.save()
        messages.success(request, "Series created.")
        return redirect(series.get_absolute_url())
    return redirect("blog:dashboard")


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
