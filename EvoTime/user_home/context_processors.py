from Cart.models import Cart
from django.conf import settings

def get_cart_item_count(request):
    cart_item_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item_count = cart.items.count()  # Count distinct product variants
    return {"cart_item_count": cart_item_count}

def razorpay_settings(request):
    return {
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID,
    }