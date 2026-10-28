from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from src.core.views import page_not_found, tinymce_disabled

urlpatterns = [
    path('tinymce/filebrowser/', tinymce_disabled),
    path('tinymce/flatpages_link_list/', tinymce_disabled),
    path('tinymce/', include('tinymce.urls')),
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('src.core.urls')),
    path('', include('src.network.urls')),
    path('', include('src.content.urls')),
    path('', include('src.leads.urls')),
    path('', include('src.blog.urls')),
    path('', include('src.reviews.urls')),
    path('', include('src.rates.urls')),
    path('', include('src.bot.urls')),
]

handler404 = page_not_found

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
