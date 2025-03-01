from django.urls import path
from . import views

urlpatterns = [
    path('<int:id>/', views.product_detail_view, name='product_detail'),
]
