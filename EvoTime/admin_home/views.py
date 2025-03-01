
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from Products.models import Product, Brand, Category, ProductVariant
from .models import UsedCoupon,Coupon
from user_home.models import CustomUser
from Cart.models import Order
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import base64
from django.utils.timezone import now
from Cart.models import Order , OrderItem , Payment
import pandas as pd
from django.http import HttpResponse
import datetime
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from django.db.models import Sum
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, timedelta, time
from django.template.loader import get_template
from xhtml2pdf import pisa
from Cart.models import Wallet
from django.db import transaction


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
    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all()
    return render(request, 'product/admin_product.html', {
        'products': products,
        'categories': categories,
        'brands': brands
    })

@admin_required
@never_cache
def add_brand(request):
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()


        if not brand_name:
            messages.error(request, 'Brand name cannot be empty!')
        elif Brand.objects.filter(name__iexact=brand_name).exists():
            messages.warning(request, 'Brand already exists!')
        elif len(brand_name) < 2:
            messages.error(request, 'Brand name must be at least 2 characters long!')
        else:
            # Validate Offer Percentage

            brand = Brand.objects.create(name=brand_name)
            messages.success(request, 'Brand added successfully!')

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

        # Validate inputs
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

        # Validate Offer Percentage
        if offer_percentage:
            try:
                offer_percentage = Decimal(offer_percentage)
                if offer_percentage < 0 or offer_percentage > 100:
                    raise ValueError
            except (ValueError, TypeError):
                messages.error(request, "Offer percentage must be between 0 and 100.")
                return redirect('admin_product')
        else:
            offer_percentage = Decimal(0)  # Default to 0 if no offer percentage is provided

        # Calculate sales price based on offer percentage
        sales_price = regular_price - (regular_price * (offer_percentage / 100))

        category = get_object_or_404(Category, id=category_id)
        brand = get_object_or_404(Brand, id=brand_id)

        # Handle Image Processing
        if cropped_image:
            try:
                format, imgstr = cropped_image.split(';base64,')
                ext = format.split('/')[-1]
                imgdata = base64.b64decode(imgstr)
                image_file = BytesIO(imgdata)
                image = Image.open(image_file)
                file_name = 'cropped_image.' + ext
                image_file = ContentFile(imgdata, name=file_name)
                product_image = image_file
            except Exception as e:
                messages.error(request, f"Error processing image: {e}")
                return redirect('admin_product')
        elif image:
            if image.size > MAX_IMAGE_SIZE:
                messages.error(request, "Image size should not exceed 5MB.")
                return redirect('admin_product')

            if not image.content_type.startswith('image/'):
                messages.error(request, "Invalid image format. Please upload a valid image file.")
                return redirect('admin_product')

            product_image = image
        else:
            product_image = None

        # Create Product
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

        messages.success(request, 'Product added successfully!')
    return redirect('admin_product')


@admin_required
@never_cache
def edit_product(request, product_id):
    
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category")
        # sales_price = request.POST.get("sales_price")
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

        # Ensure correct sales price calculation
        sales_price = regular_price - (regular_price * (int(offer_percentage) / 100))
        # Debugging output (Check if values are correctly fetched)
        print(f"Regular Price: {regular_price}, Offer Percentage: {offer_percentage}, Sales Price: {sales_price}")

        # Assign updated values
        product.name = name
        product.category = get_object_or_404(Category, id=category_id)
        product.description = description
        product.regular_price = regular_price
        product.sales_price = sales_price
        product.offer_percentage = offer_percentage
        product.brand = get_object_or_404(Brand, id=brand_id)

        if image:
            product.image = image

        product.save()
        messages.success(request, "Product updated successfully!")

    return redirect("admin_product")

@staff_member_required
def manage_variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'GET':
        variants = ProductVariant.objects.filter(product=product)
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

        # Validate inputs
        if not category_name:
            messages.error(request, "Category name cannot be empty!")
            return redirect('manage_categories')


        # Create category with optional offer
        Category.objects.create(name=category_name)
        messages.success(request, "Category added successfully!")
        return redirect('manage_categories')

    categories = Category.objects.all()
    return render(request, 'category/admin_category.html', {'categories': categories})


@admin_required
@never_cache
def toggle_category_status(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id)
        category.is_active = not category.is_active
        category.save()
        return redirect('manage_categories')

@admin_required
@never_cache
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        new_name = request.POST.get('category_name', '').strip()

        # Validate inputs
        if not new_name:
            messages.error(request, "Category name cannot be empty!")
            return redirect('manage_categories')

        # Update category
        category.name = new_name
        category.save()
        messages.success(request, "Category updated successfully!")
        return redirect('manage_categories')

    return render(request, 'product/edit_category.html', {'category': category})


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
    
    paginator = Paginator(orders_list, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, 'orders/admin_order.html', {'orders': orders})


@admin_required
def admin_change_order_item_status_view(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id)

    if request.method == 'POST':
        new_status = request.POST.get('status', '')

        if new_status in dict(OrderItem.STATUS_CHOICES).keys():  # Validate status choice
            order_item.status = new_status
            order_item.save()

            return redirect('admin_order_list_view')  # Redirect instead of returning JSON

    return redirect('admin_order_list_view')  # Redirect even on error

@staff_member_required
def admin_return_requests(request):
    return_requests = OrderItem.objects.filter(return_status="requested")
    return render(request, 'orders/admin_return_requests.html', {'return_requests': return_requests})

@staff_member_required
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





def coupon_management(request):
    """Handles adding, updating, and listing coupons"""
    coupons = Coupon.objects.all()

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


def delete_coupon(request, coupon_id):
    """Deletes a coupon"""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    return JsonResponse({"message": "Coupon deleted successfully"})



@never_cache
def admin_logout(request):
    logout(request)
    return redirect('admin_login')
