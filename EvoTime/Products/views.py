from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Brand, Product, Address , Category, ProductVariant
from django.contrib.auth.hashers import make_password
from Cart.views import add_to_cart
from django.views.decorators.cache import never_cache
from user_home.views import block_superuser_navigation
from django.db import transaction
from django.http import JsonResponse

@block_superuser_navigation
@login_required
def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()  # Get all variants for this product
    
    print("Product:", product)  # Debugging
    print("Variants:", variants)  # Debugging
    
    context = {
        'product': product,
        'variants': variants,
    }
    return render(request, 'product_detail.html', context)




