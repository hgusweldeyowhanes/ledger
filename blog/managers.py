from django.db import models
from django.utils import timezone


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=self.model.Status.PUBLISHED,
            published_at__lte=timezone.now(),
            is_deleted=False,
        )

    def visible_to(self, user):
        qs = self.filter(is_deleted=False)
        if user is None or not user.is_authenticated:
            return qs.published()
        if user.is_staff:
            return qs
        return qs.filter(models.Q(author=user) | models.Q(
            status=self.model.Status.PUBLISHED,
            published_at__lte=timezone.now(),
        ))


class PostManager(models.Manager):
    def get_queryset(self):
        return PublishedQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def published(self):
        return self.get_queryset().published()

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)
