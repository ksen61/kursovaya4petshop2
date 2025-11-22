from rest_framework import serializers
from petshop.models import User, UserProfile, Product, Cart, Category, Brand, ProductType, Species, ProductPurpose, Purpose, PickupPoint, ProductStock, Review, Order, OrderItem, OrdersByCategory, OrdersByBrand, OrdersByMonth
from rest_framework.validators import UniqueValidator
import re


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Такой email уже зарегистрирован.")]
    )
    password = serializers.CharField(write_only=True, min_length=8)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    middle_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'middle_name', 'phone', 'password', 'date_of_birth']

    def create(self, validated_data):
        date_of_birth = validated_data.pop('date_of_birth', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user, date_of_birth=date_of_birth)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=True)
    last_name = serializers.CharField(source='user.last_name', required=True)
    email = serializers.EmailField(source='user.email', required=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)

    date_format = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={'invalid': 'Неверный формат даты'}
    )

    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'date_of_birth', 'date_format', 'theme'
        ]

    def validate_first_name(self, value):
        return self._validate_russian_name(value, "Имя")

    def validate_last_name(self, value):
        return self._validate_russian_name(value, "Фамилия")

    def _validate_russian_name(self, value, field_name, required=True):
        if required and not value:
            raise serializers.ValidationError(f"{field_name} обязательно для заполнения")
        
        if value:
            value = value.strip()
            
            if not re.match(r'^[а-яёА-ЯЁ]+([-\s][а-яёА-ЯЁ]+)*$', value):
                raise serializers.ValidationError(
                    f"{field_name} должно содержать только русские буквы, дефисы и пробелы между словами"
                )
            
            if len(value) < 2:
                raise serializers.ValidationError(f"{field_name} слишком короткое (минимум 2 символа)")
            
            if len(value) > 50:
                raise serializers.ValidationError(f"{field_name} слишком длинное (максимум 50 символов)")
        
        return value

    def validate(self, attrs):
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.date_of_birth:
            data['date_of_birth'] = instance.date_of_birth.strftime("%Y-%m-%d")
        return data


    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_type = serializers.StringRelatedField()
    category = serializers.StringRelatedField()
    brand = serializers.StringRelatedField()
    age_category = serializers.StringRelatedField()
    species = serializers.StringRelatedField()
    purposes = serializers.StringRelatedField(many=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'image',
            'category', 'brand', 'product_type', 'age_category', 'species', 'purposes'
        ]

    def get_image(self, obj):
        return obj.image.url if obj.image else ''


class ProductCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'image', 'category',
            'brand', 'product_type', 'age_category', 'species', 'purposes', 'stock', 'is_active'
        ]

class PurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purpose
        fields = ['purpose_name']

class ProductStockSerializer(serializers.ModelSerializer):
    pickup_point = serializers.CharField(source='pickup_point.address')
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductStock
        fields = ['id', 'product', 'product_name', 'pickup_point', 'quantity']

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.first_name')

    class Meta:
        model = Review
        fields = ['user', 'rating', 'text', 'date_created'] 


class ProductDetailSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    brand = serializers.CharField(source='brand.name', default=None)
    age_category = serializers.CharField(source='age_category.age_name', default=None)
    product_type = serializers.CharField(source='product_type.type_name', default=None)
    species = serializers.CharField(source='species.species_name', default=None)
    purposes = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='purpose_name'
    )
    stocks = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'image',
            'category', 'brand', 'age_category', 'product_type',
            'species', 'purposes', 'stocks', 'reviews', 'can_review'
        ]

    def get_stocks(self, obj):
        return [
            {
                'pickup_point': stock.pickup_point.address,
                'quantity': stock.quantity
            }
            for stock in obj.stocks.all()
        ]

    def get_reviews(self, obj):
        return [
            {
                'user': review.user.first_name,
                'rating': review.rating,
                'text': review.text,
                'created_at': review.date_created.strftime('%Y-%m-%d %H:%M:%S')
            }
            for review in obj.reviews.all()
        ]

    def get_can_review(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return 0

        received_items = OrderItem.objects.filter(
            product=obj,
            order__user=user,
            order__status='Получен'
        )
        existing_reviews_count = Review.objects.filter(product=obj, user=user).count()
        remaining = received_items.count() - existing_reviews_count
        return max(remaining, 0)


class ReviewCreateSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, error_messages={
        'required': 'Оценка обязательна',
        'min_value': 'Минимальная оценка 1',
        'max_value': 'Максимальная оценка 5'
    })
    text = serializers.CharField(required=True, allow_blank=False, error_messages={
        'required': 'Текст отзыва обязателен',
        'blank': 'Текст отзыва не может быть пустым'
    })

    class Meta:
        model = Review
        fields = ['rating', 'text']


class AddToCartSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, error_messages={
        'required': 'Количество обязательно',
        'min_value': 'Минимальное количество — 1'
    })


class CartProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image']

    def get_image(self, obj):
        return obj.image.url if obj.image else ''
    

class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'product', 'quantity', 'total']

    def get_total(self, obj):
        return obj.product.price * obj.quantity
    

class OrdersByCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdersByCategory
        fields = ['id', 'category_name', 'total_orders', 'total_sales', 'avg_order_value']

class OrdersByBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdersByBrand
        fields = ['brand_name', 'total_orders', 'total_sales', 'avg_order_value']

class OrdersByMonthSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdersByMonth
        fields = ['month', 'total_orders', 'total_sales', 'avg_order_value']


from petshop.models import AgeCategory

class AgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeCategory
        fields = ['id', 'age_name', 'is_active']
        
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'is_active']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'is_active']

class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ['id', 'type_name', 'is_active']

class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ['id', 'species_name', 'is_active']

class ProductPurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPurpose
        fields = ['id', 'product', 'purpose']
    
class PickupPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupPoint
        fields = ['id', 'address', 'working_hours', 'is_active']

class RestoreBackupSerializer(serializers.Serializer):
    backup_file = serializers.FileField(required=True, help_text="Выберите ZIP файл для восстановления")

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True) 

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    pickup_point = serializers.CharField(source='pickup_point.address', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user_email', 'pickup_point', 'status',
            'total_price', 'date_created', 'date_updated',
            'first_name', 'last_name', 'email', 'phone', 'items'
        ]

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'middle_name', 
            'email', 'phone', 'role', 'is_active', 'is_staff', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'middle_name', 'email', 
            'phone', 'role', 'is_active', 'is_staff', 'password'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    

class AuditLogSerializer(serializers.Serializer):
    action_time = serializers.DateTimeField()
    user = serializers.CharField()
    table_name = serializers.CharField()
    row_id = serializers.IntegerField()
    action = serializers.CharField()
    old_data = serializers.JSONField()
    new_data = serializers.JSONField()