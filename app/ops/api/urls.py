from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from ops.api import views

router = DefaultRouter()
router.register('projects', views.ProjectViewSet)
router.register('detail_types', views.DetailTypeViewSet)
router.register('variants', views.VariantViewSet, basename='variant')
router.register('fieldsets', views.FieldSetViewSet)
router.register('items', views.ItemViewSet)
router.register('attributes', views.AttributeViewSet)
router.register('base_compositions', views.BaseCompositionViewSet)

project_router = NestedSimpleRouter(router, 'projects', lookup='project')
project_router.register('items', views.ProjectItemViewSet, basename='project_item')

item_router = NestedSimpleRouter(router, 'items', lookup='parent')
item_router.register('children', views.ItemChildViewSet, basename='child')

detail_type_router = NestedSimpleRouter(router, 'detail_types', lookup='detail_type')
detail_type_router.register('variants', views.VariantViewSet, basename='variant')

urlpatterns = [
    path('', include(project_router.urls)),
    path('', include(item_router.urls)),
    path('', include(detail_type_router.urls)),
    path('', include(router.urls)),
    path('marking_template/compile/', views.MarkingTemplateCompileAPIView.as_view()),
    path('calculate/', views.CalculateLoadAPIView.as_view()),
    path('shock-calc/', views.ShockCalcAPIView.as_view(), name='shock-calc'),
    path('shock-calc/available-mounts/', views.AvailableMountsAPIView.as_view(), name='shock-calc-mounts'),
    path('shock-calc/available-top-mounts/', views.AvailableTopMountsAPIView.as_view(), name='shock-calc-top-mounts'),
    path('shock-calc/assembly-length/', views.AssemblyLengthAPIView.as_view(), name='shock-calc-assembly-length'),

]
