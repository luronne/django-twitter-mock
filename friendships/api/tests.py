from friendships.models import Friendship
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import FriendshipPagination

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

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
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'user1_follower1'
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
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
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        ts2 = response.data['results'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'user1_following2'
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'user1_following1'
        )
        self.assertEqual(
            response.data['results'][2]['user']['username'],
            'user1_following0'
        )

    def test_followers_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        Friendship.objects.all().delete()
        for i in range(page_size * 2):
            follower = self.create_user('user1_follower_{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.user1)
            if follower.id % 2 == 0:
                Friendship.objects.create(from_user=self.user2, to_user=follower)

        url = FOLLOWERS_URL.format(self.user1.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # has_followed test
        # anonymous user has not followed any user
        response = self.anonymous_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)
        # user2 has followed users with even id
        response = self.user2_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)
        # user1 has not followed any follower user
        response = self.user1_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

    def test_followings_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        Friendship.objects.all().delete()
        for i in range(page_size * 2):
            following = self.create_user('user1_following_{}'.format(i))
            Friendship.objects.create(from_user=self.user1, to_user=following)
            if following.id % 2 == 0:
                Friendship.objects.create(from_user=self.user2, to_user=following)

        url = FOLLOWINGS_URL.format(self.user1.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # has_followed test
        # anonymous user has not followed any user
        response = self.anonymous_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)
        # user2 has followed users with even id
        response = self.user2_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)
        # user1 has_followed all the following users
        response = self.user1_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

    def _test_friendship_pagination(self, url, page_size, max_page_size):
        # test get_paginated_response()
        # page 1 result
        response = self.anonymous_client.get(url, {'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)
        # page 2 result
        response = self.anonymous_client.get(url, {'page': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['page_number'], 2)
        self.assertEqual(response.data['has_next_page'], False)
        # page 3 result
        response = self.anonymous_client.get(url, {'page': 3})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # user can customize the page_size in the range of max_page_size
        response = self.anonymous_client.get(url, {'page': 1, 'size': 2})
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['total_pages'], page_size)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        # user can not access page_size out of max_page_size
        response = self.anonymous_client.get(url, {'page': 1, 'size': max_page_size + 1})
        self.assertEqual(len(response.data['results']), max_page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)
