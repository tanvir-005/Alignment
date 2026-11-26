import pytest

from todos.middleware.rate_limit import SimpleRateLimitMiddleware


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    SimpleRateLimitMiddleware.clear()
    yield
    SimpleRateLimitMiddleware.clear()


@pytest.fixture(autouse=True)
def _fast_hasher(settings):
    # PBKDF2 makes user creation slow; tests do not need a strong hasher.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
