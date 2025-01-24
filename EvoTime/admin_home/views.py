

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from .models import Product, Brand, Category
from user_home.models import CustomUser

# Admin-only decorator
def admin_required(view_func):
    decorator = user_passes_test(lambda u: u.is_authenticated and u.is_staff)
    return decorator(view_func)

@never_cache
def admin_login(request):

    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('admin_login')
    return render(request, 'admin_login.html')

@admin_required
@never_cache
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@admin_required
@never_cache
def admin_product(request):
    products = Product.objects.all()
    return render(request, 'product/admin_product.html', {'products': products})

@admin_required
@never_cache
def add_product(request):
    if request.method == "POST":
        name = request.POST['name']
        category_id = request.POST['category']
        description = request.POST['description']
        stock = request.POST['stock']
        regular_price = request.POST['regular_price']
        sales_price = request.POST['sales_price']
        brand_id = request.POST['brand']

        category = Category.objects.get(id=category_id)
        brand = Brand.objects.get(id=brand_id)

        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')
        image4 = request.FILES.get('image4')

        product = Product.objects.create(
            name=name,
            category=category,
            description=description,
            stock=stock,
            regular_price=regular_price,
            sales_price=sales_price,
            brand=brand,
            image1=image1,
            image2=image2,
            image3=image3,
            image4=image4,
        )
        product.save()
        return redirect('admin_product')

    brands = Brand.objects.all()
    categories = Category.objects.all()
    return render(request, 'product/add_product.html', {'brands': brands, 'categories': categories})

@admin_required
@never_cache
def add_brand(request):
    if request.method == 'POST':
        brand_name = request.POST['brand_name']
        if not Brand.objects.filter(name=brand_name).exists():
            Brand.objects.create(name=brand_name)
            return redirect('add_product')
        else:
            return render(request, 'product/add_brand.html', {'error': 'Brand already exists!'})
    return render(request, 'product/add_brand.html')

@admin_required
@never_cache
def manage_categories(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        if category_name:
            Category.objects.create(name=category_name)
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
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id)
        new_name = request.POST.get('category_name')
        if new_name:
            category.name = new_name
            category.save()
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
        product.stock = request.POST.get('stock')
        product.description = request.POST.get('description')
        product.brand_id = request.POST.get('brand')
        product.category_id = request.POST.get('category')

        if 'image1' in request.FILES:
            product.image1 = request.FILES['image1']
        if 'image2' in request.FILES:
            product.image2 = request.FILES['image2']
        if 'image3' in request.FILES:
            product.image3 = request.FILES['image3']
        if 'image4' in request.FILES:
            product.image4 = request.FILES['image4']

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
    users = CustomUser.objects.values('id', 'full_name', 'email', 'phone_number', 'is_blocked')
    return render(request, 'users/user_viewer.html', {'users': users})

@admin_required
@never_cache
def toggle_user_block(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    user.is_blocked = not user.is_blocked
    user.save()
    messages.success(request, f"User '{user.full_name}' has been {'unblocked' if not user.is_blocked else 'blocked'}.")
    return redirect('user_viewer')

@never_cache
def admin_logout(request):
    logout(request)
    return redirect('admin_login')
