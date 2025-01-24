from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


    

class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Only auto_now_add
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        # Prevent empty category names
        if not self.name.strip():
            raise ValidationError("Category name cannot be empty or whitespace only.")

        # Ensure unique category names for active categories
        if Category.objects.filter(name=self.name, is_active=True).exclude(id=self.id).exists():
            raise ValidationError(f"An active category with the name '{self.name}' already exists.")


class Product(models.Model):
    name = models.CharField(max_length=255)
    regular_price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField()
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    is_blocked = models.BooleanField(default=False)
    image1 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image4 = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    def clean(self):
        # Ensure the sales price is not greater than the regular price
        if self.sales_price and self.sales_price > self.regular_price:
            raise ValidationError("Sales price cannot be greater than the regular price.")

        # Ensure the product has a category and brand
        if not self.category:
            raise ValidationError("A category must be assigned to the product.")
        if not self.brand:
            raise ValidationError("A brand must be assigned to the product.")

        # Validate images
        if not any([self.image1, self.image2, self.image3, self.image4]):
            raise ValidationError("At least one product image must be provided.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Trigger validation before saving
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=100)
    image1 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image4 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.color}"

    def clean(self):
        # Ensure the variant stock is not greater than the product stock
        if self.stock > self.product.stock:
            raise ValidationError(
                f"Variant stock ({self.stock}) cannot exceed the product stock ({self.product.stock})."
            )

        # Ensure the variant color is unique for the product
        if ProductVariant.objects.filter(product=self.product, color=self.color).exclude(id=self.id).exists():
            raise ValidationError(f"A variant with the color '{self.color}' already exists for this product.")

        # Validate images
        if not any([self.image1, self.image2, self.image3, self.image4]):
            raise ValidationError("At least one variant image must be provided.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Trigger validation before saving
        super().save(*args, **kwargs)
