from django.contrib import admin
from .models import User, Product, Cart, ShippingAddress, UserOrder, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(UserOrder)
class UserOrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(ShippingAddress)
