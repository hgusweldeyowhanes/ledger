from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import AuthorFollow, Comment, Notification, PostLike
from .services import notify


@receiver(post_save, sender=PostLike)
def on_like(sender, instance, created, **kwargs):
    if not created:
        return
    notify(
        recipient=instance.post.author,
        actor=instance.user,
        verb=Notification.Verb.LIKED,
        post=instance.post,
    )


@receiver(post_save, sender=Comment)
def on_comment(sender, instance, created, **kwargs):
    if not created or instance.is_deleted:
        return
    notify(
        recipient=instance.post.author,
        actor=instance.author,
        verb=Notification.Verb.COMMENTED,
        post=instance.post,
        comment=instance,
    )


@receiver(pre_save, sender=Comment)
def _track_comment_approval(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_approved = False
        return
    try:
        previous = Comment.objects.get(pk=instance.pk)
        instance._was_approved = previous.is_approved
    except Comment.DoesNotExist:
        instance._was_approved = False


@receiver(post_save, sender=Comment)
def on_comment_approved(sender, instance, created, **kwargs):
    if created or instance.is_deleted:
        return
    was = getattr(instance, "_was_approved", True)
    if not was and instance.is_approved:
        notify(
            recipient=instance.author,
            actor=instance.post.author,
            verb=Notification.Verb.COMMENT_APPROVED,
            post=instance.post,
            comment=instance,
        )


@receiver(post_save, sender=AuthorFollow)
def on_follow(sender, instance, created, **kwargs):
    if not created:
        return
    notify(
        recipient=instance.author,
        actor=instance.follower,
        verb=Notification.Verb.FOLLOWED,
    )
