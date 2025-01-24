from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Address
from admin_home.models import Product
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
import re
from .utils import send_otp

@never_cache
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

        # Check if the email or phone number already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_signup')

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "An account with this phone number already exists.")
            return redirect('user_signup')

        # Generate OTP and save user data in session
        otp = send_otp(email)  # Assuming this sends an OTP to the user's email
        print('OTP is:', otp)  # Debugging purposes (remove in production)

        user_data = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'otp': otp,
            'password': password
        }
        request.session['user_data'] = user_data

        return redirect('verify_otp')

    return render(request, 'signup.html')

@never_cache
def verify_otp(request):

    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        user_data = request.session.get('user_data', {})
        full_name = user_data.get('full_name')
        email = user_data.get('email')
        phone_number = user_data.get('phone_number')
        password = user_data.get('password')

        if user_data.get('otp') == entered_otp:
            user = CustomUser(
                full_name=full_name.strip(),
                email=email.strip(),
                password=make_password(password),  # Hash the password
            )

            # Save the user object to the database
            user.save()

            messages.success(request, "OTP verified successfully!")
            del request.session['user_data']  # Clear session
            # Log the user in
            login(request, user)
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP.")
            return redirect('verify_otp')
    return render(request, 'otp.html')

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

@never_cache
def user_logout(request):
    logout(request)
    return render(request, 'login.html')



