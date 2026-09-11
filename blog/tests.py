from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from blog.models import (
    AuthorFollow,
    Category,
    Comment,
    NewsletterSubscriber,
    Notification,
    Post,
    PostRevision,
    Series,
    SeriesMembership,
)
from blog.services import confirm_subscriber

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

    def test_newsletter_subscribe_and_confirm(self):
        res = self.client.post("/api/newsletter/subscribe/", {"email": "news@example.com"}, format="json")
        self.assertEqual(res.status_code, 202)
        sub = NewsletterSubscriber.objects.get(email="news@example.com")
        self.assertFalse(sub.is_active)
        self.assertTrue(mail.outbox)
        confirm = self.client.post(f"/api/newsletter/confirm/{sub.confirm_token}/")
        self.assertEqual(confirm.status_code, 200)
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)

    def test_follow_and_following_feed(self):
        post = Post.objects.create(
            title="For followers",
            content="hello",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        self.client.force_authenticate(self.other)
        follow = self.client.post(f"/api/authors/{self.author.username}/follow/")
        self.assertTrue(follow.data["following"])
        feed = self.client.get("/api/feed/following/")
        self.assertEqual(feed.status_code, 200)
        titles = [row["title"] for row in feed.data["results"]]
        self.assertIn(post.title, titles)

    def test_comment_pending_then_approve(self):
        post = Post.objects.create(
            title="Discuss",
            content="body",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        self.client.force_authenticate(self.other)
        res = self.client.post(
            "/api/comments/",
            {"post": post.id, "body": "Needs review"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["is_approved"])
        comment_id = res.data["id"]
        listed = self.client.get(f"/api/comments/?post={post.id}")
        ids = [row["id"] for row in listed.data["results"]]
        self.assertNotIn(comment_id, ids)
        self.client.force_authenticate(self.author)
        approved = self.client.post(f"/api/comments/{comment_id}/approve/")
        self.assertEqual(approved.status_code, 200)
        self.assertTrue(approved.data["is_approved"])

    def test_advanced_search_filters(self):
        short = Post.objects.create(
            title="Short read",
            content="x " * 50,
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        long = Post.objects.create(
            title="Long read",
            content="x " * 1200,
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        self.assertGreater(long.reading_time, short.reading_time)
        res = self.client.get("/api/posts/?min_reading_time=4")
        self.assertEqual(res.status_code, 200)
        titles = [row["title"] for row in res.data["results"]]
        self.assertIn("Long read", titles)
        self.assertNotIn("Short read", titles)

    def test_post_revisions_and_rollback(self):
        self.client.force_authenticate(self.author)
        post = Post.objects.create(
            title="Versioned",
            content="v1 text",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        patch = self.client.patch(
            f"/api/posts/{post.slug}/",
            {"title": "Versioned v2", "content": "v2 text"},
            format="json",
        )
        self.assertEqual(patch.status_code, 200)
        revs = self.client.get(f"/api/posts/{post.slug}/revisions/")
        self.assertEqual(revs.status_code, 200)
        self.assertGreaterEqual(len(revs.data["results"]), 1)
        revision_id = revs.data["results"][0]["id"]
        rollback = self.client.post(
            f"/api/posts/{post.slug}/rollback/",
            {"revision_id": revision_id},
            format="json",
        )
        self.assertEqual(rollback.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.title, "Versioned")
        self.assertEqual(post.content, "v1 text")

    def test_trending_posts_endpoint_returns_posts_by_views(self):
        now = timezone.now()
        one = Post.objects.create(
            title="Top story",
            content="hello world",
            author=self.author,
            status=Post.Status.PUBLISHED,
            published_at=now,
            view_count=12,
        )
        two = Post.objects.create(
            title="Second story",
            content="hello world again",
            author=self.author,
            status=Post.Status.PUBLISHED,
            published_at=now,
            view_count=8,
        )
        res = self.client.get("/api/posts/trending/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([row["title"] for row in res.data["results"]], [one.title, two.title])

    def test_author_analytics_endpoint(self):
        self.client.force_authenticate(self.author)
        Post.objects.create(
            title="A",
            content="hello world",
            author=self.author,
            status=Post.Status.PUBLISHED,
            view_count=7,
        )
        Post.objects.create(
            title="B",
            content="hello " * 400,
            author=self.author,
            status=Post.Status.DRAFT,
            view_count=3,
        )
        res = self.client.get("/api/posts/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["totals"]["posts"], 2)
        self.assertEqual(res.data["totals"]["views"], 10)


class SeriesAndNotificationTests(TestCase):
    def setUp(self):
        self.author = make_user("author")
        self.reader = make_user("fan")
        self.post = Post.objects.create(
            title="Part one",
            content="first",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )
        self.post2 = Post.objects.create(
            title="Part two",
            content="second",
            author=self.author,
            status=Post.Status.PUBLISHED,
        )

    def test_series_ordering(self):
        series = Series.objects.create(title="Build log", author=self.author)
        SeriesMembership.objects.create(series=series, post=self.post2, position=2)
        SeriesMembership.objects.create(series=series, post=self.post, position=1)
        ordered = list(series.ordered_posts())
        self.assertEqual([p.title for p in ordered], ["Part one", "Part two"])

    def test_like_creates_notification(self):
        self.client.login(username="fan", password="pass12345")
        self.client.post(reverse("blog:like", kwargs={"slug": self.post.slug}))
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.author,
                actor=self.reader,
                verb=Notification.Verb.LIKED,
                post=self.post,
            ).exists()
        )


class WebFeatureTests(TestCase):
    def setUp(self):
        self.user = make_user("hgus")
        self.reader = make_user("reader")
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
        self.assertContains(detail, 'property="og:title"')
        self.assertContains(detail, "Copy link")
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)

    def test_newsletter_web_subscribe(self):
        res = self.client.post(
            reverse("blog:newsletter-subscribe"),
            {"email": "web@example.com", "next": "/"},
        )
        self.assertEqual(res.status_code, 302)
        sub = NewsletterSubscriber.objects.get(email="web@example.com")
        confirm_subscriber(sub.confirm_token)
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)

    def test_follow_feed_page(self):
        AuthorFollow.objects.create(follower=self.reader, author=self.user)
        self.client.login(username="reader", password="pass12345")
        res = self.client.get(reverse("blog:following"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Public note")

    def test_comment_moderation_queue(self):
        self.client.login(username="reader", password="pass12345")
        self.client.post(
            reverse("blog:comment", kwargs={"slug": self.post.slug}),
            {"body": "Please approve me"},
        )
        comment = Comment.objects.get(body="Please approve me")
        self.assertFalse(comment.is_approved)
        self.client.login(username="hgus", password="pass12345")
        dash = self.client.get(reverse("blog:dashboard"))
        self.assertContains(dash, "Please approve me")
        self.client.post(
            reverse("blog:moderate-comment", kwargs={"comment_id": comment.id}),
            {"action": "approve", "next": reverse("blog:dashboard")},
        )
        comment.refresh_from_db()
        self.assertTrue(comment.is_approved)

    def test_theme_script_in_base(self):
        res = self.client.get(reverse("blog:home"))
        self.assertContains(res, "theme-toggle")
        self.assertContains(res, "ledger-theme")

    def test_dashboard_shows_revision_history(self):
        self.client.login(username="hgus", password="pass12345")
        self.client.post(
            reverse("blog:post-edit", kwargs={"slug": self.post.slug}),
            {
                "title": "Public note updated",
                "excerpt": "Hello from Addis.",
                "content": "Updated body",
                "status": Post.Status.PUBLISHED,
                "featured": False,
                "allow_comments": True,
                "published_at": "2026-01-01T10:00",
            },
        )
        self.assertTrue(PostRevision.objects.filter(post=self.post).exists())
        res = self.client.get(reverse("blog:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Recent revisions")
