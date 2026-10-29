from .develop import *  # noqa: F403

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

SYNC_BRANCHES_ON_MIGRATE = False

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
NOTIFICATIONS_ASYNC = False
