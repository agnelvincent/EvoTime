from django.shortcuts import render, get_object_or_404
from Products.models import Product
from Cart.models import ProductReview
from django.db.models import Avg , Count

def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()  
    reviews = ProductReview.objects.filter(product=product)
    average_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Pass the raw queryset of rating counts
    rating_counts = (
        product.reviews.values('rating')
        .annotate(count=Count('rating'))
        .order_by('-rating')
    )
    
    context = {
        'product': product,
        'variants': variants,
        'reviews': reviews,
        'average_rating': average_rating,
        'rating_counts': rating_counts,  # Pass the queryset directly
    }
    return render(request, 'product_detail.html', context)


