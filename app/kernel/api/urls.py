from django.urls import path, include
from rest_framework.routers import DefaultRouter

from kernel.api import views

router = DefaultRouter()
router.register('groups', views.GroupViewSet)
router.register('users', views.UserViewSet)
router.register('organizations', views.OrganizationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('languages/', views.LanguagesAPIView.as_view()),
    path('timezones/', views.TimeZonesApiView.as_view()),
]
