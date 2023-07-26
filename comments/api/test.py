from comments.models import Comment
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.user1 = self.create_user('user1')
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(self.user1)

        self.user2 = self.create_user('user2')
        self.user2_client = APIClient()
        self.user2_client.force_authenticate(self.user2)

        self.tweet = self.create_tweet(self.user1)

    def test_create(self):
        # anonymous client not allowed
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # no attributes
        response = self.user1_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # only tweet_id, not allowed
        response = self.user1_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # only content, not allowed
        response = self.user1_client.post(COMMENT_URL, {'content': 'test comment'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # too long content (longer than 140 ch), not allowed
        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data['errors'], True)

        # comment successfully
        response = self.user1_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': 'test comment',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], 'test comment')

    def test_destroy(self):
        comment = self.create_comment(self.user1, self.tweet)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # anonymous user can not delete
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # other user can not delete
        response = self.user2_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # successful delete
        count = Comment.objects.count()
        response = self.user1_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.user1, self.tweet, 'original')
        another_tweet = self.create_tweet(self.user2)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # anonymous client not allowed
        response = self.anonymous_client.put(url, {'content': 'updated'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # other client not allowed
        response = self.user2_client.put(url, {'content': 'updated'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, 'updated')

        # update content only
        before_created_at = comment.created_at
        before_updated_at = comment.updated_at
        now = timezone.now()
        response = self.user1_client.put(url, {
            'content': 'updated',
            'user_id': self.user2.id,  # ensure to use the user id of the request
            'tweet_id': another_tweet.id,  # ensure the related tweet not changed
            'created_at': now,  # ensure the created_at not changed
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'updated')
        self.assertEqual(comment.user, self.user1)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        # must include tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # can access with tweet_id
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # no comment at initial
        self.assertEqual(len(response.data['comments']), 0)

        # create comments
        self.create_comment(self.user1, self.tweet, 'comment 1')
        self.create_comment(self.user2, self.tweet, 'comment 2')
        self.create_comment(self.user2, self.create_tweet(self.user2), 'comment 3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        # right comments count
        self.assertEqual(len(response.data['comments']), 2)
        # ordered by created_at
        self.assertEqual(response.data['comments'][0]['content'], 'comment 1')
        self.assertEqual(response.data['comments'][1]['content'], 'comment 2')

        # only tweet_id will be used
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.user1.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail API
        tweet = self.create_tweet(self.user1)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.user2_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list API
        self.create_comment(self.user1, tweet)
        response = self.user2_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # test newsfeed list API
        self.create_comment(self.user2, tweet)
        self.create_newsfeed(self.user2, tweet)
        response = self.user2_client.get(NEWSFEED_LIST_API)  # the same user
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 2)

    def test_comments_count_with_cache(self):
        tweet_url = TWEET_DETAIL_API.format(self.tweet.id)
        response = self.user1_client.get(tweet_url)
        self.assertEqual(self.tweet.comments_count, 0)
        self.assertEqual(response.data['comments_count'], 0)

        data = {'tweet_id': self.tweet.id, 'content': 'test comment'}
        for i in range(2):
            _, client = self.create_user_and_client('test_user{}'.format(i))
            client.post(COMMENT_URL, data)
            response = client.get(tweet_url)
            self.assertEqual(response.data['comments_count'], i + 1)
            self.tweet.refresh_from_db()
            self.assertEqual(self.tweet.comments_count, i + 1)

        comment_data = self.user2_client.post(COMMENT_URL, data).data
        response = self.user2_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # comment update will not update comments_count
        comment_url = '{}{}/'.format(COMMENT_URL, comment_data['id'])
        response = self.user2_client.put(comment_url, {'content': 'updated comment'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.user2_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # comment delete will update comments_count
        response = self.user2_client.delete(comment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.user2_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 2)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 2)
