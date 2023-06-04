from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path('', views.index, name='index'),
    path('register', views.register, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('cart', views.cart, name='cart'),
    path('<int:id>', views.productdetails, name='productdetails'),
    path('cart/delete/<int:cart_item_id>/', views.delete_cart_item, name='delete_cart_item'),
    path('checkout/',views.checkout, name='checkout'),
    path('edit_adress/', views.edit_adress, name='edit_adress'),
    path('buynow/<int:id>', views.buynow, name='buynow'),
    path('paymentoption', views.paymentoption, name='paymentoption'),

]
