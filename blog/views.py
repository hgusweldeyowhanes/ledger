from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Bookmark, Category, Comment, Post, PostLike, Tag
from .permissions import IsAuthorOrReadOnly, IsStaffOrReadOnly
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    PostDetailSerializer,
    PostListSerializer,
    TagSerializer,
    UserPublicSerializer,
    UserRegistrationSerializer,
)


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
    filterset_fields = ["status", "featured", "author", "categories__slug", "tags__slug"]

    def get_queryset(self):
        qs = (
            Post.objects.visible_to(self.request.user)
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


class CommentViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    throttle_classes = [CommentThrottle]
    filterset_fields = ["post", "author"]

    def get_queryset(self):
        return (
            Comment.objects.filter(is_deleted=False, is_approved=True)
            .select_related("author", "post")
            .prefetch_related("replies")
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])


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
