from django.test import TestCase, Client
from django.urls import reverse

from django.contrib.auth.models import User

# Create your tests here.
class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('users:login')  # Replace with actual URL name

    def test_get_request_returns_login_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_valid_credentials_redirects_to_home(self):
        # Create a test user
        User.objects.create_user(username='testuser', password='testpass123')
        response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home:home'))

    def test_invalid_credentials_shows_error_message(self):
        response = self.client.post(self.url, {
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")

class SignUpViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('users:sign-up')  # Replace with actual URL name

    def test_get_request_returns_sign_up_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/sign-up.html')

    def test_passwords_match_creates_user_and_redirects(self):
        response = self.client.post(self.url, {
            'username': 'newuser',
            'password': 'password123',
            'confirmPassword': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home:home'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_passwords_do_not_match_shows_error_message(self):
        response = self.client.post(self.url, {
            'username': 'newuser',
            'password': 'password123',
            'confirmPassword': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")