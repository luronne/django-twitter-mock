from newsfeeds.models import NewsFeed
from newsfeeds.tasks import fanout_newsfeeds_task
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # use tweet.id as parameter instead of tweet
        # since celery can not serialize Tweet
        fanout_newsfeeds_task.delay(tweet.id)  # asynchronous task process

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
