from django.urls import path
from . import views


urlpatterns = [
    path('',views.user_login,name = 'user_login'),
    path('register/',views.user_signup, name='user_signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('home/', views.home_view, name='home'),
    path('product/<int:id>/', views.product_detail_view, name='product_detail'),
    path('logout/',views.user_logout , name='user_logout'),
    path('account-overview/', views.account_overview, name='account_overview'),
    path("manage-address/", views.manage_address, name="manage_address"),
    path("add-address/", views.add_address, name="add_address"),
    path("edit-address/<int:address_id>/", views.edit_address, name="edit_address"),
    path("delete-address/<int:address_id>/", views.delete_address, name="delete_address"),
]

