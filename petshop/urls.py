from django.urls import path, include
from petshop import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'), 
    path('pickup/', views.pickup, name='pickup'),
    path('faq/', views.faq, name='faq'),
    path('contacts/', views.contacts, name='contacts'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path('my-profile/', views.profile_redirect, name='my_profile'),
    path('api/', include('api_shop.urls')),
    path('catalog/', views.product_list, name='product_list'), 
    path('delete_account/', views.delete_account, name='delete_account'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path("checkout/", views.checkout, name="checkout"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
    path("product/<int:product_id>/review/", views.add_review, name="add_review"),
    path('reports/', views.admin_reports, name='admin_reports'),
    path('reports/summaries/', views.admin_summaries, name='admin_summaries'),
    path('reports/summaries/<str:summary>/', views.view_summary, name='view_summary'),
    path('reports/charts/', views.sales_charts, name='sales_charts'),
    path("reports/admin_statement/", views.admin_statement, name="admin_statement"),
    path('reports/admin_statement/export/', views.admin_reports_export, name='admin_reports_export'),
    path('reports/audit-log/', views.audit_log_view, name='audit_log'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('reviews/add/<int:product_id>/',views.add_review, name='add-review-page'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)