from django.urls import path

from kernel import views

urlpatterns = [
    path('languages/<lang>.json', views.front_language_json),
]
