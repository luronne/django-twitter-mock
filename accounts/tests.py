from testing.testcases import TestCase
from accounts.models import UserProfile


class UserProfileTests(TestCase):

    def test_profile_property(self):
        user = self.create_user('user')
        self.assertEqual(UserProfile.objects.count(), 0)
        # user profile will be created once the property is called
        p = user.profile
        self.assertEqual(isinstance(p, UserProfile), True)
        self.assertEqual(UserProfile.objects.count(), 1)
