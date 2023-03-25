from comments.models import Comment
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'


class CommentApiTests(TestCase):

    def setUp(self):
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
