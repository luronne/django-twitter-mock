from friendships.models import Friendship
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        # not authenticated user
        self.anonymous_client = APIClient()

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

    def test_follow(self):
        url = FOLLOW_URL.format(self.user1.id)

        # unauthenticated user follow
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # wrong method GET
        response = self.user2_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # self follow
        response = self.user1_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # successful follow
        response = self.user2_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # duplicate follow, silent processing
        response = self.user2_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual('duplicate' in response.data, True)
        # follow non-existent user
        response = self.user2_client.post(FOLLOW_URL.format(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # follow back, check database
        count = Friendship.objects.count()
        response = self.user1_client.post(FOLLOW_URL.format(self.user2.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Friendship.objects.count(), count + 1)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.user1.id)

        # unauthenticated user unfollow
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # wrong method GET
        response = self.user2_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # self unfollow
        response = self.user1_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # unfollow non-existent user
        response = self.user2_client.post(UNFOLLOW_URL.format(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # successful unfollow
        Friendship.objects.create(from_user=self.user2, to_user=self.user1)
        count = Friendship.objects.count()
        response = self.user2_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        # unfollow non-follower, silent processing
        count = Friendship.objects.count()
        response = self.user2_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)

    def test_followers(self):
        url = FOLLOWERS_URL.format(self.user1.id)

        # wrong method POST
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # non-existent user followers
        response = self.anonymous_client.get(FOLLOWERS_URL.format(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # right method GET
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ordering
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'user1_follower1'
        )
        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'user1_follower0'
        )

    def test_followings(self):
        url = FOLLOWINGS_URL.format(self.user1.id)

        # wrong method POST
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # non-existent user followings
        response = self.anonymous_client.get(FOLLOWINGS_URL.format(999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # right method GET
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ordering
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'user1_following2'
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'user1_following1'
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'user1_following0'
        )
