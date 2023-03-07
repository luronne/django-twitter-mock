from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        """
        DON'T MAKE DATABASE CALL INSIDE FOR LOOP
        followers = FriendshipService.get_followers(tweet.user)
        for follower in followers:
            NewsFeed.objects.create(user=follower, tweet=tweet)
        """
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet)
            for follower in FriendshipService.get_followers(tweet.user)
        ]
        # for the author of the tweet
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
        NewsFeed.objects.bulk_create(newsfeeds)
