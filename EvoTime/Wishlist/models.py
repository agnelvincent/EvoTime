from django.db import models
from django.db import models
from user_home.models import CustomUser
from Products.models import ProductVariant


class Wishlist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist of {self.user.username}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='wishlisted_items')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'variant')  # Prevents duplicate items in the same wishlist

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.color} (Wishlist: {self.wishlist.user.username})"


# Create your models here.
