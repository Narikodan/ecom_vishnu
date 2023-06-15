from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
import razorpay
from django.conf import settings
from .models import OrderItem, Product, Cart, ShippingAddress, UserOrder
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Sum
from decimal import Decimal
from django.db.models import F
from myapp.models import UserOrder, OrderItem




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
            login(request, user)  # Log in the user
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
def edit_adress(request):
    shipping_address = None
    try:
        shipping_address = ShippingAddress.objects.get(user=request.user)
    except ShippingAddress.DoesNotExist:
        shipping_address = None
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

    return render(request, 'myapp/shippingaddress.html' , {'shipping_address': shipping_address})

from django.shortcuts import redirect

@login_required
def buynow(request, id):
    product_object = Product.objects.get(id=id)
    user = request.user
    
    try:
        shipping_address = ShippingAddress.objects.get(user=user)
    except ShippingAddress.DoesNotExist:
        return redirect('myapp:edit_address', address=shipping_address.id)
    return render(request, 'myapp/buynow.html', {'product_object': product_object, 'shipping_address': shipping_address})



@login_required
def checkout(request):
    user = request.user

    # Check if the user is coming from the "buynow" page
    if 'buynow_product_id' in request.session:
        product_id = request.session['buynow_product_id']
        try:
            product = Product.objects.get(id=product_id)
            total_amount = product.price
        except Product.DoesNotExist:
            return redirect('myapp:home')  # Redirect to home if the product doesn't exist
    else:
        # User is coming from the regular cart
        try:
            shipping_address = ShippingAddress.objects.get(user=user)
        except ShippingAddress.DoesNotExist:
            return redirect('myapp:edit_address')

        cart_items = Cart.objects.filter(user=user)
        total_amount = cart_items.aggregate(total=Sum('product__price'))['total']

    # Convert the total amount to float before storing it in the session
    request.session['total_amount'] = str(total_amount)

    # Clear the session variable for buynow product ID
    request.session.pop('buynow_product_id', None)

    # Redirect to the payment option view
    return HttpResponseRedirect(reverse('myapp:paymentoption'))



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Cart, UserOrder, OrderItem
import razorpay
from django.conf import settings
from django.views.decorators.http import require_POST
import hashlib
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings
from django.shortcuts import render
import razorpay

def paymentoption(request):
    # Calculate total cart amount
    cart_items = Cart.objects.filter(user=request.user)
    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    # Generate the Razorpay order amount (in paise)
    order_amount = int(total_amount * 100)

    # Create a Razorpay order
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    data = {
        'amount': order_amount,
        'currency': 'INR',
        # Other order details if needed
    }
    razorpay_order = client.order.create(data=data)

    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_API_KEY,
        'order_amount': order_amount,
        'total_amount': total_amount,
    }

    return render(request, 'myapp/payment.html', context)


from .models import UserOrder, OrderItem



import razorpay

from django.shortcuts import redirect

def payment_success(request):
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        print("Payment ID:", payment_id)
        print("Razorpay Order ID:", razorpay_order_id)
        print("Razorpay Signature:", razorpay_signature)

        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

        try:
            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': razorpay_signature,
            }
            print("Params Dict:", params_dict)
            client.utility.verify_payment_signature(params_dict)
            print("Signature verification successful")

            # Payment signature is valid
            # Move items from cart to UserOrder
            cart_items = Cart.objects.filter(user=request.user)
            total_amount = 0

            # Create UserOrder and OrderItem for each cart item
            user_order = UserOrder.objects.create(user=request.user, total_amount=0)
            order_items = []
            for cart_item in cart_items:
                order_item = OrderItem.objects.create(order=user_order, product=cart_item.product, quantity=cart_item.quantity)
                total_amount += cart_item.product.price * cart_item.quantity
                order_items.append(order_item)

            # Update the total amount in UserOrder
            user_order.total_amount = total_amount
            user_order.save()

            # Clean the user's cart
            cart_items.delete()
            print("Cart items deleted successfully")

            # Redirect to the My Orders page
            return redirect('myapp:my_orders')

        except razorpay.errors.SignatureVerificationError:
            # Payment signature is invalid
            # Handle the error as needed
            print("Signature verification error: Razorpay Signature Verification Failed")

    # Handle the case if the request is not a POST request or payment signature verification fails
    # Redirect to an error page or display an error message
    print("Redirecting to payment_failed page")
    return redirect('myapp:payment_failed')


    
def my_orders(request):
    # Retrieve the user's orders
    user_orders = UserOrder.objects.filter(user=request.user)

    context = {
        'user_orders': user_orders
    }

    return render(request, 'myapp/my_orders.html', context)

