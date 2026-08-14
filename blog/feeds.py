from django.contrib.syndication.views import Feed

from .models import Post


class LatestPostsFeed(Feed):
    title = "Ledger — latest essays"
    link = "/"
    description = "New writing from Ledger."

    def items(self):
        return Post.objects.published()[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_link(self, item):
        return item.get_absolute_url()
