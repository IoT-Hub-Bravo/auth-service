import pytest


@pytest.mark.django_db
class TestCreateUser:
    def test_creates_user_with_correct_fields(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="securepass123",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "client"
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_active is True

    def test_password_is_hashed(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="securepass123",
        )
        assert user.check_password("securepass123")
        assert user.password != "securepass123"

    def test_normalises_email(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="testuser3",
            email="test@EXAMPLE.COM",
            password="pass",
        )
        assert user.email == "test@example.com"

    def test_raises_if_username_missing(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with pytest.raises(ValueError, match="Username"):
            User.objects.create_user(username="", email="a@b.com", password="pass")

    def test_raises_if_email_missing(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with pytest.raises(ValueError, match="Email"):
            User.objects.create_user(username="u", email="", password="pass")


@pytest.mark.django_db
class TestCreateSuperuser:
    def test_creates_superuser_with_correct_flags(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == "admin"

    def test_raises_if_is_staff_false(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with pytest.raises(ValueError, match="is_staff"):
            User.objects.create_superuser(
                username="bad",
                email="bad@example.com",
                password="pass",
                is_staff=False,
            )

    def test_raises_if_is_superuser_false(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with pytest.raises(ValueError, match="is_superuser"):
            User.objects.create_superuser(
                username="bad2",
                email="bad2@example.com",
                password="pass",
                is_superuser=False,
            )
