from django.contrib.auth import get_user_model
from django.db.models import Avg, Sum
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

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
    Tag,
)
from .permissions import IsAuthorOrReadOnly, IsStaffOrReadOnly
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    NewsletterSubscribeSerializer,
    NotificationSerializer,
    PostDetailSerializer,
    PostListSerializer,
    SeriesSerializer,
    SeriesWriteSerializer,
    TagSerializer,
    PostRevisionSerializer,
    UserPublicSerializer,
    UserRegistrationSerializer,
)
from .services import (
    confirm_subscriber,
    create_post_revision,
    restore_post_revision,
    subscribe_newsletter,
    unsubscribe,
)

User = get_user_model()


class CommentThrottle(UserRateThrottle):
    scope = "comment"


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserPublicSerializer(user).data,
                "token": token.key,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveAPIView):
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "excerpt", "content", "tags__name", "categories__name"]
    ordering_fields = ["published_at", "title", "view_count", "reading_time"]
    filterset_fields = ["status", "featured", "author", "author__username", "categories__slug", "tags__slug"]

    def get_queryset(self):
        qs = (
            Post.objects.visible_to(self.request.user)
            .select_related("author")
            .prefetch_related("categories", "tags", "series_memberships__series")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count(
                    "comments",
                    filter=Q(comments__is_approved=True, comments__is_deleted=False),
                    distinct=True,
                ),
            )
        )
        qp = self.request.query_params
        min_read = qp.get("min_reading_time")
        max_read = qp.get("max_reading_time")
        published_after = qp.get("published_after")
        published_before = qp.get("published_before")
        has_cover = qp.get("has_cover")

        if min_read and str(min_read).isdigit():
            qs = qs.filter(reading_time__gte=int(min_read))
        if max_read and str(max_read).isdigit():
            qs = qs.filter(reading_time__lte=int(max_read))
        if published_after:
            qs = qs.filter(published_at__date__gte=published_after)
        if published_before:
            qs = qs.filter(published_at__date__lte=published_before)
        if has_cover in {"true", "1"}:
            qs = qs.exclude(cover_image__isnull=True).exclude(cover_image="")
        elif has_cover in {"false", "0"}:
            qs = qs.filter(Q(cover_image__isnull=True) | Q(cover_image=""))
        return qs.distinct().order_by("-published_at", "-created_at")

    def get_serializer_class(self):
        if self.action in {"list", "trending"}:
            return PostListSerializer
        return PostDetailSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        post = self.get_object()
        create_post_revision(post, edited_by=self.request.user)
        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Post.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        instance.view_count += 1
        serializer = self.get_serializer(instance)
        data = serializer.data
        data["related"] = PostListSerializer(
            instance.related_posts(),
            many=True,
            context={"request": request},
        ).data
        return Response(data)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def trending(self, request):
        qs = self.get_queryset().order_by("-view_count", "-published_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def publish(self, request, slug=None):
        post = self.get_object()
        post.status = Post.Status.PUBLISHED
        if post.published_at > timezone.now():
            post.published_at = timezone.now()
        post.save(update_fields=["status", "published_at", "updated_at"])
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, slug=None):
        post = self.get_object()
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({"liked": False, "likes_count": post.likes.count()})
        return Response({"liked": True, "likes_count": post.likes.count()})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, slug=None):
        post = self.get_object()
        mark, created = Bookmark.objects.get_or_create(post=post, user=request.user)
        if not created:
            mark.delete()
            return Response({"bookmarked": False})
        return Response({"bookmarked": True})

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        qs = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(qs)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def saved(self, request):
        qs = self.get_queryset().filter(bookmarks__user=request.user)
        page = self.paginate_queryset(qs)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="feed/following", permission_classes=[permissions.IsAuthenticated])
    def following_feed(self, request):
        author_ids = AuthorFollow.objects.filter(follower=request.user).values_list("author_id", flat=True)
        qs = self.get_queryset().filter(author_id__in=author_ids, status=Post.Status.PUBLISHED)
        page = self.paginate_queryset(qs)
        serializer = PostListSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def analytics(self, request):
        posts = Post.objects.filter(author=request.user, is_deleted=False)
        published = posts.filter(status=Post.Status.PUBLISHED, published_at__lte=timezone.now())
        totals = posts.aggregate(
            total_posts=Count("id"),
            total_views=Sum("view_count"),
            avg_reading_time=Avg("reading_time"),
        )
        total_views = totals["total_views"] or 0
        total_posts = totals["total_posts"] or 0
        published_count = published.count()
        drafts_count = posts.filter(status=Post.Status.DRAFT).count()
        avg_reading_time = round(float(totals["avg_reading_time"] or 0), 1)

        # Total read time delivered across all views
        total_read_time_minutes = sum(
            (p.view_count or 0) * (p.reading_time or 1) for p in posts.only("view_count", "reading_time")
        )

        # Engagements
        total_likes = PostLike.objects.filter(post__author=request.user).count()
        total_bookmarks = Bookmark.objects.filter(post__author=request.user).count()
        total_comments = Comment.objects.filter(
            post__author=request.user, is_approved=True, is_deleted=False
        ).count()
        total_followers = AuthorFollow.objects.filter(author=request.user).count()

        total_engagements = total_likes + total_bookmarks + total_comments
        engagement_rate = (
            round((total_engagements / max(total_views, 1)) * 100, 1) if total_views > 0 else 0.0
        )

        # Annotated posts query for breakdowns
        posts_annotated = (
            posts.annotate(
                likes_count=Count("likes", distinct=True),
                bookmarks_count=Count("bookmarks", distinct=True),
                comments_count=Count(
                    "comments",
                    filter=Q(comments__is_approved=True, comments__is_deleted=False),
                    distinct=True,
                ),
            )
            .order_by("-view_count", "-likes_count")
        )

        top_posts_qs = posts_annotated.filter(status=Post.Status.PUBLISHED)[:5]
        top_posts_data = [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "view_count": p.view_count,
                "likes_count": p.likes_count,
                "bookmarks_count": p.bookmarks_count,
                "comments_count": p.comments_count,
                "reading_time": p.reading_time,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "engagement_rate": (
                    round(((p.likes_count + p.bookmarks_count + p.comments_count) / max(p.view_count, 1)) * 100, 1)
                    if p.view_count > 0 else 0.0
                ),
            }
            for p in top_posts_qs
        ]

        # Full catalog breakdown
        posts_breakdown = [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "status": p.status,
                "view_count": p.view_count,
                "likes_count": p.likes_count,
                "bookmarks_count": p.bookmarks_count,
                "comments_count": p.comments_count,
                "reading_time": p.reading_time,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "engagement_rate": (
                    round(((p.likes_count + p.bookmarks_count + p.comments_count) / max(p.view_count, 1)) * 100, 1)
                    if p.view_count > 0 else 0.0
                ),
            }
            for p in posts_annotated.order_by("-published_at", "-created_at")
        ]

        # Category distribution
        category_map = {}
        for p in published.prefetch_related("categories"):
            for cat in p.categories.all():
                if cat.id not in category_map:
                    category_map[cat.id] = {
                        "id": cat.id,
                        "name": cat.name,
                        "slug": cat.slug,
                        "color": cat.color,
                        "posts_count": 0,
                        "total_views": 0,
                    }
                category_map[cat.id]["posts_count"] += 1
                category_map[cat.id]["total_views"] += p.view_count

        category_distribution = sorted(
            category_map.values(), key=lambda x: x["total_views"], reverse=True
        )
        for cat in category_distribution:
            cat["percentage"] = (
                round((cat["total_views"] / max(total_views, 1)) * 100, 1) if total_views > 0 else 0.0
            )

        # Monthly trends (last 6 calendar months)
        now = timezone.now()
        monthly_trends = []
        for i in range(5, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_posts = published.filter(published_at__year=year, published_at__month=month)
            month_views = month_posts.aggregate(v=Sum("view_count"))["v"] or 0
            monthly_trends.append({
                "label": f"{year}-{month:02d}",
                "month_name": timezone.datetime(year, month, 1).strftime("%b %Y"),
                "posts_count": month_posts.count(),
                "views": month_views,
            })

        # Recent reader interactions
        recent_notifs = Notification.objects.filter(recipient=request.user).select_related("actor", "post")[:10]
        recent_activity = [
            {
                "id": n.id,
                "verb": n.verb,
                "actor_username": n.actor.username if n.actor else "A reader",
                "post_title": n.post.title if n.post else None,
                "post_slug": n.post.slug if n.post else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in recent_notifs
        ]

        return Response(
            {
                "totals": {
                    "posts": total_posts,
                    "published_posts": published_count,
                    "drafts_count": drafts_count,
                    "views": total_views,
                    "total_read_time_minutes": total_read_time_minutes,
                    "avg_reading_time": avg_reading_time,
                    "likes": total_likes,
                    "bookmarks": total_bookmarks,
                    "comments": total_comments,
                    "followers": total_followers,
                    "engagement_rate": engagement_rate,
                },
                "top_posts": top_posts_data,
                "posts_breakdown": posts_breakdown,
                "category_distribution": category_distribution,
                "monthly_trends": monthly_trends,
                "recent_activity": recent_activity,
            }
        )

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def revisions(self, request, slug=None):
        post = self.get_object()
        if post.author_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        rows = PostRevision.objects.filter(post=post).select_related("edited_by")
        page = self.paginate_queryset(rows)
        serializer = PostRevisionSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def rollback(self, request, slug=None):
        post = self.get_object()
        if post.author_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        revision_id = request.data.get("revision_id")
        if not revision_id:
            return Response({"detail": "revision_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        revision = get_object_or_404(PostRevision, pk=revision_id, post=post)
        create_post_revision(post, edited_by=request.user)
        restore_post_revision(post, revision)
        return Response(self.get_serializer(post).data)


class CommentViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    throttle_classes = [CommentThrottle]
    filterset_fields = ["post", "author"]

    def get_queryset(self):
        if self.action == "pending":
            return (
                Comment.objects.filter(
                    is_deleted=False,
                    is_approved=False,
                    post__author=self.request.user,
                )
                .select_related("author", "post")
                .order_by("-created_at")
            )
        return (
            Comment.objects.filter(is_deleted=False, is_approved=True)
            .select_related("author", "post")
            .prefetch_related("replies")
        )

    def perform_create(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def pending(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        serializer = CommentSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        comment = get_object_or_404(Comment, pk=pk, is_deleted=False)
        if comment.post.author_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        comment.is_approved = True
        comment.save(update_fields=["is_approved", "updated_at"])
        return Response(CommentSerializer(comment, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        comment = get_object_or_404(Comment, pk=pk, is_deleted=False)
        if comment.post.author_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        comment.is_deleted = True
        comment.save(update_fields=["is_deleted", "updated_at"])
        return Response({"detail": "rejected"})


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = "slug"
    queryset = Category.objects.annotate(post_count=Count("posts", distinct=True))


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    lookup_field = "slug"
    queryset = Tag.objects.all()
    search_fields = ["name"]


class SeriesViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        return (
            Series.objects.select_related("author")
            .prefetch_related("memberships__post")
            .annotate(post_count=Count("memberships", distinct=True))
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SeriesWriteSerializer
        return SeriesSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "actor", "post", "comment"
        )

    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "ok"})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def newsletter_subscribe_api(request):
    ser = NewsletterSubscribeSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    _, state = subscribe_newsletter(ser.validated_data["email"], request)
    return Response({"status": state}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def newsletter_confirm_api(request, token):
    sub = confirm_subscriber(token)
    if not sub:
        return Response({"detail": "Invalid token."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"status": "confirmed", "email": sub.email})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def newsletter_unsubscribe_api(request, token):
    sub = unsubscribe(token)
    if not sub:
        return Response({"detail": "Invalid token."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"status": "unsubscribed", "email": sub.email})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def following_feed_api(request):
    author_ids = AuthorFollow.objects.filter(follower=request.user).values_list("author_id", flat=True)
    qs = (
        Post.objects.published()
        .filter(author_id__in=author_ids)
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
        .order_by("-published_at")
    )
    from rest_framework.pagination import PageNumberPagination

    paginator = PageNumberPagination()
    page_qs = paginator.paginate_queryset(qs, request)
    ser = PostListSerializer(page_qs, many=True, context={"request": request})
    return paginator.get_paginated_response(ser.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def toggle_follow_api(request, username):
    author = get_object_or_404(User, username=username)
    if author.pk == request.user.pk:
        return Response({"detail": "Cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)
    follow, created = AuthorFollow.objects.get_or_create(follower=request.user, author=author)
    if not created:
        follow.delete()
        return Response({"following": False})
    return Response({"following": True})
