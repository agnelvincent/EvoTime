import re
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Avg

class Category(models.Model):
    name               = models.CharField(max_length=255)
    is_active          = models.BooleanField(default=True)
    offer_percentage   = models.PositiveIntegerField(
        default=0,
        help_text="Discount percentage applied to all products in this category."
    )
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)
    Category_image     = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    def clean(self):
        if not self.name.strip():
            raise ValidationError("Category name cannot be empty or whitespace only.")

        if Category.objects.filter(name=self.name, is_active=True).exclude(id=self.id).exists():
            raise ValidationError(f"An active category with the name '{self.name}' already exists.")

        if self.offer_percentage < 0 or self.offer_percentage > 100:
            raise ValidationError("Offer percentage must be between 0 and 100.")

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        for product in self.products.select_related('brand').all():
            try:
                product.save()
            except Exception as e:
                pass


class Brand(models.Model):
    name             = models.CharField(max_length=255, unique=True)
    description      = models.TextField(blank=True)
    offer_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Discount percentage applied to all products of this brand."
    )
    is_blocked       = models.BooleanField(default=False)          
    Brand_image      = models.ImageField(upload_to='brand_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for product in self.products.select_related('category').all():
            try:
                product.save()
            except Exception:
                pass


class Product(models.Model):
    name             = models.CharField(max_length=255)
    regular_price    = models.DecimalField(max_digits=10, decimal_places=2)
    sales_price      = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description      = models.TextField()
    brand            = models.ForeignKey(Brand,    on_delete=models.SET_NULL, null=True, related_name='products')
    category         = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    is_blocked       = models.BooleanField(default=False)
    image            = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    offer_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Product-level discount percentage."
    )
    applied_offer = models.PositiveIntegerField(
        default=0,
        help_text="applied discount percentage."
    )

    def __str__(self):
        return self.name

    def get_applicable_offer(self):
        category_offer = self.category.offer_percentage if self.category else 0
        brand_offer    = self.brand.offer_percentage    if self.brand    else 0
        product_offer  = self.offer_percentage
        self.applied_offer = max(category_offer, brand_offer, product_offer)
        return self.applied_offer

    def calculate_sales_price(self):
        from decimal import Decimal, ROUND_HALF_UP
        highest_offer = self.get_applicable_offer()
        if highest_offer > 0:
            discount_percentage = Decimal(str(highest_offer)) / Decimal('100')
            discount_multiplier = Decimal('1') - discount_percentage
            new_price = self.regular_price * discount_multiplier
            return new_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return self.regular_price 

    def average_rating(self):
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    def review_count(self):
        return self.reviews.count()

    def clean(self):
        if not self.category:
            raise ValidationError("A category must be assigned to the product.")
        if not self.brand:
            raise ValidationError("A brand must be assigned to the product.")
        if not self.image:
            raise ValidationError("A primary product image must be provided.")

    def save(self, *args, **kwargs):

        self.sales_price = self.calculate_sales_price()
        self.full_clean()
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product   = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name      = models.CharField(
        max_length=255,
        help_text="Human-readable display name, e.g. 'Midnight Black – 42mm Leather'."
    )
    sku       = models.CharField(max_length=100, unique=True, blank=True)
    stock     = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    def get_attribute(self, name):
        attr = self.attributes.filter(attribute_name__iexact=name).first()
        return attr.attribute_value if attr else None

    def get_primary_image(self):
        return self.images.order_by('sort_order').first()

    def clean(self):
        if ProductVariant.objects.filter(
            product=self.product, name__iexact=self.name
        ).exclude(id=self.id).exists():
            raise ValidationError(
                f"A variant named '{self.name}' already exists for this product."
            )

    def save(self, *args, **kwargs):
        if not self.sku:
            slug = re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-')
            self.sku = f"EVO-{self.product_id}-{slug}"[:100]
        self.full_clean()
        super().save(*args, **kwargs)


class VariantAttribute(models.Model):
    variant         = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='attributes')
    attribute_name  = models.CharField(max_length=100)
    attribute_value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('variant', 'attribute_name')
        ordering        = ['attribute_name']

    def __str__(self):
        return f"{self.variant} | {self.attribute_name}: {self.attribute_value}"


class VariantImage(models.Model):

    variant    = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='variant_images/')
    sort_order = models.PositiveIntegerField(default=0)
    alt_text   = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.variant} | image #{self.sort_order}"
