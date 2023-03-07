from friendships.models import Friendship


class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        """
        friendships = Friendship.objects.filter(to_user=user)
        followers_ids = [friendship.from_user for friendship in friendships]
        followers = User.objects.filter(id__in=followers_ids)
        """
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')

        return [friendship.from_user for friendship in friendships]