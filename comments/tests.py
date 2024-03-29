from testing.testcases import TestCase


class CommentModels(TestCase):

    def test_comment(self):
        user = self.create_user('tester')
        tweet = self.create_tweet(user)
        comment = self.create_comment(user, tweet)
        self.assertNotEqual(comment.__str__(), None)
