from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.models import Tweet, TweetPhoto

TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'


class TweetApiTests(TestCase):

    def setUp(self):
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # normal request
        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user1.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # too short content
        response = self.user1_client.post(TWEET_CREATE_API, {'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # too long content
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': '0' * 141
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # normal post
        tweets_count = Tweet.objects.count()
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'Hello World test tweet!'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(Tweet.objects.count(), tweets_count + 1)

    def test_create_with_files(self):
        # upload with no args of files, compatible with old api
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'selfie!',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 0)

        # upload none files
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'selfie!',
            'files': [],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 0)

        # upload one file
        file = SimpleUploadedFile(
            name='selfie.jpg',
            content=str.encode('a fake image'),
            content_type='image/jpeg',
        )
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'a selfie',
            'files': [file],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 1)

        # upload multiple file
        file1 = SimpleUploadedFile(
            name='selfie1.jpg',
            content=str.encode('image 1'),
            content_type='image/jpeg',
        )
        file2 = SimpleUploadedFile(
            name='selfie2.jpg',
            content=str.encode('image 2'),
            content_type='image/jpeg',
        )
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'selfie!',
            'files': [file1, file2],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 3)

        # retrieve with photo urls
        retrieve_url = TWEET_RETRIEVE_API.format(response.data['id'])
        response = self.user1_client.get(retrieve_url)
        self.assertEqual(len(response.data['photo_urls']), 2)
        self.assertEqual('selfie1' in response.data['photo_urls'][0], True)
        self.assertEqual('selfie2' in response.data['photo_urls'][1], True)

        # list with photo urls
        response = self.user1_client.get(TWEET_LIST_API, {
            'user_id': self.user1.id,
        })
        self.assertEqual(len(response.data['tweets'][0]['photo_urls']), 2)

        # upload files more than limit
        files = [
            SimpleUploadedFile(
                name=f'selfie{i}.jpg',
                content=str.encode(f'image {i}'),
                content_type='image/jpeg',
            )
            for i in range(TWEET_PHOTOS_UPLOAD_LIMIT + 1)
        ]
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'selfie!',
            'files': files,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TweetPhoto.objects.count(), 3)

    def test_retrieve(self):
        # invalid tweet_id
        url = TWEET_RETRIEVE_API.format(-1)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # no comments at initial
        tweet = self.create_tweet(self.user1)
        url = TWEET_RETRIEVE_API.format(tweet.id)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 0)

        #
        self.create_comment(self.user1, tweet, 'comment 1')
        self.create_comment(self.user2, tweet, 'comment 2')
        self.create_comment(self.user2, self.create_tweet(self.user1), 'comment 3')
        response = self.anonymous_client.get(url)
        self.assertEqual(len(response.data['comments']), 2)

        # tweet will include the nickname and avatar_url
        profile = self.user1.profile
        self.assertEqual(response.data['user']['nickname'], profile.nickname)
        self.assertEqual(response.data['user']['avatar_url'], None)
