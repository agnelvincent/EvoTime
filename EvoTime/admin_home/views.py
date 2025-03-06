
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from Products.models import Product, Brand, Category, ProductVariant
from .models import Coupon
from user_home.models import CustomUser
from Cart.models import Order
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import base64
from Cart.models import Order , OrderItem , Payment
from django.http import HttpResponse
import datetime
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from django.db.models import Sum
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, timedelta, time
from django.template.loader import get_template
from Cart.models import Wallet
from django.db import transaction
from django.db import transaction, IntegrityError
from decimal import Decimal, InvalidOperation
import re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.views.decorators.csrf import csrf_exempt

# Admin-only decorator
def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)

@never_cache
def admin_login(request):
    # If the user is already logged in and is a staff member, redirect to the dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    # Handle POST request for login
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)  # Log the user in
            return redirect('admin_dashboard')  # Redirect to the admin dashboard
        else:
            messages.error(request, "Invalid username or password")  # Display error message
            return redirect('admin_login')  # Redirect back to the login page

    return render(request, 'admin_login.html')  # Render login page if not POST

@admin_required
@never_cache
def admin_dashboard(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    # Key Metrics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    total_users = CustomUser.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    pending_orders = Order.objects.filter(items__status__in=["pending", "processing"]).distinct().count()
    completed_orders = Order.objects.filter(items__status="delivered").distinct().count()
    cancelled_orders = Order.objects.filter(items__status="cancelled").distinct().count()

    # Recent Orders
    recent_orders = Order.objects.order_by("-created_at")[:10]

    # Top Selling Products
    top_selling_products = (
        OrderItem.objects.values("product_variant__product__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    # Top Selling Categories
    top_selling_categories = (
        OrderItem.objects.values("product_variant__product__category__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    # Top Selling Brands
    top_selling_brands = (
        OrderItem.objects.values("product_variant__product__brand__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )

    # User Activity
    new_users_last_7_days = CustomUser.objects.filter(date_joined__gte=last_7_days).count()
    new_users_last_30_days = CustomUser.objects.filter(date_joined__gte=last_30_days).count()

    # Revenue Breakdown
    monthly_revenue = Order.objects.filter(created_at__date__gte=start_of_month).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    yearly_revenue = Order.objects.filter(created_at__date__gte=start_of_year).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    # Low Stock Alerts
    low_stock_products = ProductVariant.objects.filter(stock__lt=10)

    # Coupon Usage
    total_coupons_used = Order.objects.filter(applied_coupon__isnull=False).count()
    most_used_coupon = (
        Order.objects.values("applied_coupon__code")
        .annotate(total_used=Count("applied_coupon"))
        .order_by("-total_used")
        .first()
    )

    context = {
        # Key Metrics
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_users": total_users,
        "total_products": total_products,
        "total_categories": total_categories,
        "total_brands": total_brands,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,

        # Recent Orders
        "recent_orders": recent_orders,

        # Top Selling Data
        "top_selling_products": top_selling_products,
        "top_selling_categories": top_selling_categories,
        "top_selling_brands": top_selling_brands,

        # User Activity
        "new_users_last_7_days": new_users_last_7_days,
        "new_users_last_30_days": new_users_last_30_days,

        # Revenue Breakdown
        "monthly_revenue": monthly_revenue,
        "yearly_revenue": yearly_revenue,

        # Low Stock Alerts
        "low_stock_products": low_stock_products,

        # Coupon Usage
        "total_coupons_used": total_coupons_used,
        "most_used_coupon": most_used_coupon,
    }

    return render(request, "admin_dashboard.html", context)

@admin_required
@never_cache
def sales_data(request):
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now().date()
    
    # Set date range based on filter
    if filter_type == "today":
        start_date = today
    elif filter_type == "week":
        start_date = today - timedelta(days=7)
    elif filter_type == "month":
        start_date = today.replace(day=1)
    elif filter_type == "year":
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today.replace(day=1)  # Default to month
    
    # Get orders in date range
    orders_in_range = Order.objects.filter(created_at__date__gte=start_date)
    
    # Calculate totals
    total_orders = orders_in_range.count()
    total_revenue = orders_in_range.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    
    # Generate time series data based on filter
    if filter_type == "today":
        # Hourly breakdown for today
        hours = range(0, 24)
        labels = [f"{hour}:00" for hour in hours]
        values = []
        for hour in hours:
            hour_start = timezone.make_aware(datetime.combine(today, time(hour=hour)))
            hour_end = hour_start + timedelta(hours=1)
            hour_revenue = Order.objects.filter(
                created_at__gte=hour_start, created_at__lt=hour_end
            ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
            values.append(hour_revenue)
    
    elif filter_type == "week":
        # Daily breakdown for week
        labels = []
        values = []
        for i in range(7, 0, -1):
            date = today - timedelta(days=i-1)
            labels.append(date.strftime('%a'))
            day_revenue = Order.objects.filter(
                created_at__date=date
            ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
            values.append(day_revenue)
    
    elif filter_type == "month":
        # Daily breakdown for month
        num_days = today.day
        labels = []
        values = []
        month_start = today.replace(day=1)
        for i in range(num_days):
            date = month_start + timedelta(days=i)
            labels.append(date.strftime('%d'))
            day_revenue = Order.objects.filter(
                created_at__date=date
            ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
            values.append(day_revenue)
    
    elif filter_type == "year":
        # Monthly breakdown for year
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        values = []
        for month in range(1, 13):
            month_start = today.replace(month=month, day=1)
            if month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            month_revenue = Order.objects.filter(
                created_at__date__gte=month_start, created_at__date__lt=month_end
            ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
            values.append(month_revenue)
    
    # Get top selling products, categories, and brands for the date range
    top_selling_products = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )
    
    top_selling_categories = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__category__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )
    
    top_selling_brands = (
        OrderItem.objects.filter(order__created_at__date__gte=start_date)
        .values("product_variant__product__brand__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:10]
    )
    
    # Prepare data for the response
    data = {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "labels": labels,
        "values": values,
        "top_selling_products": list(top_selling_products),
        "top_selling_categories": list(top_selling_categories),
        "top_selling_brands": list(top_selling_brands)
    }
    
    return JsonResponse(data)

@admin_required
@never_cache
def generate_pdf(request):
    # Fetch data
    orders = Order.objects.all()

    # Create a buffer for the PDF
    buffer = BytesIO()

    # Create the PDF object
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add a title
    title = Paragraph("Sales Report", styles['Title'])
    elements.append(title)

    data = [['Order ID', 'User Email', 'Total Amount', 'Offer Percentage', 'Created At']]

    for order in orders:
        offer_percentages = [item.product_variant.product.offer_percentage for item in order.items.all()]
        avg_offer_percentage = sum(offer_percentages) / len(offer_percentages) if offer_percentages else 0

        data.append([
            str(order.id),
            order.user.email,
            f"${order.total_amount}",
            f"{avg_offer_percentage}%",
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    # Create the table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Build the PDF
    pdf.build(elements)

    # File response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    return response


@admin_required
@never_cache
def generate_excel(request):
    # Fetch data
    orders = Order.objects.all()

    # Create a workbook and add a worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    # Add headers
    ws.append(['Order ID', 'User Email', 'Total Amount', 'Created At'])

    # Add data
    for order in orders:
        ws.append([order.id, order.user.email, order.total_amount, order.created_at.strftime('%Y-%m-%d %H:%M:%S')])

    # Save to a BytesIO buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # File response
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    return response



@admin_required
@never_cache
def sales_report(request):
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    total_revenue = Order.objects.filter(payment__status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(items__status='delivered').count()
    cancelled_orders = Order.objects.filter(items__status='cancelled').count()
    weekly_sales = Order.objects.filter(payment__status='completed', created_at__gte=last_7_days).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    monthly_sales = Order.objects.filter(payment__status='completed', created_at__gte=last_30_days).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    best_selling_products = OrderItem.objects.values('product_variant__product__name')\
        .annotate(total_sold=Sum('quantity'))\
        .order_by('-total_sold')[:5]
    
    payment_breakdown = Payment.objects.values('payment_method')\
        .annotate(total=Sum('amount'))\
        .order_by('-total')

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'best_selling_products': best_selling_products,
        'payment_breakdown': payment_breakdown,
    }
    return render(request, "sales_report.html", context)


MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

@admin_required
@never_cache
def admin_product_view(request):
    products_list = Product.objects.all().order_by('id')  # Ensure consistent ordering
    categories = Category.objects.all()
    brands = Brand.objects.all()

    # Pagination
    paginator = Paginator(products_list, 10)  # Show 10 products per page
    page = request.GET.get('page')

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)  # Default to the first page
    except EmptyPage:
        products = paginator.page(paginator.num_pages)  # Deliver the last page if page is out of range

    return render(request, 'product/admin_product.html', {
        'products': products,
        'categories': categories,
        'brands': brands
    })

def list_brands(request):
    brands = Brand.objects.all()
    return render(request, 'brands/brands.html', {'brands': brands})

@csrf_exempt  # Only for testing; use CSRF protection in production
def edit_brand(request, brand_id):
    if request.method == "POST":
        brand = get_object_or_404(Brand, id=brand_id)  # Ensures ID exists, otherwise returns 404
        data = json.loads(request.body)  # Parse JSON request body
        brand.name = data.get('name', brand.name)
        brand.offer_percentage = data.get('offer_percentage', brand.offer_percentage)
        brand.save()
        return JsonResponse({"message": "Brand updated successfully"})
    
    return JsonResponse({"error": "Invalid request"}, status=400)

def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_blocked = not brand.is_blocked
    brand.save()
    return JsonResponse({"success": True, "message": f"Brand {'blocked' if brand.is_blocked else 'unblocked'} successfully!"})

@admin_required
@never_cache
def add_brand(request):
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        offer_percentage = request.POST.get('offer_percentage', '').strip()

        # Comprehensive Validations
        errors = []

        # Brand Name Validations
        if not brand_name:
            errors.append('Brand name cannot be empty!')
        elif len(brand_name) < 2:
            errors.append('Brand name must be at least 2 characters long!')
        elif len(brand_name) > 100:
            errors.append('Brand name cannot exceed 100 characters!')
        elif not re.match(r'^[A-Za-z0-9\s\-&]+$', brand_name):
            errors.append('Brand name can only contain letters, numbers, spaces, hyphens, and ampersands!')
        elif Brand.objects.filter(name__iexact=brand_name).exists():
            errors.append('A brand with this name already exists!')

        # Offer Percentage Validations
        if offer_percentage:
            try:
                offer_percentage = int(offer_percentage)
                if offer_percentage < 0 or offer_percentage > 100:
                    errors.append('Offer percentage must be between 0 and 100!')
            except ValueError:
                errors.append('Offer percentage must be a valid integer!')
        else:
            offer_percentage = 0

        # Handle Validation Errors
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('admin_product')

        # Create Brand
        try:
            with transaction.atomic():
                brand = Brand.objects.create(
                    name=brand_name, 
                    offer_percentage=offer_percentage
                )

                # Apply Offer to All Associated Products
                # Use bulk_update for better performance
                products = brand.products.all()
                for product in products:
                    product.save()  # This triggers price recalculation

            messages.success(request, f'Brand "{brand_name}" added successfully!')
            return redirect('admin_product')

        except IntegrityError:
            messages.error(request, 'An error occurred while creating the brand. Please try again.')
            return redirect('admin_product')

    return render(request, 'product/admin_product.html')




@admin_required
@never_cache
def add_product(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        regular_price = request.POST.get('regular_price')
        offer_percentage = request.POST.get('offer_percentage', '').strip()
        brand_id = request.POST.get('brand')
        image = request.FILES.get('image')
        cropped_image = request.POST.get('cropped_image')
        
        errors = []
        
        try:
            category = Category.objects.get(id=category_id) if category_id else None
            if not category:
                errors.append("Invalid category selected.")
        except (Category.DoesNotExist, ValueError):
            errors.append("Invalid category selected.")
        
        try:
            brand = Brand.objects.get(id=brand_id) if brand_id else None
        except (Brand.DoesNotExist, ValueError):
            errors.append("Invalid brand selected.")
        
        try:
            regular_price = Decimal(regular_price)
            if regular_price <= 0:
                errors.append("Regular price must be a positive number.")
        except (ValueError, TypeError, InvalidOperation):
            errors.append("Invalid regular price.")
        
        if offer_percentage:
            try:
                offer_percentage = Decimal(offer_percentage)
                if offer_percentage < 0 or offer_percentage > 100:
                    errors.append("Offer percentage must be between 0 and 100.")
            except (ValueError, TypeError, InvalidOperation):
                errors.append("Invalid offer percentage.")
        else:
            offer_percentage = Decimal(0)
        
        product_image = None
        if cropped_image:
            try:
                format, imgstr = cropped_image.split(';base64,')
                ext = format.split('/')[-1]
                imgdata = base64.b64decode(imgstr)
                
                with Image.open(BytesIO(imgdata)) as img:
                    if img.width > 2000 or img.height > 2000:
                        errors.append("Image dimensions are too large.")
                    if img.format not in ['JPEG', 'PNG', 'WEBP']:
                        errors.append("Unsupported image format.")
                
                product_image = ContentFile(imgdata, name=f'cropped_product_{name}.{ext}')
            except Exception as e:
                errors.append(f"Error processing cropped image: {str(e)}")
        elif image:
            product_image = image
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('admin_product')
        
        try:
            brand_offer = Decimal(brand.offer_percentage) if brand else Decimal(0)
            final_offer = max(offer_percentage, brand_offer)
            sales_price = (regular_price * (Decimal(100) - final_offer) / Decimal(100)) if final_offer > 0 else regular_price
            
            with transaction.atomic():
                Product.objects.create(
                    name=name,
                    category=category,
                    description=description,
                    regular_price=regular_price,
                    sales_price=sales_price,
                    offer_percentage=offer_percentage,
                    brand=brand,
                    image=product_image
                )
            messages.success(request, f'Product "{name}" added successfully!')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('admin_product')

    return redirect('admin_product')




@admin_required
@never_cache
def edit_product(request, product_id):
    
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category")
        description = request.POST.get("description", "").strip()
        regular_price = request.POST.get("regular_price")
        offer_percentage = request.POST.get("offer_percentage", "").strip()
        brand_id = request.POST.get("brand")
        image = request.FILES.get("image")

        # Validations
        if not name or len(name) < 3:
            messages.error(request, "Product name must be at least 3 characters long.")
            return redirect('admin_product')

        if not category_id or not Category.objects.filter(id=category_id).exists():
            messages.error(request, "Invalid category selected.")
            return redirect('admin_product')

        if not brand_id or not Brand.objects.filter(id=brand_id).exists():
            messages.error(request, "Invalid brand selected.")
            return redirect('admin_product')

        try:
            regular_price = Decimal(regular_price)
            if regular_price < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Regular price must be a valid positive number.")
            return redirect('admin_product')

        # Validate and Apply Offer Percentage
        if offer_percentage.strip():  # Ensure offer percentage is not empty
            try:
                offer_percentage = Decimal(offer_percentage)
                if offer_percentage < 0 or offer_percentage > 100:
                    raise ValueError
            except (ValueError, TypeError):
                messages.error(request, "Offer percentage must be between 0 and 100.")
                return redirect('admin_product')
        else:
            offer_percentage = Decimal(0)  # Default to 0 if empty

        # Get Category & Brand
        category = get_object_or_404(Category, id=category_id)
        brand = get_object_or_404(Brand, id=brand_id)

        # 🔥 Apply Highest Offer Between Product & Brand
        brand_offer = Decimal(brand.offer_percentage) if brand else Decimal(0)
        final_offer = max(offer_percentage, brand_offer)

        # **Calculate Sales Price**
        if final_offer > 0:
            sales_price = regular_price - (regular_price * (final_offer / 100))
        else:
            sales_price = regular_price  # No offer applied, use regular price

        # Debugging output (Check if values are correctly fetched)
        print(f"Regular Price: {regular_price}, Product Offer: {offer_percentage}, Brand Offer: {brand_offer}, Applied Offer: {final_offer}, Sales Price: {sales_price}")

        # Assign updated values
        product.name = name
        product.category = category
        product.description = description
        product.regular_price = regular_price
        product.sales_price = sales_price
        product.offer_percentage = offer_percentage  # Save product-level offer only
        product.brand = brand

        if image:
            product.image = image

        product.save()
        messages.success(request, "Product updated successfully!")

    return redirect("admin_product")


@admin_required
@never_cache
def manage_variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'GET':
        variants_list = ProductVariant.objects.filter(product=product)
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(variants_list, 10)  # Show 10 variants per page

        try:
            variants = paginator.page(page)
        except PageNotAnInteger:
            variants = paginator.page(1)
        except EmptyPage:
            variants = paginator.page(paginator.num_pages)

        context = {
            'product': product,
            'variants': variants,
        }
        return render(request, 'variant/manage_variant.html', context)
    
    elif request.method == 'POST':
        # Handle adding new variant
        color = request.POST.get('color', '').strip().lower()
        if not color:
            return JsonResponse({'error': 'Color cannot be empty!'}, status=400)

        try:
            stock = int(request.POST.get('stock', 0))
            if stock < 0:
                raise ValueError
        except ValueError:
            return JsonResponse({'error': 'Invalid stock value!'}, status=400)

        if ProductVariant.objects.filter(product=product, color=color).exists():
            return JsonResponse({'error': f"The color '{color}' already exists for this product."}, status=400)

        # Handle image uploads
        images = {}
        for i in range(1, 5):
            image = request.FILES.get(f'image{i}')
            if image:
                images[f'image{i}'] = image

        variant = ProductVariant.objects.create(
            product=product,
            color=color,
            stock=stock,
            **images
        )
        
        return JsonResponse({'message': 'Variant added successfully!'})

@require_http_methods(["POST"])
@admin_required
@never_cache
def add_variant(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get and validate color
        color = request.POST.get('color', '').strip().lower()
        if not color:
            return JsonResponse({'error': 'Color cannot be empty!'}, status=400)

        # Get and validate stock
        try:
            stock = int(request.POST.get('stock', 0))
            if stock < 0:
                return JsonResponse({'error': 'Stock cannot be negative!'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Invalid stock value!'}, status=400)

        # Check for duplicate color
        if ProductVariant.objects.filter(product=product, color=color).exists():
            return JsonResponse({'error': f"The color '{color}' already exists for this product."}, status=400)

        # Handle image uploads
        images = {}
        for i in range(1, 5):
            image = request.FILES.get(f'image{i}')
            if image:
                images[f'image{i}'] = image

        # Create variant
        variant = ProductVariant.objects.create(
            product=product,
            color=color,
            stock=stock,
            **images
        )
        
        return JsonResponse({
            'message': 'Variant added successfully!',
            'variant': {
                'id': variant.id,
                'color': variant.color,
                'stock': variant.stock
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@admin_required
@never_cache
@require_http_methods(["POST"])
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    color = request.POST.get('color', '').strip().lower()
    if not color:
        return JsonResponse({'error': 'Color cannot be empty!'}, status=400)

    try:
        stock = int(request.POST.get('stock', 0))
        if stock < 0:
            raise ValueError
    except ValueError:
        return JsonResponse({'error': 'Invalid stock value!'}, status=400)

    if ProductVariant.objects.filter(
        product=variant.product, 
        color=color
    ).exclude(id=variant.id).exists():
        return JsonResponse({'error': f"The color '{color}' already exists for this product."}, status=400)

    variant.color = color
    variant.stock = stock

    # Handle image uploads
    for i in range(1, 5):
        image = request.FILES.get(f'image{i}')
        if image:
            setattr(variant, f'image{i}', image)

    variant.save()
    return JsonResponse({'message': 'Variant updated successfully!'})

@staff_member_required
@admin_required
@never_cache
@require_http_methods(["DELETE"])
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.delete()
    return JsonResponse({'message': 'Variant deleted successfully!'})





@admin_required
@never_cache
def manage_categories(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name', '').strip()
        image = request.FILES.get('Category_image')

        # Comprehensive Validations
        errors = []

        # Name Validation
        if not category_name:
            errors.append("Category name cannot be empty!")
        elif len(category_name) < 2:
            errors.append("Category name must be at least 2 characters long!")
        elif len(category_name) > 100:
            errors.append("Category name cannot exceed 100 characters!")
        elif not re.match(r'^[A-Za-z0-9\s\-&.()]+$', category_name):
            errors.append("Category name contains invalid characters!")
        
        # Check for Duplicate Category (case-insensitive)
        if Category.objects.filter(name__iexact=category_name).exists():
            errors.append("A category with this name already exists!")

        # Handle Errors
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('manage_categories')
        
        print("Form submitted!")
        print(f"POST data: {request.POST}")
        print(f"FILES data: {request.FILES}")

        # Create Category with Transaction
        try:
            with transaction.atomic():
                Category.objects.create(name=category_name , Category_image = image)
            messages.success(request, f"Category '{category_name}' added successfully!")
        except IntegrityError:
            messages.error(request, "An error occurred while creating the category.")
        
        return redirect('manage_categories')

    # Fetch categories with ordering
    categories = Category.objects.all().order_by('-created_at')
    categories_list = Category.objects.all().order_by('-created_at')

    # Pagination
    paginator = Paginator(categories_list, 10)  # Show 10 categories per page
    page = request.GET.get('page')

    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)  # Default to the first page
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)  # Deliver the last page if page is out of range
    return render(request, 'category/admin_category.html', {'categories': categories})


@admin_required
@never_cache
def toggle_category_status(request, category_id):
    try:
        # Validate category ID
        category_id = int(category_id)
        category = get_object_or_404(Category, id=category_id)

        # Check if category has associated products before deactivation
        if not category.is_active:
            # Check for active products in this category
            active_products_count = category.products.filter(is_active=True).count()
            if active_products_count > 0:
                messages.warning(request, 
                    f"Cannot deactivate category with {active_products_count} active products!")
                return redirect('manage_categories')

        # Toggle status with transaction
        with transaction.atomic():
            category.is_active = not category.is_active
            category.save()

        # Success message based on new status
        status_message = "activated" if category.is_active else "deactivated"
        messages.success(request, f"Category {status_message} successfully!")
        
        return redirect('manage_categories')

    except ValueError:
        messages.error(request, "Invalid category ID!")
        return redirect('manage_categories')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('manage_categories')


@admin_required
@never_cache
def edit_category(request, category_id):
    try:
        # Validate and fetch category
        category_id = int(category_id)
        category = get_object_or_404(Category, id=category_id)

        if request.method == 'POST':
            new_name = request.POST.get('category_name', '').strip()

            # Comprehensive Validations
            errors = []

            # Name Validation
            if not new_name:
                errors.append("Category name cannot be empty!")
            elif len(new_name) < 2:
                errors.append("Category name must be at least 2 characters long!")
            elif len(new_name) > 100:
                errors.append("Category name cannot exceed 100 characters!")
            elif not re.match(r'^[A-Za-z0-9\s\-&.()]+$', new_name):
                errors.append("Category name contains invalid characters!")
            
            # Check for Duplicate Category (case-insensitive, excluding current category)
            if Category.objects.exclude(id=category_id).filter(name__iexact=new_name).exists():
                errors.append("A category with this name already exists!")

            # Handle Errors
            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect('manage_categories')

            # Update Category with Transaction
            try:
                with transaction.atomic():
                    category.name = new_name
                    category.save()
                messages.success(request, "Category updated successfully!")
            except IntegrityError:
                messages.error(request, "An error occurred while updating the category.")
            
            return redirect('manage_categories')

        return render(request, 'product/edit_category.html', {'category': category})

    except ValueError:
        messages.error(request, "Invalid category ID!")
        return redirect('manage_categories')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('manage_categories')


@admin_required
@never_cache   
def block_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_blocked = True
    product.save()
    messages.success(request, f"{product.name} has been blocked successfully.")
    return redirect('admin_product')

@admin_required
@never_cache
def unblock_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_blocked = False
    product.save()
    messages.success(request, f"{product.name} has been unblocked successfully.")
    return redirect('admin_product')

@admin_required
@never_cache
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.regular_price = request.POST.get('regular_price')
        product.sales_price = request.POST.get('sales_price') or None
        product.description = request.POST.get('description')
        product.brand_id = request.POST.get('brand')
        product.category_id = request.POST.get('category')

        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, f"Product '{product.name}' has been updated successfully.")
        return redirect('admin_product')
    
    brands = Brand.objects.all()
    categories = Category.objects.all()
    return render(request, 'product/edit_product.html', {
        'product': product,
        'brands': brands,
        'categories': categories
    })


@admin_required
@never_cache
def user_viewer(request):
    user_list = CustomUser .objects.values('id', 'full_name', 'email', 'phone_number', 'is_blocked')
    paginator = Paginator(user_list, 10)  # Show 10 users per page

    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    return render(request, 'users/user_viewer.html', {'users': users})

@admin_required
@never_cache
def toggle_user_block(request, user_id):
    user = get_object_or_404(CustomUser , id=user_id)
    user.is_blocked = not user.is_blocked
    user.save()
    messages.success(request, f"User  '{user.full_name}' has been {'unblocked' if not user.is_blocked else 'blocked'}.")
    return redirect('user_viewer')




@admin_required
@never_cache
def admin_order_list_view(request):
    # Fetch all orders with related user and order items
    orders_list = Order.objects.select_related('user').prefetch_related('items__product_variant__product').order_by('-created_at')
    

    paginator = Paginator(orders_list, 5)  # Show 10 orders per page
    page_number = request.GET.get('page')
    try:
        orders = paginator.page(page_number)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    return render(request, 'orders/admin_order.html', {'orders': orders})


@admin_required
@never_cache   
def admin_change_order_item_status_view(request, order_item_id):
    try:
        # Fetch the order item with related order and payment
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order = order_item.order

        if request.method == 'POST':
            new_status = request.POST.get('status', '').strip()

            # Validate status choice
            if new_status not in dict(OrderItem.STATUS_CHOICES).keys():
                messages.error(request, "Invalid status selected.")
                return redirect('admin_order_list_view')

            # Prevent changing to 'cancelled' status
            if new_status == 'cancelled':
                messages.error(request, "Cannot manually change status to cancelled.")
                return redirect('admin_order_list_view')

            # Comprehensive Status Change Logic
            try:
                with transaction.atomic():
                    # Update Order Item Status
                    order_item.status = new_status
                    order_item.save()

                    # Handle Payment Status for COD Orders
                    try:
                        payment = order.payment
                        
                        # Update payment status based on order item status and payment method
                        if payment.payment_method == 'cod':
                            if new_status in ['shipped', 'delivered']:
                                payment.status = 'completed'
                            payment.save()

                    except Payment.DoesNotExist:
                        # Log or handle case where payment doesn't exist
                        messages.warning(request, "No payment record found for this order.")

                    # Optional: Update overall order status if all items are in same status
                    order_statuses = order.items.values_list('status', flat=True).distinct()
                    if len(order_statuses) == 1:
                        # If all items have same status, potentially update order status
                        if new_status == 'delivered':
                            # Mark order as fully delivered
                            order.status = 'completed'
                            order.save()

                messages.success(request, f"Order item status updated to {new_status}.")
            
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

        return redirect('admin_order_list_view')

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('admin_order_list_view')

@admin_required
@never_cache   
def admin_return_requests(request):
    return_requests = OrderItem.objects.filter(return_status="requested")
    return render(request, 'orders/admin_return_requests.html', {'return_requests': return_requests})


@admin_required
@never_cache   
def admin_handle_return_request(request, item_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('admin_return_requests')

    order_item = get_object_or_404(OrderItem, id=item_id)
    action = request.POST.get('action')

    if action not in ['approve', 'reject']:
        messages.error(request, "Invalid action.")
        return redirect('admin_return_requests')

    try:
        with transaction.atomic():
            if action == 'approve':
                # **1. Restock the product**
                product_variant = order_item.product_variant
                product_variant.stock += order_item.quantity
                product_variant.save()

                # **2. Calculate Refund (Item Price + Shipping Share)**
                order = order_item.order
                total_items = order.items.filter(status__in=["pending", "processing", "shipped", "delivered"]).count()

                if total_items > 1:
                    per_item_shipping_charge = order.shipping_charge / Decimal(total_items)
                else:
                    per_item_shipping_charge = order.shipping_charge  # If only one item, refund full shipping charge

                refund_amount = (order_item.product_variant.product.sales_price * Decimal(order_item.quantity)) + per_item_shipping_charge

                # **3. Check if the order has a valid payment**
                payment = getattr(order, "payment", None)  # Safely get the payment attribute
                if payment and payment.status == "completed":
                    wallet, _ = Wallet.objects.get_or_create(user=order.user)
                    wallet.add_amount(refund_amount, reason="Order Return Refund")
                else:
                    messages.warning(request, "Order has no valid payment. Refund not processed.")

                # **4. Mark the order item as returned**
                order_item.return_status = "approved"
                order_item.status = "returned"
                order_item.save()

                messages.success(request, "Return request approved. Refund processed if payment exists.")
            else:
                order_item.return_status = "rejected"
                order_item.save()
                messages.success(request, "Return request rejected.")

    except Exception as e:
        print(f"Exception: {e}")  # Debugging
        messages.error(request, "An error occurred while processing the return request.")

    return redirect('admin_return_requests')




@admin_required
@never_cache   
def coupon_management(request):
    """Handles adding, updating, and listing coupons"""
    coupons = Coupon.objects.all()
    coupons_list = Coupon.objects.all()
        # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(coupons_list, 10)  # Show 10 coupons per page

    try:
        coupons = paginator.page(page)
    except PageNotAnInteger:
        coupons = paginator.page(1)
    except EmptyPage:
        coupons = paginator.page(paginator.num_pages)

    if request.method == "POST":
        coupon_id = request.POST.get("coupon_id")
        code = request.POST.get("code")
        discount_percentage = request.POST.get("discount_percentage")  # Updated field name
        min_cart_value = request.POST.get("min_cart_value")
        start_date = request.POST.get("start_date")
        expiry_date = request.POST.get("expiry_date") or None
        is_active = request.POST.get("is_active") == "on"

        # Validate discount percentage
        try:
            discount_percentage = float(discount_percentage)
            if not (1 <= discount_percentage <= 100):
                raise ValueError("Discount percentage must be between 1 and 100.")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("coupon_management")

        if coupon_id:  # Update existing coupon
            coupon = get_object_or_404(Coupon, id=coupon_id)
            coupon.code = code
            coupon.discount_percentage = discount_percentage  # Updated field name
            coupon.min_cart_value = min_cart_value
            coupon.start_date = start_date
            coupon.expiry_date = expiry_date
            coupon.is_active = is_active
            coupon.save()
        else:  # Create a new coupon
            Coupon.objects.create(
                code=code,
                discount_percentage=discount_percentage,  # Updated field name
                min_cart_value=min_cart_value,
                start_date=start_date,
                expiry_date=expiry_date,
                is_active=is_active
            )

        return redirect("coupon_management")

    return render(request, "coupon/manage_coupon.html", {"coupons": coupons})


@admin_required
@never_cache   
def get_coupon_details(request, coupon_id):
    """Fetch coupon details via AJAX for editing"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    data = {
        "id": coupon.id,
        "code": coupon.code,
        "discount_percentage": str(coupon.discount_percentage),  # Updated field name
        "min_cart_value": str(coupon.min_cart_value),
        "start_date": str(coupon.start_date),
        "expiry_date": str(coupon.expiry_date) if coupon.expiry_date else "",
        "is_active": coupon.is_active,
    }
    return JsonResponse(data)


@admin_required
@never_cache   
def delete_coupon(request, coupon_id):
    """Deletes a coupon"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    return JsonResponse({"message": "Coupon deleted successfully"})



@admin_required
@never_cache   
def admin_logout(request):
    logout(request)
    return redirect('admin_login')
