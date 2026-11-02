from .develop import *  # noqa: F403

# Тести завжди на стандартному префіксі, незалежно від ADMIN_URL у середовищі.
ADMIN_URL = 'admin/'
UNFOLD['LOGIN']['redirect_after'] = '/' + ADMIN_URL  # noqa: F405

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

SYNC_BRANCHES_ON_MIGRATE = False

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
NOTIFICATIONS_ASYNC = False
