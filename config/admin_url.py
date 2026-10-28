_DEFAULT_ADMIN_URL = 'admin/'


def normalize(value):
    """Strip a leading slash, keep one trailing slash, blank values -> admin/."""
    if value is None:
        return _DEFAULT_ADMIN_URL
    text = str(value).strip().lstrip('/')
    if not text:
        return _DEFAULT_ADMIN_URL
    if not text.endswith('/'):
        text += '/'
    return text
