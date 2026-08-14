from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Comment, Post, Tag

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2", "first_name", "last_name")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords must match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        extra = {}
        if "name" in {f.name for f in User._meta.get_fields()}:
            extra["name"] = validated_data.get("first_name") or validated_data["username"]
        return User.objects.create_user(**validated_data, **extra)


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "color", "post_count")
        read_only_fields = ("slug",)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("slug",)


class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "author",
            "parent",
            "body",
            "is_approved",
            "created_at",
            "replies",
        )
        read_only_fields = ("is_approved", "created_at")

    def get_replies(self, obj):
        if obj.parent_id:
            return []
        qs = obj.replies.filter(is_deleted=False, is_approved=True)
        return CommentSerializer(qs, many=True, context=self.context).data

    def validate_parent(self, parent):
        if parent and parent.parent_id:
            raise serializers.ValidationError("Replies can only be one level deep.")
        return parent


class PostListSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="post-detail", lookup_field="slug")

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "author",
            "categories",
            "tags",
            "status",
            "featured",
            "published_at",
            "reading_time",
            "view_count",
            "likes_count",
            "comments_count",
            "url",
        )


class PostDetailSerializer(PostListSerializer):
    content = serializers.CharField()
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
    )
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=40),
        write_only=True,
        required=False,
    )
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            "content",
            "allow_comments",
            "meta_title",
            "meta_description",
            "category_ids",
            "tag_names",
            "is_liked",
            "is_bookmarked",
            "comments",
        )

    def get_is_liked(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_is_bookmarked(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.bookmarks.filter(user=user).exists()

    def get_comments(self, obj):
        roots = obj.comments.filter(parent__isnull=True, is_deleted=False, is_approved=True)
        return CommentSerializer(roots, many=True, context=self.context).data

    def _apply_tags(self, post, tag_names):
        if tag_names is None:
            return
        tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        post.tags.set(tags)

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        post = super().create(validated_data)
        self._apply_tags(post, tag_names)
        return post

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        post = super().update(instance, validated_data)
        self._apply_tags(post, tag_names)
        return post
