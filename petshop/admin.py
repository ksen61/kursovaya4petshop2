from django.contrib import admin
from django.db import connection
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.forms.models import model_to_dict
from datetime import datetime, date
from .models import (
    Role, User, UserProfile,
    Category, Brand, AgeCategory, ProductType, Species, Purpose,
    Product, ProductPurpose,
    Cart,
    PickupPoint, ProductStock,
    Order, OrderItem,
    Review,
    ProductPurpose
)


class AuditLogAdminMixin:
    def is_admin_in_admin_panel(self, request):
        if not hasattr(request, 'path') or not request.path.startswith('/admin/'):
            return False
            
        return (request.user.is_authenticated and 
                hasattr(request.user, 'role') and 
                request.user.role.name == 'Администратор')

    def save_model(self, request, obj, form, change):
        if self.is_admin_in_admin_panel(request):
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL myapp.current_user_id = %s", [request.user.id])
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        if self.is_admin_in_admin_panel(request):
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL myapp.current_user_id = %s", [request.user.id])
        super().delete_model(request, obj)


def serialize_for_json(data):
    result = {}
    for k, v in data.items():
        if isinstance(v, (datetime, date)):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


class UserAuditLogAdminMixin:
    def is_admin_in_admin_panel(self, request):
        if not hasattr(request, 'path') or not request.path.startswith('/admin/'):
            return False
            
        if (request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'id') and 
            request.user.id is not None and 
            request.user.id != 0):
            
            return (
                hasattr(request.user, 'role') and 
                request.user.role and 
                hasattr(request.user.role, 'name') and 
                request.user.role.name == 'Администратор'
            )
        return False

    def log_action(self, request, obj, action):
        if not self.is_admin_in_admin_panel(request):
            return
            
        from .models import AuditLog

        new_data = serialize_for_json(model_to_dict(obj))
        old_data = serialize_for_json(getattr(obj, '_old_state', {}))

        if action == 'save':
            act = 'CREATE' if not old_data else 'UPDATE'
            try:
                AuditLog.objects.create(
                    user=request.user,
                    table_name=obj._meta.db_table,
                    row_id=obj.pk,
                    action=act,
                    old_data=None if act == 'CREATE' else old_data,
                    new_data=new_data
                )
            except Exception as e:
                print(f"Ошибка при создании аудит-лога: {e}")

        elif action == 'delete':
            try:
                AuditLog.objects.create(
                    user=request.user,
                    table_name=obj._meta.db_table,
                    row_id=obj.pk,
                    action='DELETE',
                    old_data=new_data,
                    new_data=None
                )
            except Exception as e:
                print(f"Ошибка при создании аудит-лога: {e}")

    def save_model(self, request, obj, form, change):
        if self.is_admin_in_admin_panel(request) and obj.pk:
            try:
                obj._old_state = model_to_dict(obj.__class__.objects.get(pk=obj.pk))
            except obj.__class__.DoesNotExist:
                obj._old_state = {}
        
        super().save_model(request, obj, form, change)
        self.log_action(request, obj, 'save')

    def delete_model(self, request, obj):
        self.log_action(request, obj, 'delete')
        super().delete_model(request, obj)


class ProductPurposesInline(AuditLogAdminMixin,admin.TabularInline):
    model = ProductPurpose
    extra = 1


@admin.register(User)
class UserAdmin(UserAuditLogAdminMixin, BaseUserAdmin):
    list_display = ('id', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'role')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'role')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('email',)

@admin.register(Category)
class CategoryAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Brand)
class BrandAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(AgeCategory)
class AgeCategoryAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'age_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('age_name',)

@admin.register(ProductType)
class ProductTypeAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'type_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('type_name',)

@admin.register(Species)
class SpeciesAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'species_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('species_name',)

@admin.register(Purpose)
class PurposeAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'purpose_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('purpose_name',)

@admin.register(Product)
class ProductAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'brand', 'price', 'stock', 'is_active')
    list_filter = ('category', 'brand', 'is_active')
    search_fields = ('name', 'description')
    inlines = [ProductPurposesInline]

@admin.register(ProductPurpose)
class ProductPurposeAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'product', 'purpose')
    list_filter = ('purpose', 'product')
    search_fields = ('product__name', 'purpose__purpose_name')

@admin.register(PickupPoint)
class PickupPointAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'address', 'working_hours', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('address',)

@admin.register(ProductStock)
class ProductStockAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'product', 'pickup_point', 'quantity')
    list_filter = ('pickup_point', 'product')
    search_fields = ('product__name', 'pickup_point__address')




class OrderAuditMixin:    
    def save_model(self, request, obj, form, change):
        if (request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role.name == 'Администратор'):
            
            print(f"Admin {request.user} {'updated' if change else 'created'} order {obj.id}")
        
        super().save_model(request, obj, form, change)
    
    def delete_model(self, request, obj):
        if (request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role.name == 'Администратор'):
            
            print(f"Admin {request.user} deleted order {obj.id}")
        
        super().delete_model(request, obj)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_number', 'user', 'pickup_point', 
        'status', 'total_price', 'date_created', 'date_updated'
    )
    list_filter = ('status', 'pickup_point')
    search_fields = ('order_number', 'user__first_name', 'user__last_name')
    
    readonly_fields = [
        'order_number', 'user', 'pickup_point', 'total_price',
        'first_name', 'last_name', 'email', 'phone',
        'date_created', 'date_updated'
    ]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def save_model(self, request, obj, form, change):
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL myapp.disable_audit = true")
            cursor.execute("SET LOCAL myapp.current_user_id = %s", [request.user.id] if request.user.is_authenticated else [1]) 
        super().save_model(request, obj, form, change)