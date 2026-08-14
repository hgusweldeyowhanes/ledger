from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .managers import PostManager


def cover_upload_to(instance, filename):
    return f"blog/covers/{instance.slug or 'draft'}/{filename}"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.CharField(max_length=240, blank=True)
    color = models.CharField(max_length=7, default="#c9a227")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Tag(TimeStampedModel):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:tag", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(max_length=320, blank=True)
    content = models.TextField(help_text="Markdown is supported.")
    cover_image = models.ImageField(upload_to=cover_upload_to, blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_posts",
    )
    categories = models.ManyToManyField(Category, related_name="posts", blank=True)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    reading_time = models.PositiveSmallIntegerField(default=1)
    view_count = models.PositiveIntegerField(default=0)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    is_deleted = models.BooleanField(default=False)

    objects = PostManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["featured", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug(slugify(self.title) or "post")
        words = len((self.content or "").split())
        self.reading_time = max(1, round(words / 200)) or 1
        if not self.excerpt:
            self.excerpt = (self.content or "")[:280]
        if not self.meta_title:
            self.meta_title = self.title[:70]
        if not self.meta_description:
            self.meta_description = self.excerpt[:160]
        super().save(*args, **kwargs)

    def _unique_slug(self, base):
        slug = base
        n = 2
        qs = Post.all_objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def is_live(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.published_at <= timezone.now()
            and not self.is_deleted
        )

    def get_absolute_url(self):
        return reverse("blog:post-detail", kwargs={"slug": self.slug})

    def related_posts(self, limit=3):
        return (
            Post.objects.published()
            .filter(categories__in=self.categories.all())
            .exclude(pk=self.pk)
            .distinct()[:limit]
        )

    def __str__(self):
        return self.title


class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.post}"


class PostLike(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_likes",
    )

    class Meta:
        unique_together = ("post", "user")


class Bookmark(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_bookmarks",
    )

    class Meta:
        unique_together = ("post", "user")
        ordering = ["-created_at"]
