from django.contrib.auth import get_user_model
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
    UserPublicSerializer,
    UserRegistrationSerializer,
)
from .services import confirm_subscriber, subscribe_newsletter, unsubscribe

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
        return qs.distinct().order_by("-published_at", "-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostDetailSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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
