from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import User, UserProfile, Product, Cart, Order, OrderItem, Review, PickupPoint, Role, Category, Brand, AgeCategory, Species, ProductType, Purpose, ProductStock, OrdersByMonth, OrdersByBrand, OrdersByCategory, AuditLog
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, CartAddForm, OrderForm, ReviewForm
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
import json
from django.db import connection
import csv
import datetime
from django.http import HttpResponse, JsonResponse
from . import db_reports  
import os
from django.views.decorators.http import require_POST
from django.core import serializers
from django.conf import settings
from datetime import datetime, date
import zipfile
import tempfile
from django.utils import timezone
from io import StringIO

def admin_required(user):
    return user.is_authenticated and user.role.name == 'Администратор'

def customer_required(user):
    return user.is_authenticated and getattr(user.role, 'name', None) == 'Покупатель'

def index(request):
    context = {
        'all_species': Species.objects.filter(is_active=True),
        'all_ages': AgeCategory.objects.filter(is_active=True),
        'all_categories': Category.objects.filter(is_active=True),
        'all_types': ProductType.objects.filter(is_active=True),
        'all_purposes': Purpose.objects.filter(is_active=True),
    }
    return render(request, 'shablons/index.html', context)

def pickup(request):
    return render(request, 'shablons/pickup.html')

def faq(request):
    return render(request, 'shablons/faq.html')

def contacts(request):
    return render(request, 'shablons/contacts.html')
def about(request):
    return render(request, 'shablons/about.html')

def register(request):
    return render(request, 'shablons/register.html')

def user_login(request):
    return render(request, 'shablons/login.html')

def profile_redirect(request):
    if request.user.is_authenticated:
        return redirect('profile')  
    else:
        return redirect('login') 

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Вы вышли из системы")
    return redirect('login')

def profile(request):
        return render(request, 'shablons/profile.html')


@login_required
def order_list(request):
        return render(request, 'shablons/order_list.html')


@login_required
def order_detail(request, order_id):
    return render(request, 'shablons/order_detail.html', {'orderId': order_id})



def product_list(request):
    all_categories = Category.objects.filter(is_active=True)
    all_brands = Brand.objects.filter(is_active=True)
    all_ages = AgeCategory.objects.filter(is_active=True)
    all_species = Species.objects.filter(is_active=True)
    all_types = ProductType.objects.filter(is_active=True)
    all_purposes = Purpose.objects.filter(is_active=True)

    context = {
        'all_categories': all_categories,
        'all_brands': all_brands,
        'all_ages': all_ages,
        'all_species': all_species,
        'all_types': all_types,
        'all_purposes': all_purposes,
    }

    return render(request, 'shablons/catalog.html', context)


@login_required
def delete_account(request):
    return redirect('profile')


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    received_orders_count = OrderItem.objects.filter(
        product=product,
        order__user=request.user,
        order__status='Получен'
    ).count() if request.user.is_authenticated else 0

    user_reviews_count = Review.objects.filter(
        product=product,
        user=request.user
    ).count() if request.user.is_authenticated else 0

    can_review = received_orders_count > user_reviews_count
    remaining_reviews = received_orders_count - user_reviews_count

    average_rating = product.reviews.aggregate(avg=Avg('rating'))['avg']
    star_percentage = (average_rating / 5 * 100) if average_rating else 0

    return render(request, 'shablons/product_detail.html', {
        'product': product,
        'can_review': can_review,
        'remaining_reviews': remaining_reviews,
        'average_rating': average_rating,
        'star_percentage': star_percentage,
    })


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product, 
    }
    return render(request, 'shablons/add_review.html', context)



@login_required
def cart_view(request):
    return render(request, 'shablons/cart.html')



@login_required
def add_to_cart(request, product_id):
    return redirect('cart')


@login_required
def remove_from_cart(request, cart_id):
    return redirect('cart')


@login_required
def update_cart_quantity(request, cart_id):
    return redirect('cart')


@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, "Ваша корзина пуста")
        return redirect('cart')

    total_price = sum(item.quantity * item.product.price for item in cart_items)

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            pickup_point = form.cleaned_data['pickup_point']
            
            try:
                with transaction.atomic():
                    for item in cart_items:
                        stock_entry = ProductStock.objects.get(
                            product=item.product,
                            pickup_point=pickup_point
                        )
                        if item.quantity > stock_entry.quantity:
                            raise ValueError(
                                f"В пункте {pickup_point.address} доступно только {stock_entry.quantity} шт. товара {item.product.name}"
                            )

                    
                    order = Order.objects.create(
                        order_number=get_random_string(10).upper(),
                        user=request.user,
                        pickup_point=pickup_point,
                        status="В обработке",
                        total_price=0,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone']
                    )

                    total_price_post = 0
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.price
                        )
                        total_price_post += item.quantity * item.product.price

                        stock_entry = ProductStock.objects.get(
                            product=item.product,
                            pickup_point=pickup_point
                        )
                        stock_entry.quantity -= item.quantity
                        stock_entry.save()

                    order.total_price = total_price_post
                    order.save()

                    cart_items.delete() 

                    subject = f"Подтверждение заказа №{order.order_number}"
                    message = render_to_string('shablons/email.html', {'order': order})
                    email = EmailMessage(subject, message, to=[order.email])
                    email.content_subtype = "html"
                    email.send(fail_silently=False)

                    messages.success(request, "Заказ оформлен успешно!")
                    return redirect('order_success', order_id=order.id)

            except ProductStock.DoesNotExist:
                messages.error(request, "Некоторые товары отсутствуют в выбранном пункте выдачи.")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Ошибка при оформлении заказа: {str(e)}")

    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone or '+7'
        }
        form = OrderForm(initial=initial_data)

    pickup_points = PickupPoint.objects.filter(is_active=True)

    return render(request, "shablons/checkout.html", {
        "cart_items": cart_items,
        "pickup_points": pickup_points,
        "total_price": total_price,
        "form": form
    })

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shablons/order_success.html", {"order": order})

@user_passes_test(admin_required)
def admin_reports(request):
    return render(request, 'admin/reports.html')


@user_passes_test(admin_required)
def admin_summaries(request):
    return render(request, 'admin/summaries.html')


@user_passes_test(admin_required)
def view_summary(request, summary):
    return render(request, 'admin/view_summary.html')


def get_sales_by_category():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_sales_by_category();")
        rows = cursor.fetchall()
    return [{'category': r[0], 'total_sales': float(r[1])} for r in rows]

def get_sales_by_month():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_sales_by_month();")
        rows = cursor.fetchall()
    return [{'month': r[0].strftime('%Y-%m-%d'), 'total_sales': float(r[1])} for r in rows]


@user_passes_test(admin_required)
def sales_charts(request):
    return render(request, 'admin/sales_charts.html')

@user_passes_test(admin_required)
def admin_statement(request):
    report_type = request.GET.get("type", "day")
    date_str = request.GET.get("date")
    
    date_obj = date.today() if not date_str else datetime.strptime(date_str, "%Y-%m-%d").date()

    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all()
    users = User.objects.all()

    if report_type in ["day", "week", "month"]:
        if report_type == "day":
            data = db_reports.get_orders_by_day(date_obj)
        elif report_type == "week":
            data = db_reports.get_orders_by_week(date_obj)
        else:
            data = db_reports.get_orders_by_month(date_obj)
    else: 
        product_id = request.GET.get("product_id") or None
        category_id = request.GET.get("category_id") or None
        brand_id = request.GET.get("brand_id") or None
        user_id = request.GET.get("user_id") or None

        data = db_reports.get_orders_report(product_id, category_id, brand_id, user_id)

    column_names = {
        "order_id": "ID заказа",
        "user_name": "Пользователь",
        "total": "Сумма заказа",
        "order_date": "Дата создания",
        "product_name": "Товар",
        "brand_name": "Бренд",
        "category_name": "Категория",
        "quantity": "Кол-во товара"
    }

    context = {
        "data": data,
        "products": products,
        "categories": categories,
        "brands": brands,
        "users": users,
        "report_type": report_type,
        "date": date_obj, 
        "column_names": column_names
    }

    return render(request, "admin/admin_reports.html", context)

@user_passes_test(admin_required)
def admin_reports_export(request):
    report_type = request.GET.get("type", "day")
    date_str = request.GET.get("date")
    date = datetime.date.today() if not date_str else datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    product_id = request.GET.get("product_id") or None
    category_id = request.GET.get("category_id") or None
    brand_id = request.GET.get("brand_id") or None
    user_id = request.GET.get("user_id") or None

    if report_type in ["day", "week", "month"]:
        if report_type == "day":
            data = db_reports.get_orders_by_day(date)
        elif report_type == "week":
            data = db_reports.get_orders_by_week(date)
        else:
            data = db_reports.get_orders_by_month(date)
    else:
        data = db_reports.get_orders_report(product_id, category_id, brand_id, user_id)

    column_names = {
        "order_id": "ID заказа",
        "user_name": "Пользователь",
        "total": "Сумма заказа",
        "order_date": "Дата создания",
        "product_name": "Товар",
        "brand_name": "Бренд",
        "category_name": "Категория",
        "quantity": "Кол-во товара"
    }

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{date}.csv"'
    response.write(u'\ufeff'.encode('utf8')) 

    writer = csv.writer(response, dialect='excel')

    if data:
        headers = [column_names.get(k, k) for k in data[0].keys()]
        writer.writerow(headers)

        for row in data:
            writer.writerow(row.values())

    return response

@user_passes_test(admin_required)
def audit_log_view(request):
    logs = AuditLog.objects.select_related('user').all()
    return render(request, 'admin/audit_log.html', {'logs': logs})


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)