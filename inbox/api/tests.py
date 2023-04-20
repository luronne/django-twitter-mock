from notifications.models import Notification
from rest_framework import status
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'
NOTIFICATION_UNREAD_URL = '/api/notifications/unread-count/'
NOTIFICATION_MARK_URL = '/api/notifications/mark-all-as-read/'


class NotificationTests(TestCase):

    def setUp(self):
        self.clear_cache()
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
        # multiple like actions will not trigger duplicate notification
        self.user2_client.post(LIKE_URL, data)
        self.assertEqual(Notification.objects.count(), 1)


class NotificationApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.user1, self.user1_client = self.create_user_and_client('user1')
        self.user2, self.user2_client = self.create_user_and_client('user2')
        self.tweet_user1 = self.create_tweet(self.user1)

    def test_unread_count(self):
        # test like notification unread count
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.tweet_user1.id,
        })
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)

        # test comment notification unread count
        self.user2_client.post(COMMENT_URL, {
            'tweet_id': self.tweet_user1.id,
            'content': 'comment'
        })
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # test the filter user function, only the owner receives notifications
        response = self.user2_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 0)

    def test_mark_all_as_read(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.tweet_user1.id,
        })
        self.user2_client.post(COMMENT_URL, {
            'tweet_id': self.tweet_user1.id,
            'content': 'comment'
        })
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # GET method not allowed
        response = self.user1_client.get(NOTIFICATION_MARK_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # other user can not mark notification
        response = self.user2_client.post(NOTIFICATION_MARK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 0)
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # mark all notifications success
        response = self.user1_client.post(NOTIFICATION_MARK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.tweet_user1.id,
        })
        self.user2_client.post(COMMENT_URL, {
            'tweet_id': self.tweet_user1.id,
            'content': 'comment'
        })

        # anonymous not allowed
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # other user can not see notifications
        response = self.user2_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

        # list success
        response = self.user1_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # test filter unread function
        notification = self.user1.notifications.first()
        notification.unread = False
        notification.save()
        response = self.user1_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.user1_client.get(NOTIFICATION_URL, {'unread': True})
        self.assertEqual(response.data['count'], 1)
        response = self.user1_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)

    def test_upgrade(self):
        self.user2_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.tweet_user1.id,
        })
        self.user2_client.post(COMMENT_URL, {
            'tweet_id': self.tweet_user1.id,
            'content': 'comment'
        })
        notification = self.user1.notifications.first()
        url = '{}{}/'.format(NOTIFICATION_URL, notification.id)

        # POST method not allowed
        response = self.user1_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # anonymous user can not update
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # other user can not update
        response = self.user2_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # update to read success
        response = self.user1_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 1)

        # update to unread success
        response = self.user1_client.put(url, {'unread': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.user1_client.get(NOTIFICATION_UNREAD_URL)
        self.assertEqual(response.data['unread_count'], 2)
        # unread param is required
        response = self.user1_client.put(url, {'verb': 'newverb'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # only unread will be updated
        response = self.user1_client.put(url, {'verb': 'newverb', 'unread': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertNotEqual(notification.verb, 'newverb')
