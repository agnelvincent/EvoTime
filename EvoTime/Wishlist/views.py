from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from user_home.views import block_superuser_navigation
from django.http import JsonResponse
from .models import Wishlist , WishlistItem
from Products.models import ProductVariant


@block_superuser_navigation
@never_cache
@login_required
def wishlist_view(request):
    if request.user.is_authenticated:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        return render(request, 'wishlist.html', {'wishlist': wishlist})
    return render(request, 'wishlist.html', {'wishlist': None})


@block_superuser_navigation
@never_cache
@login_required
def add_to_wishlist(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)

        wishlist_item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            variant=variant
        )

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@block_superuser_navigation
@never_cache
@login_required
def remove_from_wishlist(request, variant_id):
    if request.method == "POST":
        wishlist = Wishlist.objects.get(user=request.user)
        item = get_object_or_404(WishlistItem, wishlist=wishlist, variant_id=variant_id)
        item.delete()
        return JsonResponse({"success": True})
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


@block_superuser_navigation
@never_cache
@login_required
def wishlist_status(request):
    """Return a list of product variant IDs in the user's wishlist"""
    if request.user.is_authenticated:
        wishlist_items = WishlistItem.objects.filter(wishlist__user=request.user).values_list('variant_id', flat=True)
        return JsonResponse({'items': list(wishlist_items)})
    return JsonResponse({'items': []})
    

