from django.db.models import Count

from .models import Category, Notification, Tag
from .forms import NewsletterForm


def blog_nav(request):
    unread = 0
    if request.user.is_authenticated:
        unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {
        "nav_categories": Category.objects.annotate(
            post_count=Count("posts", distinct=True)
        ).order_by("name")[:10],
        "nav_tags": Tag.objects.annotate(post_count=Count("posts", distinct=True)).order_by(
            "-post_count"
        )[:8],
        "unread_notifications": unread,
        "newsletter_form": NewsletterForm(),
    }
