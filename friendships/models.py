from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save, pre_delete
from friendships.listeners import invalidate_following_cache

class Friendship(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='following_friendship_set',
    )

    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='follower_friendship_set',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('from_user_id', 'created_at'),
            ('to_user_id', 'created_at'),
        )
        unique_together = (('from_user_id', 'to_user_id'),)
        ordering = ('-created_at',)

    def __str__(self):
        return '{} followed {}'.format(self.from_user_id, self.to_user_id)

# hook up with listeners to invalidate cache
pre_delete.connect(invalidate_following_cache, sender=Friendship)
pre_save.connect(invalidate_following_cache, sender=Friendship)