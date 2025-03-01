from django.db import models
from user_home.models import Address, CustomUser
from django.core.exceptions import ValidationError


class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name

    def clean(self):
        if not self.name.strip():
            raise ValidationError("Category name cannot be empty or whitespace only.")

        if Category.objects.filter(name=self.name, is_active=True).exclude(id=self.id).exists():
            raise ValidationError(f"An active category with the name '{self.name}' already exists.")


class Product(models.Model):
    name = models.CharField(max_length=255)
    regular_price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField()
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    is_blocked = models.BooleanField(default=False)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    offer_percentage = models.PositiveIntegerField(default=0, help_text="Discount percentage for this product.")

    def __str__(self):
        return self.name

    def clean(self):
        if self.sales_price and self.sales_price > self.regular_price:
            raise ValidationError("Sales price cannot be greater than the regular price.")

        if not self.category:
            raise ValidationError("A category must be assigned to the product.")
        if not self.brand:
            raise ValidationError("A brand must be assigned to the product.")

        if not self.image:
            raise ValidationError("A primary product image must be provided.")

    def save(self, *args, **kwargs):
        # self.sales_price = self.calculate_sales_price()  # Automatically update sales price based on offers
        self.full_clean()
        super().save(*args, **kwargs)



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=100)  # Color now only in variants
    image1 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    image4 = models.ImageField(upload_to='variant_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.color}"

    def clean(self):

        # Ensure the variant color is unique for the product
        if ProductVariant.objects.filter(product=self.product, color=self.color).exclude(id=self.id).exists():
            raise ValidationError(f"A variant with the color '{self.color}' already exists for this product.")

        # Validate images
        if not any([self.image1, self.image2, self.image3, self.image4]):
            raise ValidationError("At least one variant image must be provided.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Trigger validation before saving
        super().save(*args, **kwargs)

