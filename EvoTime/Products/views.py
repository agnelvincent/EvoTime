from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from user_home.views import block_superuser_navigation
from Products.models import Product
from Cart.models import ProductReview
from django.db.models import Avg

@block_superuser_navigation
@never_cache
@login_required
def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()  
    reviews = ProductReview.objects.filter(product = product)
    average_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']

    
    context = {
        'product': product,
        'variants': variants,
        'reviews': reviews,  
        'average_rating' : average_rating
    }
    return render(request, 'product_detail.html', context)


