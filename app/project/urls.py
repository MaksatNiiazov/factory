from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

from kernel.api import API_DESCRIPTION

SchemaView = get_schema_view(
    openapi.Info(
        title='Witzenmann OPS',
        default_version='v1',
        description=API_DESCRIPTION,
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = i18n_patterns(
    path('admin/', admin.site.urls),
    path('ops/', include('ops.urls')),
) + [
    re_path(r'^api(?P<format>\.json|\.yaml)$', SchemaView.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^api/$', SchemaView.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/', include('kernel.api.urls')),
    path('api/', include('ops.api.urls')),
    path('api/', include('catalog.api.urls')),
    path('api/', include('taskmanager.api.urls')),
    re_path(r'^_nested_admin/', include('nested_admin.urls')),
    path('kernel/', include('kernel.urls')),
    path("i18n/", include("django.conf.urls.i18n")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
