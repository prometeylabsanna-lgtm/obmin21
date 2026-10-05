from django.contrib.auth.models import User
from django.db.utils import OperationalError, ProgrammingError


def ensure_vercel_admin() -> None:
    try:
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@obmin21.local'},
        )
        dirty = created
        if user.email != 'admin@obmin21.local':
            user.email = 'admin@obmin21.local'
            dirty = True
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            dirty = True
        if created or not user.check_password('admin'):
            user.set_password('admin')
            dirty = True
        if dirty:
            user.save()
    except (OperationalError, ProgrammingError):
        return
