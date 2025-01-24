from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Create your models here.

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    password = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(8)]  # Ensure password is at least 8 characters
    )
    is_blocked = models.BooleanField(default=False)
    profile_complete = models.BooleanField(default=False)
    
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(
        max_length=15, 
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', _('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'))]
    )
    alternate_phone_number = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def clean(self):
        # Custom validation example
        if not self.full_name:
            raise ValidationError({'full_name': _('Full name cannot be empty.')})
        
        # Custom logic for profile completeness
        if not self.profile_complete and not self.full_name:
            raise ValidationError(_('Please complete your profile by adding a full name.'))

class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="addresses")
    address_line = models.CharField(max_length=255)
    address_type = models.CharField(max_length=50, choices=(('home', 'Home'), ('work', 'Work')), default='home')
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
