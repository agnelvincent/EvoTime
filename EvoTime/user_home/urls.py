from django.urls import path
from . import views
from Products.views import product_detail_view
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('showpage' , views.showpage , name = 'showpage'),
    path('', views.user_login, name='user_login'),  # This is your login view
    path('register/', views.user_signup, name='user_signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-password/verify-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('forgot-password/resend-otp/', views.resend_reset_otp, name='resend_reset_otp'),
    path('forgot-password/reset/', views.reset_password, name='reset_password'),
    path('home/', views.home_view, name='home'),
    path('brand/', views.brand_list, name='brand_list'),  # Brand list page
    path('brand/<int:brand_id>/', views.brand_products, name='brand_products'),
    path('products/' , views.all_products , name = 'all_products'),
    path('about/',views.about_us , name = 'about'),


    


    path('search/', views.search_products, name='search_products'),
    path('<int:id>/', product_detail_view, name='product_detail'),
    path('logout/', views.user_logout, name='user_logout'),
    path('account-overview/', views.account_overview, name='account_overview'),
    path("manage-address/", views.manage_address, name="manage_address"),
    path("add-address/", views.add_address, name="add_address"),
    path("edit-address/<int:address_id>/", views.edit_address, name="edit_address"),
    path("delete-address/<int:address_id>/", views.delete_address, name="delete_address"),
    path('orders/', views.order_list_view, name='order_list'),
    path('invoice/<int:item_id>/', views.generate_invoice, name='generate_invoice'),
    path('orders/item/<int:item_id>/', views.order_item_detail, name='order_item_detail'),
    path('orders/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),
    path('orders/item/<int:item_id>/return/', views.return_order_item, name='return_order_item'),
    path("wallet/", views.wallet_view, name="wallet_page"),
]

