from django.contrib import admin
from .models import User, Product, Cart, ShippingAddress, UserOrder, OrderItem



# Register your models here.

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(ShippingAddress)
admin.site.register(UserOrder)
admin.site.register(OrderItem)