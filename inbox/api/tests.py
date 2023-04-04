from testing.testcases import TestCase
from notifications.models import Notification

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'


class NotificationTests(TestCase):

    def setUp(self):
        self.user1, self.user1_client = self.create_user_and_client('user1')
        self.user2, self.user2_client = self.create_user_and_client('user2')
        self.tweet_user1 = self.create_tweet(self.user1)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.user2_client.post(COMMENT_URL, {
            'tweet_id': self.tweet_user1.id,
            'content': 'test comment'
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        data = {
            'content_type': 'tweet',
            'object_id': self.tweet_user1.id,
        }
        self.user2_client.post(LIKE_URL, data)
        self.assertEqual(Notification.objects.count(), 1)
        # multiple actions will not trigger notification
        self.user2_client.post(LIKE_URL, data)
        self.assertEqual(Notification.objects.count(), 1)
