"""Static images: prefer a sibling WebP and report its intrinsic size."""

from functools import lru_cache
from pathlib import Path

from django.contrib.staticfiles import finders
from django.templatetags.static import static

HERO_SIZES = (
    '(max-width: 767px) calc(100vw - 32px), '
    'min(1380px, calc(100vw - 60px))'
)


def webp_name(name):
    return str(Path(name).with_suffix('.webp'))


def prefer_webp_name(name):
    if not name or Path(name).suffix.lower() == '.webp':
        return name
    candidate = webp_name(name)
    if finders.find(candidate):
        return candidate
    return name


def static_image(name):
    return static(prefer_webp_name(name))


def static_exists(name):
    if not name:
        return False
    return bool(finders.find(name) or finders.find(webp_name(name)))


@lru_cache(maxsize=256)
def static_size(name):
    found = finders.find(prefer_webp_name(name))
    if not found:
        return (0, 0)
    from PIL import Image

    with Image.open(found) as image:
        return image.size


def exact_static_size(name):
    found = finders.find(name) if name else None
    if not found:
        return (0, 0)
    from PIL import Image

    try:
        with Image.open(found) as image:
            return image.size
    except OSError:
        return (0, 0)


def field_size(field):
    if not field:
        return (0, 0)
    try:
        width = int(field.width or 0)
        height = int(field.height or 0)
    except (OSError, ValueError):
        return (0, 0)
    if width and height:
        return (width, height)
    return (0, 0)


def hero_pack(slug):
    fallback_name = prefer_webp_name('images/hero-kyiv.jpg')
    name = f'images/hero-{slug}.jpg'
    if not static_exists(name):
        name = 'images/hero-kyiv.jpg'
    chosen = prefer_webp_name(name)
    width, height = static_size(chosen)
    src = static(chosen)
    srcset = ''
    small = str(Path(chosen).with_name(f'{Path(chosen).stem}-800.webp'))
    if width > 800 and finders.find(small):
        srcset = f'{static(small)} 800w, {src} {width}w'
    return {
        'src': src,
        'srcset': srcset,
        'width': width or 1280,
        'height': height or 720,
        'fallback': static(fallback_name),
        'sizes': HERO_SIZES,
    }


def hero_for_city(city):
    image = getattr(city, 'banner_image', None) if city is not None else None
    if image:
        try:
            url = image.url
        except ValueError:
            url = ''
        if url:
            width, height = field_size(image)
            pack = hero_pack('kyiv')
            return {
                'src': url,
                'srcset': '',
                'width': width or 1600,
                'height': height or 900,
                'fallback': pack['fallback'],
                'sizes': HERO_SIZES,
            }
    slug = getattr(city, 'slug', None) or 'kyiv'
    return hero_pack(slug)
