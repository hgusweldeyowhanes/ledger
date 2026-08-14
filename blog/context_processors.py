from django.db.models import Count

from .models import Category, Tag


def blog_nav(request):
    return {
        "nav_categories": Category.objects.annotate(
            post_count=Count("posts", distinct=True)
        ).order_by("name")[:10],
        "nav_tags": Tag.objects.annotate(post_count=Count("posts", distinct=True)).order_by("-post_count")[:8],
    }
