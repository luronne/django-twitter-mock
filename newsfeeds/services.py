from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper


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
        # USE bulk_create INSTEAD
        NewsFeed.objects.bulk_create(newsfeeds)

        # bulk_create will not call the post_save method
        # need to manually push to cache
        for newsfeed in newsfeeds:
            cls.push_newsfeed_to_cache(newsfeed)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        # queryset is lazy loading
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(key, queryset)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        return RedisHelper.push_object(key, newsfeed, queryset)
