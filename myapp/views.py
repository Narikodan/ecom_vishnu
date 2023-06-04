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

from decimal import Decimal

from django.urls import reverse

@login_required
def checkout(request):
    user = request.user
    try:
        shipping_address = ShippingAddress.objects.get(user=user)
    except ShippingAddress.DoesNotExist:
        return redirect('myapp:edit_address')

    cart_items = Cart.objects.filter(user=user)
    total_amount = cart_items.aggregate(total=Sum('product__price'))['total']

    # Convert the total amount to float before storing it in the session
    request.session['total_amount'] = str(total_amount)

    # Redirect to the payment option view
    return HttpResponseRedirect(reverse('myapp:paymentoption'))


@login_required
def paymentoption(request):
    print("Inside paymentoption view")

    # Get the total amount from the session or calculate it from the user's cart
    total_amount = request.session.get('total_amount')
    if not total_amount:
        # Calculate the total amount from the user's cart
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.product.price * item.quantity for item in cart_items)

    # Create a Razorpay client instance
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

    # Create an order on Razorpay
    order_amount = int(float(total_amount) * 100)  # Convert the amount to paise (Razorpay uses paise as the unit)
    order_currency = 'INR'  # Set the currency to Indian Rupees (INR)
    order_receipt = 'order_{}'.format(request.user.id)  # Generate a unique order receipt for each user

    # Prepare the order details
    order_data = {
        'amount': order_amount,
        'currency': order_currency,
        'receipt': order_receipt,
        'payment_capture': 1,  # Capture the payment immediately
    }

    # Create the order on Razorpay
    order = client.order.create(data=order_data)

    # Extract the order ID from the response
    order_id = order.get('id')

    # Pass the order ID and total amount to the template
    context = {
        'razorpay_api_key': settings.RAZORPAY_API_KEY,
        'razorpay_order_id': order_id,
        'total_amount': total_amount,
    }

    if request.method == 'POST':
        print("Processing POST request")

        # Check if the payment is successful
        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        try:
            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)
            print("Payment signature verified")


            # Payment is successful
            # Create a UserOrder object
            user_order = UserOrder.objects.create(
                user=request.user,
                total_amount=total_amount,
            )
            
            print("UserOrder created:", user_order)

            # Move cart items to UserOrder
            cart_items = Cart.objects.filter(user=request.user)
            for cart_item in cart_items:
                order_item = OrderItem.objects.create(
                    order=user_order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                )
                print("OrderItem created:", order_item)

            # Delete cart items
            cart_items.delete()

            # Pass the order ID, total amount, and user order ID to the template
            context['user_order_id'] = user_order.pk
            context['payment_successful'] = True

            # Redirect to my_orders page
            return redirect('myapp:my_orders')

        except razorpay.errors.SignatureVerificationError:
            print("Signature verification failed")

            # Payment verification failed
            context['payment_successful'] = False

    # Render the paymentoption.html template with the data
    return render(request, 'myapp/paymentoption.html', context)


@login_required
def my_orders(request):
    # Retrieve the user's orders
    user_orders = UserOrder.objects.filter(user=request.user)

    # Calculate the total for each order item
    for user_order in user_orders:
        order_items = user_order.orderitem_set.all()
        for order_item in order_items:
            order_item.total = order_item.quantity * order_item.product.price

    context = {
        'user_orders': user_orders,
    }

    return render(request, 'myapp/my_orders.html', context)
