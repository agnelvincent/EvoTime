import re
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Avg


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

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
        """Cascade: re-compute sales_price for every product in this category."""
        super().save(*args, **kwargs)
        for product in self.products.select_related('brand', 'category').all():
            try:
                product.save()
            except Exception:
                # Don't let a bad product block the category save
                pass


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

class Brand(models.Model):
    name             = models.CharField(max_length=255, unique=True)
    description      = models.TextField(blank=True)
    offer_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Discount percentage applied to all products of this brand."
    )
    is_blocked       = models.BooleanField(default=False)           # was missing → caused runtime crash
    Brand_image      = models.ImageField(upload_to='brand_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Cascade: re-compute sales_price for every product of this brand."""
        super().save(*args, **kwargs)
        for product in self.products.select_related('brand', 'category').all():
            try:
                product.save()
            except Exception:
                # Don't let a bad product block the brand save
                pass


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(models.Model):
    name             = models.CharField(max_length=255)
    regular_price    = models.DecimalField(max_digits=10, decimal_places=2)
    # sales_price is always auto-computed in save(); never set it manually.
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

    def __str__(self):
        return self.name

    # ------------------------------------------------------------------
    # Offer / price helpers
    # ------------------------------------------------------------------

    def get_applicable_offer(self):
        """
        Return the single highest offer percentage across three tiers:
          category offer  →  brand offer  →  product offer
        """
        category_offer = self.category.offer_percentage if self.category else 0
        brand_offer    = self.brand.offer_percentage    if self.brand    else 0
        product_offer  = self.offer_percentage
        return max(category_offer, brand_offer, product_offer)

    def calculate_sales_price(self):
        """Compute sales price from the highest applicable offer."""
        highest_offer = self.get_applicable_offer()
        if highest_offer > 0:
            return self.regular_price * (1 - highest_offer / 100)
        return self.regular_price   # no offer → same as regular price

    # ------------------------------------------------------------------
    # Rating helpers
    # ------------------------------------------------------------------

    def average_rating(self):
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    def review_count(self):
        return self.reviews.count()

    # ------------------------------------------------------------------
    # Validation & save
    # ------------------------------------------------------------------

    def clean(self):
        if not self.category:
            raise ValidationError("A category must be assigned to the product.")
        if not self.brand:
            raise ValidationError("A brand must be assigned to the product.")
        if not self.image:
            raise ValidationError("A primary product image must be provided.")

    def save(self, *args, **kwargs):
        # Always auto-compute; admin forms must NOT write sales_price directly.
        self.sales_price = self.calculate_sales_price()
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ProductVariant
# ---------------------------------------------------------------------------

class ProductVariant(models.Model):
    """
    One orderable SKU of a product.
    Attributes (color, size, strap material …) live in VariantAttribute.
    Images live in VariantImage.
    """
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
        """Convenience: get a single attribute value by name (case-insensitive)."""
        attr = self.attributes.filter(attribute_name__iexact=name).first()
        return attr.attribute_value if attr else None

    def get_primary_image(self):
        """Return the lowest sort_order image, or None."""
        return self.images.order_by('sort_order').first()

    def clean(self):
        # Variant name must be unique within the same product
        if ProductVariant.objects.filter(
            product=self.product, name__iexact=self.name
        ).exclude(id=self.id).exists():
            raise ValidationError(
                f"A variant named '{self.name}' already exists for this product."
            )

    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            slug = re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-')
            self.sku = f"EVO-{self.product_id}-{slug}"[:100]
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# VariantAttribute  (replaces the single 'color' field)
# ---------------------------------------------------------------------------

class VariantAttribute(models.Model):
    """
    Flexible key-value attributes per variant.
    Examples:
        attribute_name="color"          attribute_value="Midnight Black"
        attribute_name="case_size"      attribute_value="42mm"
        attribute_name="strap_material" attribute_value="Leather"
        attribute_name="dial_color"     attribute_value="White"
    """
    variant         = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='attributes')
    attribute_name  = models.CharField(max_length=100)
    attribute_value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('variant', 'attribute_name')
        ordering        = ['attribute_name']

    def __str__(self):
        return f"{self.variant} | {self.attribute_name}: {self.attribute_value}"


# ---------------------------------------------------------------------------
# VariantImage  (replaces flat image1/image2/image3/image4 columns)
# ---------------------------------------------------------------------------

class VariantImage(models.Model):
    """
    An ordered gallery of images per variant.
    No cap on image count; reorderable via sort_order.
    """
    variant    = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='variant_images/')
    sort_order = models.PositiveIntegerField(default=0)
    alt_text   = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.variant} | image #{self.sort_order}"
