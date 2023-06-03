from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import Product, Cart, ShippingAddress
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse



def index(request):
    success_message = messages.get_messages(request)
    products = Product.objects.all()
    item_name = request.GET.get('item_name')
    if item_name != '' and item_name is not None:
        products = products.filter(name__icontains=item_name)
    user = request.user
    first_name = ''
    if user.is_authenticated:
        first_name = user.first_name

    return render(request, 'myapp/index.html', {'success_message': success_message, 'first_name': first_name, 'products': products})




def register(request):
    User = get_user_model()
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        mobile_number = request.POST.get('mobile_number', '')
        password = request.POST.get('password', '')
        username = request.POST.get('username', '')

        # Validate form data
        if not first_name or not last_name or not mobile_number or not password or not username:
            messages.error(request, 'Please fill in all fields.')
        elif User.objects.filter(mobile_number=mobile_number).exists():
            messages.error(request, 'Mobile number is already registered.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
        else:
            # Create user
            user = User.objects.create_user(first_name=first_name, last_name=last_name, mobile_number=mobile_number,
                                            password=password, username=username)
            messages.success(request, 'User created successfully!')
            return redirect('myapp:index')

    return render(request, 'myapp/register.html')





def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('myapp:index')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'myapp/login.html')



def logout_view(request):
    logout(request)
    return redirect('myapp:index')


from django.db.models import Sum

@login_required
def cart(request):
    if request.method == 'POST':
        user = request.user
        if user.is_authenticated:
            product_id = request.POST.get('product_id')
            product = Product.objects.get(id=product_id)
            cart_item = Cart.objects.filter(user=user, product=product).first()
            if cart_item:
                # Product already exists in the cart, update quantity
                cart_item.quantity += 1
                cart_item.save()
                response_data = {
                    'status': 'success',
                    'message': 'Product quantity updated successfully',
                }
            else:
                # Product doesn't exist in the cart, create new entry
                cart_item = Cart(user=user, product=product)
                cart_item.save()
                response_data = {
                    'status': 'success',
                    'message': 'Product added to cart successfully',
                }

            return JsonResponse(response_data)
        else:
            response_data = {
                'status': 'error',
                'message': 'You need to login to add products to the cart!',
            }
            return JsonResponse(response_data)

    user = request.user
    if user.is_authenticated:
        cart_items = Cart.objects.filter(user=user)
        total_amount = cart_items.aggregate(total=Sum('product__price'))['total']
        return render(request, 'myapp/cart.html', {'cart_items': cart_items, 'total_amount': total_amount})
    else:
        messages.error(request, 'You need to login to view your cart!')
        return redirect('myapp:login')



@login_required
def delete_cart_item(request, cart_item_id):
    user = request.user
    cart_item = get_object_or_404(Cart, id=cart_item_id, user=user)
    cart_item.delete()
    messages.success(request, 'Cart item deleted successfully!')
    return redirect('myapp:cart')

def productdetails(request, id):
    product_object = Product.objects.get(id=id)
    return render(request, 'myapp/productdetails.html', {'product_object': product_object})

@login_required
def checkout(request):
    user = request.user
    try:
        shipping_address = ShippingAddress.objects.get(user=user)
    except ShippingAddress.DoesNotExist:
        return redirect('myapp:edit_adress')

    cart_items = Cart.objects.filter(user=user)
    total_amount = cart_items.aggregate(total=Sum('product__price'))['total']
    return render(request, 'myapp/checkout.html', {'shipping_address': shipping_address, 'cart_items': cart_items, 'total_amount': total_amount})


@login_required
def edit_adress(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pin_code = request.POST.get('pin_code')
        phone = request.POST.get('phone')

        # Get or create the shipping address for the current user
        shipping_address, created = ShippingAddress.objects.get_or_create(user=request.user)
        shipping_address.name = name
        shipping_address.address = address
        shipping_address.city = city
        shipping_address.state = state
        shipping_address.pin_code = pin_code
        shipping_address.phone = phone
        shipping_address.save()

        return redirect('myapp:checkout')

    return render(request, 'myapp/shippingaddress.html')

@login_required
def buynow(request, id):
    product_object = Product.objects.get(id=id)
    user = request.user
    try:
        shipping_address = ShippingAddress.objects.get(user=user)
    except ShippingAddress.DoesNotExist:
        return redirect('myapp:edit_adress')
    return render(request, 'myapp/buynow.html', {'product_object': product_object, 'shipping_address': shipping_address})