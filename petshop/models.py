from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class Role(models.Model):
    name = models.CharField("Название роли", max_length=50, unique=True)
    class Meta:
            verbose_name = "Роль"
            verbose_name_plural = "Роли"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    role = models.ForeignKey('Role', verbose_name="Роль", on_delete=models.PROTECT, default=1)
    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    middle_name = models.CharField("Отчество", max_length=50, blank=True, null=True)
    email = models.EmailField("Электронная почта", unique=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    is_active = models.BooleanField("Активен", default=True)
    is_staff = models.BooleanField("Персонал", default=False)
    date_joined = models.DateTimeField("Дата регистрации", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class UserProfile(models.Model):
    user = models.OneToOneField(User, verbose_name="Пользователь", on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField("Дата рождения", blank=True, null=True)
    theme = models.BooleanField("Тёмная тема", default=False)
    date_format = models.CharField("Формат даты", max_length=20, default="%d.%m.%Y") 

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField("Название бренда", max_length=100)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self):
        return self.name

class AgeCategory(models.Model):
    age_name = models.CharField("Возрастная категория", max_length=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Возрастная категория"
        verbose_name_plural = "Возрастная категория"

    def __str__(self):
        return self.age_name

class ProductType(models.Model):
    type_name = models.CharField("Тип", max_length=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Тип товара"
        verbose_name_plural = "Тип товара"

    def __str__(self):
        return self.type_name

class Species(models.Model):
    species_name = models.CharField("Вид животного", max_length=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Вид животного"
        verbose_name_plural = "Вид животного"

    def __str__(self):
        return self.species_name

class Purpose(models.Model):
    purpose_name = models.CharField("Назначение", max_length=100)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Назначение"
        verbose_name_plural = "Назначение"

    def __str__(self):
        return self.purpose_name


class Product(models.Model):
    category = models.ForeignKey(Category, verbose_name="Категория", on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, verbose_name="Бренд", on_delete=models.SET_NULL, null=True, blank=True)
    age_category = models.ForeignKey(AgeCategory, verbose_name="Возрастная категория", on_delete=models.SET_NULL, null=True, blank=True)
    product_type = models.ForeignKey(ProductType, verbose_name="Тип товара", on_delete=models.SET_NULL, null=True, blank=True)
    species = models.ForeignKey(Species, verbose_name="Вид", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField("Название товара", max_length=100)
    description = models.TextField("Описание", blank=True, null=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    stock = models.IntegerField("Остаток", default=0)
    image = models.ImageField("Изображение", max_length=255, blank=True, null=True)
    is_active = models.BooleanField("Активен", default=True)
    purposes = models.ManyToManyField(Purpose, through='ProductPurpose', related_name='products')

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
            return self.name
    
class ProductPurpose(models.Model):
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE)
    purpose = models.ForeignKey(Purpose, verbose_name="Назначение", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Назначение товара"
        verbose_name_plural = "Назначение товара"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    def get_total_price(self):
        return self.product.price * self.quantity
    
    def get_stock(self):
        return sum(stock.quantity for stock in self.product.stocks.all())

class PickupPoint(models.Model):
    address = models.CharField("Адрес", max_length=255)
    working_hours = models.CharField("Часы работы", max_length=100, blank=True, null=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Пункт выдачи"
        verbose_name_plural = "Пункты выдачи"

    def __str__(self):
        return self.address


class ProductStock(models.Model):
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name='stocks')
    pickup_point = models.ForeignKey(PickupPoint, verbose_name="Пункт выдачи", on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField("Количество", default=0)

    class Meta:
        verbose_name = "Остаток на пункте выдачи"
        verbose_name_plural = "Остатки на пунктах выдачи"


class Order(models.Model):
    STATUS_CHOICES = [
        ('В обработке', 'В обработке'),
        ('В работе', 'В работе'),
        ('Завершён', 'Завершён'),
        ('Получен', 'Получен'),

    ]
    user = models.ForeignKey(User, verbose_name="Пользователь", on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField("Номер заказа", max_length=20, unique=True)
    pickup_point = models.ForeignKey(PickupPoint, verbose_name="Пункт выдачи", on_delete=models.PROTECT)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='В обработке')
    total_price = models.DecimalField("Итоговая сумма", max_digits=10, decimal_places=2)
    date_created = models.DateTimeField("Дата создания", auto_now_add=True)
    date_updated = models.DateTimeField("Дата обновления", auto_now=True)
    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    text = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)



class OrdersByCategory(models.Model):
    id = models.IntegerField(primary_key=True) 
    category_name = models.CharField(max_length=255)
    total_orders = models.IntegerField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False  
        db_table = 'petshop_orders_by_category'


class OrdersByBrand(models.Model):
    brand_name = models.CharField(max_length=255, primary_key=True)  
    total_orders = models.IntegerField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'petshop_orders_by_brand'


class OrdersByMonth(models.Model):
    month = models.DateField(primary_key=True)
    total_orders = models.IntegerField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'petshop_orders_by_month'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Создание'),
        ('UPDATE', 'Изменение'),
        ('DELETE', 'Удаление'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    table_name = models.CharField(max_length=100) 
    row_id = models.BigIntegerField()          
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    action_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-action_time']

    def __str__(self):
        return f"{self.user} {self.action} {self.table_name}#{self.row_id}"