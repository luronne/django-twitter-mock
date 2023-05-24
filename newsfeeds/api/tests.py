from django.conf import settings
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEET_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        # authenticated user1 and user2
        self.user1 = self.create_user('user1')
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(self.user1)

        self.user2 = self.create_user('user2')
        self.user2_client = APIClient()
        self.user2_client.force_authenticate(self.user2)

        # create followers and following for user1
        for i in range(2):
            follower = self.create_user('user1_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.user1)
        for i in range(3):
            following = self.create_user('user1_following{}'.format(i))
            Friendship.objects.create(from_user=self.user1, to_user=following)

    def test_list(self):
        # logged in user
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # POST not allowed
        response = self.user1_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # No newsfeeds at beginning
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

        # post a tweet, self view
        self.user1_client.post(POST_TWEET_URL, {'content': 'Test world!'})
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)

        # followers view
        self.user1_client.post(FOLLOW_URL.format(self.user2.id))
        response = self.user2_client.post(POST_TWEET_URL, {
            'content': 'Test world!'
        })
        posted_twitter_id = response.data['id']
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(
            response.data['results'][0]['tweet']['id'],
            posted_twitter_id
        )

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []

        # create newsfeeds
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user, 'tweet {}'.format(i))
            newsfeed = self.create_newsfeed(user=self.user1, tweet=tweet)
            newsfeeds.append(newsfeed)

        newsfeeds = newsfeeds[::-1]

        # load the first page
        response = self.user1_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        # ordering
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # load the second page
        response = self.user1_client.get(NEWSFEEDS_URL, {
            'user_id': self.user1.id,
            'created_at__lt': newsfeeds[page_size - 1].created_at,
        })
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), page_size)
        # ordering
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[page_size].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size * 2 - 1].id,
        )

        # load latest posts
        response = self.user1_client.get(NEWSFEEDS_URL, {
            'user_id': self.user1.id,
            'created_at__gt': newsfeeds[0].created_at,
        })
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        new_tweet = self.create_tweet(followed_user, 'new tweet coming!')
        new_newsfeed = self.create_newsfeed(user=self.user1, tweet=new_tweet)
        response = self.user1_client.get(NEWSFEEDS_URL, {
            'user_id': self.user1.id,
            'created_at__gt': newsfeeds[0].created_at,
        })
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        profile = self.user2.profile
        profile.nickname = 'user_two'
        profile.save()

        self.assertEqual(self.user1.username, 'user1')
        self.create_newsfeed(self.user2, self.create_tweet(self.user1))
        self.create_newsfeed(self.user2, self.create_tweet(self.user2))

        response = self.user2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'user2')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'user_two')
        self.assertEqual(results[1]['tweet']['user']['username'], 'user1')

        self.user1.username = 'user_one'
        self.user1.save()
        profile.nickname = 'user_dos'
        profile.save()

        response = self.user2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'user2')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'user_dos')
        self.assertEqual(results[1]['tweet']['user']['username'], 'user_one')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.user1, 'content1')
        self.create_newsfeed(self.user2, tweet)
        response = self.user2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'user1')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # user cache test, update of utils
        self.user1.username = 'user_uno'
        self.user1.save()
        response = self.user2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'user_uno')

        # tweet cache test
        tweet.content = 'content2'
        tweet.save()
        response = self.user2_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')

    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL, {'created_at__lt': created_at__lt})
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = EndlessPagination.page_size
        users = [self.create_user('user_{}'.format(i)) for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5], content='feed{}'.format(i))
            feed = self.create_newsfeed(self.user1, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # only cache list_limit number of objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(self.user1.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.user1)
        self.assertEqual(queryset.count(), list_limit + page_size)

        # a followed user create a new tweet
        self.create_friendship(self.user1, self.user2)
        new_tweet = self.create_tweet(self.user2, 'a new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.user1_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()

        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()
