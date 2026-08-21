from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import NewsletterSubscriber, Notification


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
