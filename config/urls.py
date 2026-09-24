from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from src.core.sitemaps import sitemaps
from src.core.views import page_not_found

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('src.core.urls')),
    path('', include('src.network.urls')),
    path('', include('src.content.urls')),
    path('', include('src.leads.urls')),
    path('', include('src.blog.urls')),
    path('', include('src.reviews.urls')),
    path('', include('src.rates.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

handler404 = page_not_found

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
