# rocky_herbals/urls.py
from django.contrib import admin
from django.urls import path, include   # include import செய்ய வேண்டும்
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),              # Django default admin
    path('', include('herbalapp.urls')),          # herbalapp urls connect
]

# Serve media files during development (product images, uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

