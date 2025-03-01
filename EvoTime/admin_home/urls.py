from django.urls import path
from . import views
from .views import user_viewer, toggle_user_block

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    # Dashboard 
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('sales-data/', views.sales_data, name='sales_data'),
    path('download-pdf/', views.generate_pdf, name='download_pdf'),
    path('download-excel/', views.generate_excel, name='download_excel'),


    path('sales_report/' , views.sales_report , name = 'sales_report'),

    # Product Management
    path('products/', views.admin_product_view, name='admin_product'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/block/<int:product_id>/', views.block_product, name='block_product'),
    path('products/unblock/<int:product_id>/', views.unblock_product, name='unblock_product'),

    # Brand Management
    path('brands/add/', views.add_brand, name='add_brand'),

    # Variant Management
    path('products/<int:product_id>/variants/', views.manage_variants, name='manage_variants'),
    path('products/<int:product_id>/variants/add/', views.add_variant, name='add_variant'),
    path('variants/<int:variant_id>/edit/', views.edit_variant, name='edit_variant'),
    path('variants/<int:variant_id>/delete/', views.delete_variant, name='delete_variant'),

    # Category Management
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/toggle/<int:category_id>/', views.toggle_category_status, name='toggle_category'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit_category'),

    # User Management
    path('users/', views.user_viewer, name='user_viewer'),
    path('users/toggle-block/<int:user_id>/', views.toggle_user_block, name='toggle_user_block'),

    # Order Management
    path('orders/', views.admin_order_list_view, name='admin_order_list_view'),
    path('orders/change-status/<int:order_item_id>/', views.admin_change_order_item_status_view, name='admin_change_orderitem_status'),
    path('return-requests/', views.admin_return_requests, name='admin_return_requests'),
    path('handle-return-request/<int:item_id>/', views.admin_handle_return_request, name='admin_handle_return_request'),

    #Coupon Management
    path('coupons/', views.coupon_management, name='coupon_management'),
    path('coupons/details/<int:coupon_id>/', views.get_coupon_details, name='get_coupon_details'),
    path('coupons/delete/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),
]