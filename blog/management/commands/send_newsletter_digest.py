from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from blog.services import active_subscribers, send_digest_email


class Command(BaseCommand):
    help = "Email confirmed newsletter subscribers a digest of recently published posts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=int,
            default=24,
            help="Include posts published in the last N hours (default 24).",
        )

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(hours=options["since"])
        posts = list(
            Post.objects.published()
            .filter(published_at__gte=since)
            .order_by("-published_at")
        )
        subs = list(active_subscribers())
        if not posts:
            self.stdout.write("No recent posts; nothing to send.")
            return
        if not subs:
            self.stdout.write("No active subscribers.")
            return
        for sub in subs:
            send_digest_email(sub, posts)
        self.stdout.write(
            self.style.SUCCESS(f"Sent digest of {len(posts)} post(s) to {len(subs)} subscriber(s).")
        )
