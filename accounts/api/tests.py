from accounts.models import UserProfile
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase

LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL = '/api/profiles/{}/'


class AccountApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        # execute every test function
        self.client = APIClient()
        self.user = self.create_user(
            username='testUser',
            email='testuser@example.com',
            password='correct password',
        )

    def test_login(self):
        # have to use POST, not GET
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'email': self.user.email,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # method POST used, but with wrong password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'email': self.user.email,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # login status, not logged in yet
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_logged_in'], False)

        # login
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'email': self.user.email,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['email'], 'testuser@example.com')
        # login status, logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # login first
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'email': self.user.email,
            'password': 'correct password',
        })
        # login status, logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # have to use POST, not GET
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # POST used, log out
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # login status, logged out
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@example.com',
            'password': 'any password',
        }

        # have to use POST, not GET
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # wrong email
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # too short password
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@example.com',
            'password': '123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # too long username
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooong',
            'email': 'someone@twitter.com',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # sign up success
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'someone')
        # user profile is created
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)
        # login status, logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileApiTests(TestCase):

    def test_update(self):
        user1, user1_client = self.create_user_and_client('user1')
        p = user1.profile
        p.nickname = 'old nickname'
        p.save()
        url = USER_PROFILE_DETAIL.format(p.id)

        # anonymous user
        response = self.anonymous_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['detail'],
            'Authentication credentials were not provided.',
        )

        # profile can only be updated by the user
        _, user2_client = self.create_user_and_client('user2')
        response = user2_client.put(url, {
            'nickname': 'new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['detail'],
            "You don't have permission to access this object.",
        )
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'old nickname')

        # update nickname
        response = user1_client.put(url, {
            'nickname': 'real new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'real new nickname')

        # update avatar
        response = user1_client.put(url, {
            'avatar': SimpleUploadedFile(
                name='my-avatar.jpg',
                content=str.encode('a fake image'),
                content_type='image/jpeg',
            )
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('my-avatar' in response.data['avatar'], True)
        p.refresh_from_db()
        self.assertIsNotNone(p.avatar)
