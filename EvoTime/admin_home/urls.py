from django.urls import path
from . import views
from .views import user_viewer, toggle_user_block

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('home/',views.admin_dashboard , name='admin_dashboard'),
    path('products/', views.admin_product, name='admin_product'),
    path('products/add-product/', views.add_product, name='add_product'),
    path('products/add-product/add-brands/', views.add_brand, name='add_brands'),
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('toggle-category/<int:category_id>/', views.toggle_category_status, name='toggle_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('block/<int:product_id>/', views.block_product, name='block_product'),
    path('unblock/<int:product_id>/', views.unblock_product, name='unblock_product'),
    path('users/', user_viewer, name='user_viewer'),
    path('toggle-block/<int:user_id>/', toggle_user_block, name='toggle_user_block'),
    path('admin/logout/', views.admin_logout, name='admin_logout')
]
