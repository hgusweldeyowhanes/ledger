from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from blog.models import Category, Post

User = get_user_model()


def make_user(username, **kwargs):
    extra = {"email": f"{username}@example.com", "password": "pass12345"}
    extra.update(kwargs)
    password = extra.pop("password")
    if "name" in {f.name for f in User._meta.get_fields()}:
        extra.setdefault("name", username)
    return User.objects.create_user(username=username, password=password, **extra)


class PostModelTests(TestCase):
    def setUp(self):
        self.user = make_user("author")

    def test_slug_and_reading_time(self):
        post = Post.objects.create(
            title="Hello Ledger",
            content="word " * 400,
            author=self.user,
            status=Post.Status.PUBLISHED,
        )
        self.assertEqual(post.slug, "hello-ledger")
        self.assertGreaterEqual(post.reading_time, 2)
        self.assertTrue(post.is_live())

    def test_draft_is_not_live(self):
        post = Post.objects.create(title="Secret", content="x", author=self.user)
        self.assertFalse(post.is_live())
        self.assertEqual(Post.objects.published().count(), 0)


class BlogAPITests(APITestCase):
    def setUp(self):
        self.author = make_user("writer")
        self.other = make_user("reader")
        self.cat = Category.objects.create(name="Engineering")

    def test_anonymous_lists_only_published(self):
        Post.objects.create(title="Draft", content="d", author=self.author)
        Post.objects.create(
            title="Live",
            content="published essay",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        res = self.client.get("/api/posts/")
        self.assertEqual(res.status_code, 200)
        titles = [row["title"] for row in res.data["results"]]
        self.assertIn("Live", titles)
        self.assertNotIn("Draft", titles)

    def test_create_requires_auth(self):
        res = self.client.post("/api/posts/", {"title": "Nope", "content": "x"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_author_can_create_like_and_publish(self):
        self.client.force_authenticate(self.author)
        res = self.client.post(
            "/api/posts/",
            {
                "title": "My essay",
                "content": "A careful argument about Django.",
                "category_ids": [self.cat.id],
                "tag_names": ["django", "addis"],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        slug = res.data["slug"]
        pub = self.client.post(f"/api/posts/{slug}/publish/")
        self.assertEqual(pub.status_code, 200)
        self.assertEqual(pub.data["status"], "published")
        like = self.client.post(f"/api/posts/{slug}/like/")
        self.assertTrue(like.data["liked"])

    def test_other_user_cannot_edit(self):
        post = Post.objects.create(
            title="Owned",
            content="body",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        self.client.force_authenticate(self.other)
        res = self.client.patch(f"/api/posts/{post.slug}/", {"title": "Hacked"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class WebTests(TestCase):
    def setUp(self):
        self.user = make_user("hgus")
        self.post = Post.objects.create(
            title="Public note",
            content="Hello from Addis.",
            author=self.user,
            status=Post.Status.PUBLISHED,
        )

    def test_home_and_detail(self):
        home = self.client.get(reverse("blog:home"))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Public note")
        detail = self.client.get(self.post.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)
