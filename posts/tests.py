from django.test import TestCase
from django.test import Client
from .models import User, Post, Group, Follow
from django.urls import reverse
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

# Create your tests here.


class CreateProfile(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="TestUser@example.com", password="Test12345User"
        )

    def test_profile(self):
        self.client.force_login(self.user)
        response = self.client.get("/testuser/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["user_profile"], User)
        self.assertEqual(response.context["user_profile"].username, self.user.username)

    def test_login_new_post(self):
        self.client.force_login(self.user)
        new_post = self.client.post("/new/", {"text": "New_test_post"})
        self.assertRedirects(
            new_post,
            "/",
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )
        response = self.client.get("/")
        self.assertContains(
            response,
            "New_test_post",
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )

    def test_post_add_all_pages(self):
        self.client.force_login(self.user)
        self.post_text = "It`s very interesting, but difficult. Work more"
        self.post = Post.objects.create(text=self.post_text, author=self.user)
        response = self.client.get("/")
        self.assertContains(
            response,
            self.post_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )
        response = self.client.get("/testuser/")
        self.assertContains(
            response,
            self.post_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )
        response = self.client.get(f"/testuser/{self.post.pk}/")
        self.assertContains(
            response,
            self.post_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )

    def test_unauth_new_post(self):
        response = self.client.post("/new/", {"text": "Ha-ha-ha, I can do it!"})
        self.assertRedirects(
            response,
            "/auth/login/?next=/new/",
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )

    def test_edit_post(self):
        self.edit_text = "It`s new text. Work more anymore"
        self.post = Post.objects.create(text="Doesn`t matter", author=self.user)
        self.client.force_login(self.user)
        response = self.client.post(
            reverse(
                "post_edit", kwargs={"username": "testuser", "post_id": self.post.pk}
            ),
            {"text": self.edit_text},
        )
        response = self.client.get("/")
        self.assertContains(
            response,
            self.edit_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )
        response = self.client.get("/testuser/")
        self.assertContains(
            response,
            self.edit_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )
        response = self.client.get(f"/testuser/{self.post.pk}/")
        self.assertContains(
            response,
            self.edit_text,
            count=1,
            status_code=200,
            msg_prefix="",
            html=False,
        )

    def test_404(self):
        response = self.client.get("/12345qwerasfdzxcv09876/")
        self.assertEqual(response.status_code, 404)

    def test_cache(self):
        key = make_template_fragment_key("index_page", [1])
        self.assertFalse(cache.get(key))
        self.client.get("")
        self.assertTrue(cache.get(key))


class Image(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="TestUser@example.com", password="Test12345User"
        )
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title="ping-echo", slug="ping-group", description="Ping-ping-ping"
        )

    def test_image(self):
        with open("media/posts/tmlfrOv5Iz4.jpg", "rb") as fp:
            self.client.post(
                "/new/", {"group": self.group.pk, "text": "Ping", "image": fp}
            )
        response = self.client.get("/")
        self.assertContains(response, "<img", status_code=200)
        response = self.client.get("/testuser/1/")
        self.assertContains(response, "<img ", status_code=200)
        response = self.client.get("/testuser/")
        self.assertContains(response, "<img ", status_code=200)
        response = self.client.get("/group/ping-group/")
        self.assertContains(response, "<img ", status_code=200)

    def test_image_upload(self):
        with open("media/posts/to-do.txt", "rb") as fp:
            response = self.client.post(
                "/new/", {"group": self.group.pk, "text": "to-do", "image": fp}
            )
        self.assertFormError(
            response,
            "form",
            "image",
            "Загрузите правильное изображение. Файл, который вы загрузили, поврежден или не является изображением.",
        )


class Subscription(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.follower = User.objects.create_user(
            username="testfollower",
            email="TestFollower@example.com",
            password="TestFollower",
        )
        self.following = User.objects.create_user(
            username="testfollowing",
            email="TestFollowing@example.com",
            password="TestFollowing",
        )

    def test_follow_unfollow(self):
        self.client.force_login(self.follower)
        self.post = Post.objects.create(text="Test subscribe", author=self.following)
        response = self.client.get(f"/{self.following}/follow/")
        self.assertEqual(response.status_code, 302)
        response = Follow.objects.filter(user=self.follower)
        self.assertTrue(response)
        response = self.client.get(f"/{self.following}/unfollow/")
        self.assertEqual(response.status_code, 302)
        response = Follow.objects.filter(user=self.follower)
        self.assertFalse(response)

    def test_post_on_follow_page(self):
        self.text = "Test add new post to follow page"
        self.unfollower = User.objects.create_user(
            username="testunfollower",
            email="TestUnFollower@example.com",
            password="TestUnFollower",
        )
        self.client.force_login(self.follower)
        self.client.get(f"/{self.following}/follow/")
        self.post = Post.objects.create(text=self.text, author=self.following)
        response = self.client.get("/follow/")
        self.assertContains(
            response, self.text, count=1, status_code=200, msg_prefix="", html=False,
        )
        self.client.logout()
        self.client.force_login(self.unfollower)
        response = self.client.get("/follow/")
        self.assertNotContains(
            response, self.text, html=False,
        )

    def test_new_follow(self):
        self.text = "Test comments"
        self.post = Post.objects.create(text="Test post", author=self.following)
        response = self.client.post(
            f"/{self.following}/{self.post.pk}/comment/",
            {"text": "Ha-ha-ha, I can do it!"},
        )
        self.assertRedirects(
            response,
            f"/auth/login/?next=/{self.following}/{self.post.pk}/comment/",
            status_code=302,
            target_status_code=200,
            msg_prefix="",
            fetch_redirect_response=True,
        )
        self.client.force_login(self.follower)
        response = self.client.post(
            f"/{self.following}/{self.post.pk}/comment/", {"text": self.text}
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(f"/{self.following}/{self.post.pk}/")
        self.assertContains(
            response, self.text, count=1, status_code=200, msg_prefix="", html=False,
        )
