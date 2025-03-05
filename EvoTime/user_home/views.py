from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Address
from Products.models import Product, Brand , Category
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
import re
from django.contrib.auth import login
from .utils import send_otp
from datetime import datetime, timedelta
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from Cart.models import Order , OrderItem
from Wishlist.models import Wishlist
from django.core.paginator import Paginator
from datetime import timedelta
from Cart.models import Wallet , ProductReview
from django.db import transaction
from django.urls import reverse
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def block_superuser_navigation(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect(reverse('admin_dashboard'))  # Redirect to admin dashboard
        return view_func(request, *args, **kwargs)
    return wrapper


def showpage(request):
    return render(request , 'showpage.html')


@never_cache
@block_superuser_navigation
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    login_error = None  # Initialize error variable

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                login_error = "This account is inactive. Please contact support."
            else:
                login(request, user)
                return redirect('home')
        else:
            login_error = "Invalid email or password. Please try again."

    # Render the login page with the error if any
    return render(request, 'login.html', {'login_error': login_error})

@never_cache
@block_superuser_navigation
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        # Retrieve form data
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validations
        if len(full_name) < 3:
            messages.error(request, "Full name must be at least 3 characters long.")
            return redirect('user_signup')

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('user_signup')

        if not re.match(r'^\+?1?\d{9,15}$', phone_number):
            messages.error(request, "Please enter a valid phone number (up to 15 digits).")
            return redirect('user_signup')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('user_signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')

        # Check if email or phone already exists
        if CustomUser .objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_signup')

        if CustomUser .objects.filter(phone_number=phone_number).exists():
            messages.error(request, "An account with this phone number already exists.")
            return redirect('user_signup')

        # Clear any previous session data
        request.session.flush()

        # Generate OTP and send email
        otp = send_otp(email)
        print('OTP is:', otp)  # Debugging purposes (remove in production)

        # Store user data and OTP in session
        user_data = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'otp': otp,
            'otp_created_at': timezone.now().isoformat(),  # Use timezone.now() here
            'password': make_password(password),  # Hash the password
        }
        request.session['user_data'] = user_data

        return redirect('verify_otp')

    return render(request, 'signup.html')




@never_cache
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        user_data = request.session.get('user_data')

        if not user_data:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect('user_signup')

        otp = user_data.get('otp')
        otp_created_at = datetime.fromisoformat(user_data.get('otp_created_at'))

        # Check if OTP is expired
        if timezone.now() > otp_created_at + timedelta(minutes=2):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect('resend_otp')

        if entered_otp == otp:
            # Create the user
            user = CustomUser (
                full_name=user_data['full_name'],
                email=user_data['email'],
                phone_number=user_data['phone_number'],
                password=user_data['password']
            )
            user.save()

            # Clear session data
            request.session.flush()

            # Login the user with the specified backend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, "Account created successfully! You are now logged in.")
            return redirect('home')  # Redirect to home page
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    user_data = request.session.get('user_data')
    return render(request, 'verify_otp.html', {'user_data': user_data})


@never_cache
def resend_otp(request):
    user_data = request.session.get('user_data')

    if not user_data:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('user_signup')

    # Generate a new OTP and send it
    otp = send_otp(user_data['email'])
    print('New OTP is:', otp)  # Debugging purposes (remove in production)

    # Update the OTP in session
    user_data['otp'] = otp
    user_data['otp_created_at'] = timezone.now().isoformat()  # Update OTP creation time
    request.session['user_data'] = user_data

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_otp')


@never_cache
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            # Generate OTP using your existing function
            otp = send_otp(email)
            
            # Store data in session
            reset_data = {
                'email': email,
                'otp': otp,
                'otp_created_at': timezone.now().isoformat(),
                'is_password_reset': True
            }
            request.session['reset_data'] = reset_data
            
            messages.success(request, 'OTP has been sent to your email.')
            return redirect('verify_reset_otp')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    return render(request, 'password/forgot_password.html')


@never_cache
def verify_reset_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        reset_data = request.session.get('reset_data')

        if not reset_data:
            messages.error(request, "Session expired. Please try again.")
            return redirect('forgot_password')

        otp = reset_data.get('otp')
        otp_created_at = datetime.fromisoformat(reset_data.get('otp_created_at'))

        # Check if OTP is expired (2 minutes)
        if timezone.now() > otp_created_at + timedelta(minutes=2):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect('resend_reset_otp')

        if entered_otp == otp:
            reset_data['otp_verified'] = True
            request.session['reset_data'] = reset_data
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    reset_data = request.session.get('reset_data')
    return render(request, 'password/verify_reset_otp.html', {'reset_data': reset_data})


@never_cache
def resend_reset_otp(request):
    reset_data = request.session.get('reset_data')

    if not reset_data:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    email = reset_data['email']
    otp = send_otp(email)

    reset_data['otp'] = otp
    reset_data['otp_created_at'] = timezone.now().isoformat()
    request.session['reset_data'] = reset_data

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_reset_otp')


@never_cache
def reset_password(request):
    reset_data = request.session.get('reset_data')
    
    if not reset_data or not reset_data.get('otp_verified'):
        messages.error(request, "Please verify your OTP first")
        return redirect('forgot_password')
        
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'password/reset_password.html')
            
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'password/reset_password.html')
            
        try:
            user = CustomUser.objects.get(email=reset_data['email'])
            user.set_password(new_password)
            user.save()
            
            # Clear session data
            request.session.flush()
            
            messages.success(request, 'Password has been reset successfully')
            return redirect('user_login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Something went wrong. Please try again.')
            return redirect('forgot_password')
            
    return render(request, 'password/reset_password.html')


@block_superuser_navigation
@never_cache
@login_required
def home_view(request):


    # Fetch products with related variants
    products = Product.objects.prefetch_related('variants').all()
    new_products = Product.objects.all().order_by('-created_at')[:8]

    user_wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            user_wishlist_variant_ids = wishlist.items.values_list('variant_id', flat=True)


    # Set up pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')  # Get the page number from the URL
    products_page = paginator.get_page(page_number)  # Get the products for the current page

    context = {
        'products': products_page,  # Pass the paginated products to the template
        'brands': Brand.objects.all(),  # Pass all brands for filtering
        'categories': Category.objects.all(),  # Pass all categories for filtering
        'user_wishlist_variant_ids': user_wishlist_variant_ids,
    }
    return render(request, 'home.html', context)


@block_superuser_navigation
@never_cache
@login_required
def all_products(request):
    products = Product.objects.filter(is_blocked=False)
    brands = Brand.objects.all()
    categories = Category.objects.filter(is_active=True)

    # Apply filters
    brand_id = request.GET.get('brand')
    category_id = request.GET.get('category')
    price_range = request.GET.get('price')

    if brand_id:
        products = products.filter(brand_id=brand_id)
    if category_id:
        products = products.filter(category_id=category_id)
    if price_range:
        min_price, max_price = price_range.split('-')
        if min_price:
            products = products.filter(regular_price__gte=min_price)
        if max_price:
            products = products.filter(regular_price__lte=max_price)

    context = {
        'products': products,
        'brands': brands,
        'categories': categories,
    }
    return render(request, 'all_products.html', context)


@block_superuser_navigation
@never_cache
@login_required
def brand_list(request):
    brands = Brand.objects.all()  # Fetch all brands
    return render(request, 'brand.html', {'brands': brands})


@block_superuser_navigation
@never_cache
@login_required
def brand_products(request, brand_id):
    try:
        brand = Brand.objects.get(id=brand_id)
        products = Product.objects.filter(brand=brand, is_blocked=False)

        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'regular_price': str(product.regular_price),
                'sales_price': str(product.sales_price) if product.sales_price else str(product.regular_price),
                'image': product.image.url if product.image else '',
                'discount': round(((product.regular_price - product.sales_price) / product.regular_price) * 100, 2) if product.sales_price else 0,
                'variants': [{'id': variant.id, 'stock': variant.stock} for variant in product.variants.all()]
            })

        return JsonResponse({
            'brand': {
                'id': brand.id,
                'name': brand.name,
                'description': brand.description
            },
            'products': product_list
        })
    except Brand.DoesNotExist:
        return JsonResponse({'error': 'Brand not found'}, status=404)

@block_superuser_navigation
@never_cache
@login_required    
def about_us(request):
    return render(request , 'about.html')


@block_superuser_navigation
@never_cache
@login_required
def account_overview(request):
    user = request.user  # Get the logged-in user

    if request.method == "POST":
        # Retrieve form data
        dob = request.POST.get("dob")
        alternate_phone_number = request.POST.get("alternate_phone_number")
        profile_image = request.FILES.get("profile_image")

        errors = False  # Flag to track validation errors

        # Validate Date of Birth (must be a valid date and in the past)
        if dob:
            try:
                dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
                if dob_date >= datetime.today().date():
                    messages.error(request, "Date of birth cannot be in the future!")
                    errors = True
                else:
                    user.dob = dob_date
            except ValueError:
                messages.error(request, "Invalid date format! Use YYYY-MM-DD.")
                errors = True

        # Validate Alternate Phone Number (must be numeric and 10-15 digits)
        if alternate_phone_number:
            if not re.match(r"^\d{10,15}$", alternate_phone_number):
                messages.error(request, "Alternate phone number must be 10-15 digits long.")
                errors = True
            else:
                user.alternate_phone_number = alternate_phone_number

        # Validate Profile Image (optional, but must be an image file)
        if profile_image:
            if not profile_image.content_type.startswith("image"):
                messages.error(request, "Invalid file type! Please upload an image.")
                errors = True
            else:
                user.profile_image = profile_image  # Save uploaded image

        # If no errors, save the user model and redirect
        if not errors:
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("account_overview")

    # Prepopulate the form with existing data
    context = {
        "profile_image": user.profile_image,
        "dob": user.dob,
        "alternate_phone_number": user.alternate_phone_number,
    }

    return render(request, "user_profile/account_overview.html", context)



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
        # Extract data from the request
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address_line = request.POST.get("address_line")
        address_type = request.POST.get("address_type")
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        
        # Create the address
        try:
            address = Address(
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
            address.save()  # Explicitly save the address instance
            
            # Return success with address data
            return JsonResponse({
                "success": True,
                "address": {
                    "id": address.id,
                    "name": address.name,
                    "phone": address.phone,
                    "address_line": address.address_line,
                    "city": address.city,
                    "state": address.state,
                    "postal_code": address.postal_code,
                    "country": address.country
                }
            }, status=201)
            
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=400)

@block_superuser_navigation
@login_required
@never_cache
def edit_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == "POST":
        # Update the address fields
        address.name = request.POST.get("name")
        address.phone = request.POST.get("phone")
        address.address_line = request.POST.get("address_line")
        address.address_type = request.POST.get("address_type")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.postal_code = request.POST.get("postal_code")
        address.country = request.POST.get("country")
        

        try:
            address.save() 
            return JsonResponse({"success": True}, status=200) 
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)  # Bad Request

    return JsonResponse({"error": "Invalid request method."}, status=400)


@block_superuser_navigation
@login_required
@never_cache
def delete_address(request, address_id):
    if request.method == "DELETE":
        # Use get_object_or_404 to handle the case where the address does not exist
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Check if the address is used in any orders
        if address.orders.exists():
            return JsonResponse({
                "error": "This address cannot be deleted as it is associated with one or more orders. Please add a new address instead.",
                "type": "address_in_use"
            }, status=400)
        
        try:
            address.delete()
            return JsonResponse({"success": True}, status=200)
        except Exception as e:
            return JsonResponse({
                "error": "An error occurred while deleting the address.",
                "details": str(e)
            }, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=400)



@block_superuser_navigation
@never_cache
@login_required
def order_list_view(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders_list = orders_list.filter(status__status=status)

    # Pagination
    paginator = Paginator(orders_list, 5)  # Show 10 orders per page
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    return render(request, 'user_profile/order_list.html', {'orders': orders})

@block_superuser_navigation
@never_cache
@login_required
def generate_invoice(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    user = item.order.user
    address = item.order.shipping_address  # Use the shipping address from the order

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{item.id}.pdf"'

    # Create the PDF object, using the response object as its "file."
    pdf = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        textColor=colors.darkblue
    )
    
    normal_style = styles['BodyText']
    
    # Create the content
    content = []
    
    # Add title
    content.append(Paragraph("Invoice", title_style))
    content.append(Spacer(1, 12))
    
    # Add store information (dynamic)
    store_name = "EvoTime"  # Replace with dynamic data (e.g., from a Store model)
    store_address = "Ivrine Stafford Texas North America"  # Replace with dynamic data
    content.append(Paragraph(store_name, header_style))
    content.append(Paragraph(store_address, normal_style))
    content.append(Spacer(1, 12))
    
    # Add customer information
    content.append(Paragraph("Bill To:", header_style))
    content.append(Paragraph(f"{user.full_name}", normal_style))
    content.append(Paragraph(f"Email: {user.email}", normal_style))  # Add email
    if address:
        content.append(Paragraph(f"{address.address_line}", normal_style))
        content.append(Paragraph(f"{address.city}, {address.state} {address.postal_code}", normal_style))
        content.append(Paragraph(f"{address.country}", normal_style))
    content.append(Spacer(1, 12))
    
    # Add order details
    content.append(Paragraph("Order Details", header_style))
    order_details = [
        ["Order ID", item.order.id],
        ["Product", Paragraph(item.product_variant.product.name, normal_style)],  # Wrap product name
        ["Quantity", item.quantity],
        ["Price per unit", f"${item.product_variant.product.sales_price}"],
        ["Total Price", f"${item.total_price}"]
    ]
    
    # Define column widths
    col_widths = [1.5 * inch, 4.5 * inch]  # Adjust column widths to fit content
    
    table = Table(order_details, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap
    ]))
    
    content.append(table)
    content.append(Spacer(1, 12))
    
    # Add thank you message
    content.append(Paragraph("Thank you for your purchase!", normal_style))
    
    # Build the PDF
    pdf.build(content)
    
    return response




@block_superuser_navigation
@never_cache
@login_required
def order_item_detail(request, item_id):
    """
    View for displaying detailed information about a specific order item
    """
    # Get the order item and make sure it belongs to the current user
    order_item = get_object_or_404(OrderItem, id=item_id)
    
    # Security check: Make sure the order belongs to the current user
    if order_item.order.user != request.user:
        messages.error(request, "You don't have permission to view this order item.")
        return redirect('order_list')
        
    context = {
        'order_item': order_item,
    }
    
    return render(request, 'user_profile/order_item_detail.html', context)


@block_superuser_navigation
@never_cache
@login_required
def cancel_order_item(request, item_id):
    """
    View for cancelling a specific order item and processing a wallet refund if payment was completed.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('order_list')

    order_item = get_object_or_404(OrderItem, id=item_id)

    try:
        if not order_item.can_be_cancelled:
            messages.error(request, "This item can no longer be cancelled.")
            return redirect('order_item_detail', item_id=item_id)

        with transaction.atomic():
            reason = request.POST.get('reason', '')

            # **1. Restock the cancelled item**
            product_variant = order_item.product_variant
            product_variant.stock += order_item.quantity
            product_variant.save()


            order = order_item.order
            total_items = order.items.count()  

            if total_items > 1:
                shipping_share = order.shipping_charge / Decimal(total_items) 
            else:
                shipping_share = order.shipping_charge 


            refund_amount = order_item.total_price + shipping_share


            payment = order.payment
            if payment.status == 'completed':
                wallet, _ = Wallet.objects.get_or_create(user=order.user) 
                wallet.add_amount(refund_amount, reason="Order Cancellation Refund")


            order_item.cancel_item(reason=reason)

            messages.success(request, "Item has been successfully cancelled, and the refund has been processed.")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('order_item_detail', item_id=item_id)



@block_superuser_navigation
@never_cache
@login_required
def return_order_item(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('order_list')

    order_item = get_object_or_404(OrderItem, id=item_id)

    if order_item.order.user != request.user:
        messages.error(request, "You don't have permission to return this order item.")
        return redirect('order_list')

    try:
        if not order_item.can_be_returned:
            messages.error(request, "This item is not eligible for return.")
            return redirect('order_item_detail', item_id=item_id)

        reason = request.POST.get('reason', '')
        order_item.return_status = "requested"
        order_item.return_reason = reason
        order_item.save()

        messages.success(request, "Return request submitted successfully. Waiting for admin approval.")
    
    except Exception as e:
        print(f"Exception: {e}")  # Debugging
        messages.error(request, "An error occurred while processing your return request.")

    return redirect('order_item_detail', item_id=item_id)



@block_superuser_navigation
@never_cache
@login_required
def wallet_view(request):
    """Display wallet balance and transaction history with pagination"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get all transactions ordered by most recent first
    transactions_list = wallet.transactions.all().order_by("-timestamp")
    
    # Set up pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions_list, 10)  # Show 10 transactions per page
    
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        transactions = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        transactions = paginator.page(paginator.num_pages)
    
    context = {
        "wallet": wallet,
        "page_obj": transactions,
    }
    
    return render(request, "user_profile/wallet_page.html", context)


@block_superuser_navigation
@never_cache
@login_required
def search_products(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(name__icontains=query)[:5]  # Limit results
        results = [{'id': p.id, 'name': p.name} for p in products]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user_profile/order_detail.html', {'order': order})

@login_required
def submit_review(request, order_item_id):
    if request.method == "POST":
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        product_id = request.POST.get('product_id')

        print(rating, review_text, product_id)

        if rating and review_text:
            # Ensure the product exists
            product = get_object_or_404(Product, id=product_id)

            # Check if the user has already reviewed this specific product
            existing_review = ProductReview.objects.filter(user=request.user, product=product).exists()
            if not existing_review:
                ProductReview.objects.create(
                    user=request.user,
                    product=product,
                    rating=int(rating),
                    review=review_text
                )
                messages.success(request, "Review submitted successfully!")
            else:
                messages.error(request, "You have already reviewed this product.")

        else:
            messages.error(request, "Rating and review text are required.")

    return redirect('order_item_detail', item_id=order_item_id)



@block_superuser_navigation
@never_cache
@login_required
def user_logout(request):
    logout(request)
    return redirect('user_login')

def custom_page_not_found_view(request, exception):
    return render(request, '404page.html', status=404)



