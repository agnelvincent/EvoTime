from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Address
from admin_home.models import Product
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
import re
from django.contrib.auth import login
from django.utils.crypto import get_random_string
from .utils import send_otp
from datetime import datetime, timedelta
from django.urls import reverse
from django.http import JsonResponse

def block_superuser_navigation(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('admin_dashboard'))  # Redirect to admin dashboard
        return view_func(request, *args, **kwargs)
    return wrapper

@never_cache
@block_superuser_navigation
def user_login(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')  # Use get to avoid KeyError
        password = request.POST.get('password')

        # Authenticate user
        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive. Please contact support.")
                return redirect('user_login')
            
            login(request, user)
            messages.success(request, "Login successful! Welcome back.")
            return redirect('home')  # Redirect to dashboard after successful login
        else:
            messages.error(request, "Invalid email or password. Please try again.")

    # Render the login page for GET requests or after a failed login
    return render(request, 'login.html')

@never_cache
@block_superuser_navigation
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # Retrieve form data
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validations
        if not full_name or len(full_name.strip()) < 3:
            messages.error(request, "Full name must be at least 3 characters long.")
            return redirect('user_signup')

        if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('user_signup')

        if not phone_number or not re.match(r'^\+?1?\d{9,15}$', phone_number):
            messages.error(request, "Please enter a valid phone number in the format '+999999999' (up to 15 digits).")
            return redirect('user_signup')

        if not password or len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('user_signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')

        # Check if email or phone already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_signup')

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "An account with this phone number already exists.")
            return redirect('user_signup')

        # Generate OTP and send email
        otp = send_otp(email)
        print('OTP is:', otp)  # Debugging purposes (remove in production)

        # Store user data and OTP in session
        user_data = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'otp': otp,
            'otp_created_at': datetime.now().isoformat(),  # Store OTP creation time
            'password': password,
        }
        request.session['user_data'] = user_data

        return redirect('verify_otp')

    return render(request, 'signup.html')

@block_superuser_navigation
@never_cache
def verify_otp(request):
    if request.user.is_authenticated:
        return redirect('home')

    user_data = request.session.get('user_data', {})
    if not user_data:
        messages.error(request, "Session expired or invalid access. Please sign up again.")
        return redirect('user_signup')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        # Check OTP timeout
        otp_created_at = datetime.fromisoformat(user_data.get('otp_created_at'))
        if datetime.now() > otp_created_at + timedelta(minutes=2):  # Timeout after 2 minutes
            messages.error(request, "OTP has expired. Please resend OTP.")
            return redirect('resend_otp')

        # Validate the entered OTP
        if user_data.get('otp') == entered_otp:
            # Create the user
            user = CustomUser.objects.create(
                full_name=user_data['full_name'].strip(),
                email=user_data['email'].strip(),
                phone_number=user_data['phone_number'].strip(),
                password=make_password(user_data['password']),  # Hash the password
            )

            # Log the user in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, "OTP verified successfully! Your account has been created.")
            del request.session['user_data']  # Clear session
            return redirect('home')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')

    return render(request, 'otp.html')


@never_cache
def resend_otp(request):
    user_data = request.session.get('user_data', {})
    if not user_data:
        messages.error(request, "Session expired or invalid access. Please sign up again.")
        return redirect('user_signup')

    # Resend the OTP
    new_otp = send_otp(user_data['email'])
    user_data['otp'] = new_otp  # Update OTP in session
    user_data['otp_created_at'] = datetime.now().isoformat()  # Reset OTP creation time
    request.session['user_data'] = user_data  # Save updated data in session

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_otp')


@block_superuser_navigation
@never_cache
@login_required
def home_view(request):
    """
    Renders the home page with all available products.
    """
    products = Product.objects.all()  # Fetch all products from the database
    context = {
        'products': products
    }
    return render(request, 'home.html', context)

@block_superuser_navigation
@never_cache
def product_detail_view(request, id):
    """
    Displays detailed information for a single product.
    """
    product = get_object_or_404(Product, id=id)  # Automatically handles the case if the product is not found
    context = {
        'product': product
    }
    return render(request, 'product_detail.html', context)


@block_superuser_navigation
@login_required
@never_cache
def account_overview(request):
    user = request.user  # Get current user

    if request.method == 'POST':
        profile_image = request.FILES.get('profile_image')
        dob = request.POST.get('dob')
        alternate_phone_number = request.POST.get('alternate_phone_number')

        # Update the fields
        if profile_image:
            user.profile_image = profile_image
        if dob:
            user.dob = dob
        if alternate_phone_number:
            user.alternate_phone_number = alternate_phone_number

        user.save()
        messages.success(request, 'Your details were successfully updated!')
        return redirect('account_overview')  # Redirect back to the same page

    context = {
        'profile_image': user.profile_image,
        'dob': user.dob,
        'alternate_phone_number': user.alternate_phone_number,
    }

    return render(request, 'user_profile/account_overview.html', context)

@block_superuser_navigation
@login_required
@never_cache
def manage_address(request):
    addresses = Address.objects.filter(user=request.user)  # Assuming a relationship between user and addresses
    return render(request, 'user_profile/address/manage_address.html', {'addresses': addresses})

@block_superuser_navigation
@login_required
@never_cache
def add_address(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address_line = request.POST.get("address_line")
        address_type = request.POST.get("address_type")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        
        Address.objects.create(
            user=request.user,
            name=name,
            phone=phone,
            address_line=address_line,
            address_type=address_type,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country
        )
        return redirect("manage_address")

    return render(request, "user_profile/address/add_address.html")


@block_superuser_navigation
@login_required
@never_cache
def edit_address(request, address_id):
    address = Address.objects.get(id=address_id, user=request.user)
    
    if request.method == "POST":
        address.name = request.POST.get("name")
        address.phone = request.POST.get("phone")
        address.address_line = request.POST.get("address_line")
        address.address_type = request.POST.get("address_type")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.postal_code = request.POST.get("postal_code")
        address.country = request.POST.get("country")
        address.save()
        return redirect("manage_address")

    return render(request, "user_profile/address/edit_address.html", {"address": address})


@block_superuser_navigation
@login_required
@never_cache
def delete_address(request, address_id):
    if request.method == "DELETE":
        try:
            address = Address.objects.get(id=address_id, user=request.user)
            address.delete()
            return JsonResponse({"success": True}, status=200)
        except Address.DoesNotExist:
            return JsonResponse({"error": "Address not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)



@block_superuser_navigation
@never_cache
def user_logout(request):
    logout(request)
    return redirect('user_login')



