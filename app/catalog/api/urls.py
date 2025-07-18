from catalog.api.views import ActionHistoryViewSet, UserActionHistoryViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from catalog.api import views

router = DefaultRouter()
router.register('nominal_diameters', views.NominalDiameterViewSet)
router.register('pipe_diameters', views.PipeDiameterViewSet)
router.register('load_groups', views.LoadGroupViewSet)
router.register('materials', views.MaterialViewSet)
router.register('covering_types', views.CoveringTypeViewSet)
router.register('coverings', views.CoveringViewSet)
router.register('directories', views.DirectoryViewSet)
router.register('support-distances', views.SupportDistanceViewSet)
router.register('product-classes', views.ProductClassViewSet)
router.register('product-families', views.ProductFamilyViewSet)
router.register('loads', views.LoadViewSet)
router.register('spring-stiffnesses', views.SpringStiffnessViewSet)
router.register('pipe-mounting-groups', views.PipeMountingGroupViewSet)
router.register('pipe-mounting-rules', views.PipeMountingRuleViewSet)
router.register('component-groups', views.ComponentGroupViewSet)
router.register('spring-block-family-binding', views.SpringBlockFamilyBindingViewSet)
router.register('ssb-catalog', views.SSBCatalogViewSet)
router.register('ssg-catalog', views.SSGCatalogViewSet)
router.register("clamp-material-coefficients", views.ClampMaterialCoefficientViewSet)
router.register(r'action_history', ActionHistoryViewSet, basename='action_history')


directory_router = NestedSimpleRouter(router, 'directories', lookup='directory')
directory_router.register('fields', views.DirectoryFieldViewSet, basename='directory-fields')
directory_router.register('entries', views.DirectoryEntryViewSet, basename='directory-entries')

urlpatterns = [
    path('', include(directory_router.urls)),
    path('', include(router.urls)),
    path('users/<int:user_id>/action_history/',
         UserActionHistoryViewSet.as_view({'get': 'list'}),
         name='user-action-history'),
]
