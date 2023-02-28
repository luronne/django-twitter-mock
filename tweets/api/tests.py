from testing.testcases import TestCase
from rest_framework.test import APIClient
from tweets.models import Tweet

TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'


class TweetApiTests(TestCase):

    def setUp(self):
        self.anonymous_client = APIClient()

        # authenticated
        self.user1 = self.create_user('testUser1', 'user1@example.com')
        self.tweets1 = [
            self.create_tweet(self.user1)
            for i in range(3)
        ]
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(self.user1)

        self.user2 = self.create_user('testUser2', 'user2@example.com')
        self.tweets2 = [
            self.create_tweet(self.user2)
            for i in range(2)
        ]
        self.user2_client = APIClient()
        self.user2_client.force_authenticate(self.user2)

    def test_list_api(self):
        # user_id must include
        response = self.anonymous_client.get(TWEET_CREATE_API)
        self.assertEqual(response.status_code, 400)

        # normal request
        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user1.id,
        })
        self.assertEqual(response.status_code, 200)
        # length of tweets
        self.assertEqual(len(response.data['tweets']), 3)
        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user2.id,
        })
        self.assertEqual(len(response.data['tweets']), 2)
        # ordered by created time
        self.assertEqual(response.data['tweets'][0]['id'], self.tweets2[1].id)
        self.assertEqual(response.data['tweets'][1]['id'], self.tweets2[0].id)

    def test_create_api(self):
        # must log in
        response = self.anonymous_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, 403)
        # must with content
        response = self.user1_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, 400)
        # too short content
        response = self.user1_client.post(TWEET_CREATE_API, {'content': '1'})
        self.assertEqual(response.status_code, 400)
        # too long content
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': '0' * 141
        })
        self.assertEqual(response.status_code, 400)

        # normal post
        tweets_count = Tweet.objects.count()
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'Hello World test tweet!'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(Tweet.objects.count(), tweets_count + 1)
