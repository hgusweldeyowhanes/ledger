from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import NewsletterSubscriber, Notification, PostRevision, SeriesMembership, Tag


def comment_should_auto_approve(user, post):
    return user.is_staff or user.pk == post.author_id


def notify(*, recipient, actor, verb, post=None, comment=None):
    if recipient is None or (actor and recipient.pk == actor.pk):
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        verb=verb,
        post=post,
        comment=comment,
    )


def create_post_revision(post, edited_by=None):
    snapshot = {
        "status": post.status,
        "featured": post.featured,
        "allow_comments": post.allow_comments,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "category_ids": list(post.categories.values_list("id", flat=True)),
        "tag_names": list(post.tags.values_list("name", flat=True)),
        "series": None,
    }
    membership = post.series_membership()
    if membership:
        snapshot["series"] = {
            "series_id": membership.series_id,
            "position": membership.position,
        }
    return PostRevision.objects.create(
        post=post,
        edited_by=edited_by,
        title=post.title,
        excerpt=post.excerpt,
        content=post.content,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        snapshot=snapshot,
    )


def restore_post_revision(post, revision):
    post.title = revision.title
    post.excerpt = revision.excerpt
    post.content = revision.content
    post.meta_title = revision.meta_title
    post.meta_description = revision.meta_description
    post.status = revision.snapshot.get("status", post.status)
    post.featured = revision.snapshot.get("featured", post.featured)
    post.allow_comments = revision.snapshot.get("allow_comments", post.allow_comments)
    published_at = revision.snapshot.get("published_at")
    if published_at:
        post.published_at = datetime.fromisoformat(published_at)
        if timezone.is_naive(post.published_at):
            post.published_at = timezone.make_aware(post.published_at, timezone.get_current_timezone())
    post.save()

    category_ids = revision.snapshot.get("category_ids")
    if isinstance(category_ids, list):
        post.categories.set(category_ids)

    tag_names = revision.snapshot.get("tag_names")
    if isinstance(tag_names, list):
        tags = []
        for name in tag_names:
            if not str(name).strip():
                continue
            tag, _ = Tag.objects.get_or_create(name=str(name).strip())
            tags.append(tag)
        post.tags.set(tags)

    SeriesMembership.objects.filter(post=post).delete()
    series_info = revision.snapshot.get("series")
    if isinstance(series_info, dict) and series_info.get("series_id"):
        SeriesMembership.objects.create(
            series_id=series_info["series_id"],
            post=post,
            position=max(1, int(series_info.get("position") or 1)),
        )
    return post


def subscribe_newsletter(email, request=None):
    email = email.strip().lower()
    sub, created = NewsletterSubscriber.objects.get_or_create(email=email)
    if sub.is_active and sub.confirmed_at:
        return sub, "already"
    if not created and not sub.is_active:
        from .models import _token

        sub.confirm_token = _token()
        sub.save(update_fields=["confirm_token", "updated_at"])
    _send_confirm_email(sub, request)
    return sub, "pending"


def confirm_subscriber(token):
    try:
        sub = NewsletterSubscriber.objects.get(confirm_token=token)
    except NewsletterSubscriber.DoesNotExist:
        return None
    sub.is_active = True
    sub.confirmed_at = timezone.now()
    sub.save(update_fields=["is_active", "confirmed_at", "updated_at"])
    return sub


def unsubscribe(token):
    try:
        sub = NewsletterSubscriber.objects.get(unsubscribe_token=token)
    except NewsletterSubscriber.DoesNotExist:
        return None
    sub.is_active = False
    sub.save(update_fields=["is_active", "updated_at"])
    return sub


def active_subscribers():
    return NewsletterSubscriber.objects.filter(is_active=True, confirmed_at__isnull=False)


def _frontend_base(request=None):
    base = getattr(settings, "FRONTEND_URL", "") or getattr(settings, "SITE_URL", "http://127.0.0.1:5173")
    return base.rstrip("/")


def _send_confirm_email(sub, request=None):
    base = _frontend_base(request)
    confirm_url = f"{base}/newsletter/confirm/{sub.confirm_token}"
    unsub_url = f"{base}/newsletter/unsubscribe/{sub.unsubscribe_token}"
    send_mail(
        subject="Confirm your Ledger newsletter subscription",
        message=(
            f"Confirm: {confirm_url}\n\n"
            f"If you did not subscribe, ignore this email or unsubscribe: {unsub_url}\n"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ledger.local"),
        recipient_list=[sub.email],
        fail_silently=False,
    )


def send_digest_email(subscriber, posts, request=None):
    if not posts:
        return
    base = _frontend_base(request)
    lines = ["New on Ledger:\n"]
    for post in posts:
        lines.append(f"- {post.title}\n  {base}/post/{post.slug}\n")
    unsub = f"{base}/newsletter/unsubscribe/{subscriber.unsubscribe_token}"
    lines.append(f"\nUnsubscribe: {unsub}")
    send_mail(
        subject=f"Ledger digest · {len(posts)} new post{'s' if len(posts) != 1 else ''}",
        message="\n".join(lines),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ledger.local"),
        recipient_list=[subscriber.email],
        fail_silently=False,
    )
