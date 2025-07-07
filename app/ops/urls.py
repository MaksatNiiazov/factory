from django.urls import path, re_path

from ops import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.login_page, name='login'),
    path('logout', views.logout_page, name='logout'),
    path('register', views.register_page, name='register'),
    path('projects_list', views.ProjectList.as_view(), name='projects_list'),
    path('project_page/<pid>/', views.project_page, name='project_page'),
    path('project_page/<pid>/<pji_id>', views.project_page, name='project_page_with_pji'),
    path('projectitem/<pid>/<pji_id>', views.projectitem, name='projectitem'),
    path('tmp_composition/<pji_id>', views.tmp_composition, name='tmp_composition'),
    path('spring_choice/', views.spring_choice, name='spring_choice'),
    path('dn_size_diameter/', views.dn_size_diameter, name='dn_size_diameter'),
    path('dn_autocomplete/', views.DnAutocomplete.as_view(), name='dn_autocomplete'),
    path('clamp_material_autocomplete/', views.ClampMaterialAutocomplete.as_view(), name='clamp_material_autocomplete'),
    path('get_sketch/<pid>', views.get_sketch, name='get_sketch'),
    path('get_sketch_pdf/<int:project_item_id>', views.get_sketch_pdf, name='get_sketch_pdf'),
    path('download_sketch_pdf/<int:project_item_id>', views.download_sketch_pdf, name='download_sketch_pdf'),
    path('product_type_autocomplete/', views.DetailTypeAutocomplete.as_view(), name='product_type_autocomplete'),
    path('copy_pji/<pji_id>/', views.copy_pji, name='copy_pji'),
    path('delete_pji/<pji_id>/', views.delete_pji, name='delete_pji'),
    path('import_project/<int:project_id>/', views.import_project, name='import_project'),
]
