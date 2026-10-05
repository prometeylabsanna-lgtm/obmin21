from django.contrib.auth.models import User
from django.db.utils import OperationalError, ProgrammingError


def ensure_vercel_admin() -> None:
    try:
        user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@obmin21.local'},
        )
        user.email = user.email or 'admin@obmin21.local'
        user.is_staff = True
        user.is_superuser = True
        user.set_password('admin')
        user.save()
    except (OperationalError, ProgrammingError):
        return
