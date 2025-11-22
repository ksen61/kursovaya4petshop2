from django.urls import path, include
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .views import (
    RegisterAPIView, LoginAPIView, ProfileAPIView, LogoutAPIView, ProductListAPIView, 
    ProductDetailAPIView, AddToCartAPIView, CartAPIView, UpdateCartAPIView, 
    RemoveFromCartAPIView, PickupPointsAPIView, CreateOrderAPIView, OrderDetailAPIView,
    CreateReviewAPIView, OrderHistoryAPIView, AgeCategoryViewSet, PurposeViewSet,
    CategoryViewSet, BrandViewSet, ProductTypeViewSet, SpeciesViewSet, ProductPurposeViewSet, PickupPointViewSet,
    ProductStockViewSet, OrderAdminViewSet, ProductViewSet, UserViewSet, OrdersReportAPIView, CreateBackupAPIView,
    RestoreBackupAPIView, ListBackupsAPIView, ChartsDataAPIView, SummaryTablesAPIView, UsersImportAPIView, UsersExportAPIView
)
from .permissions import IsAdminUserRole

schema_view = get_schema_view(
    openapi.Info(
        title="Yes of Кусь API",
        default_version='v1',
        description="API для магазина: регистрация, авторизация, продукты, корзина, заказы, возрастные категории",
    ),
    public=False,
    permission_classes=[IsAdminUserRole],
)

router = DefaultRouter()
router.register(r'age-categories', AgeCategoryViewSet, basename='agecategory')
router.register(r'purposes', PurposeViewSet, basename='purpose')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'product-types', ProductTypeViewSet, basename='producttype')
router.register(r'species', SpeciesViewSet, basename='species')
router.register(r'product-purposes', ProductPurposeViewSet, basename='product-purpose')
router.register(r'pickup-points', PickupPointViewSet, basename='pickup-point')
router.register(r'product-stocks', ProductStockViewSet, basename='product-stock')
router.register(r'admin/orders', OrderAdminViewSet, basename='admin-orders')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),

    path('register/', RegisterAPIView.as_view(), name='api_register'),
    path('login/', LoginAPIView.as_view(), name='api_login'),
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('logout/', LogoutAPIView.as_view(), name='logout_api'),
    path('products/public/', ProductListAPIView.as_view(), name='api_products'),
    path('products/public/<int:pk>/', ProductDetailAPIView.as_view(), name='api-product-detail'),
    path('cart/add/<int:product_id>/', AddToCartAPIView.as_view(), name='api-add-to-cart'),
    path('cart/', CartAPIView.as_view(), name='api-cart'),
    path('cart/update/<int:item_id>/', UpdateCartAPIView.as_view(), name='api-cart-update'),
    path('cart/remove/<int:item_id>/', RemoveFromCartAPIView.as_view(), name='api-cart-remove'),
    path('pickup_points/', PickupPointsAPIView.as_view(), name='api-pickup-points'),
    path('orders/create/', CreateOrderAPIView.as_view(), name='api-create-order'),
    path('orders/<int:pk>/', OrderDetailAPIView.as_view(), name='api-order-detail'),
    path('orders/history/', OrderHistoryAPIView.as_view(), name='api-order-history'),
    path('reviews/add/<int:product_id>/', CreateReviewAPIView.as_view(), name='create-review'),
    path('api/orders-report/', OrdersReportAPIView.as_view(), name='api_orders_report'),
    path('admin/backups/create/', CreateBackupAPIView.as_view(), name='api_create_backup'),
    path('admin/backups/restore/', RestoreBackupAPIView.as_view(), name='api_restore_backup'),
    path('admin/backups/list/', ListBackupsAPIView.as_view(), name='api_list_backups'),
    path('charts-data/', ChartsDataAPIView.as_view(), name='charts_data_api'),
    path('summary-tables/', SummaryTablesAPIView.as_view(), name='summary_tables'),
    path('import_users/', UsersImportAPIView.as_view(), name='api_import_users'),
    path('export_users/', UsersExportAPIView.as_view(), name='api_export_users'),

    path('', include(router.urls)),

]