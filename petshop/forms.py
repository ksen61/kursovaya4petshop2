from django import forms
from django.contrib.auth.hashers import make_password
from .models import User, UserProfile, Cart, Order, Review, Product, PickupPoint
import re
from datetime import date
from django.core.exceptions import ValidationError
import datetime


class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(label="Имя", max_length=50)
    last_name = forms.CharField(label="Фамилия", max_length=50)
    middle_name = forms.CharField(label="Отчество", required=False, max_length=50)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Телефон", max_length=16, help_text="Формат: +7XXXXXXXXXX")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль", min_length=6)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Подтвердите пароль")
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Дата рождения",
        required=True
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone', 'password', 'date_of_birth']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        pattern = r'^\+7\d{10}$'
        if not re.match(pattern, phone):
            raise forms.ValidationError("Телефон должен быть в формате +7XXXXXXXXXX")
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob >= date.today():
            raise forms.ValidationError("Дата рождения не может быть в будущем")
        return dob

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password != password_confirm:
            raise forms.ValidationError("Пароли не совпадают")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                date_of_birth=self.cleaned_data['date_of_birth']
            )
        return user

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'  
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class UserLoginForm(forms.Form):
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={'class': 'form-input'}),
        max_length=254
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        min_length=6
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise ValidationError("Поле Email обязательно для заполнения")
        if len(email) > 254:
            raise ValidationError("Email слишком длинный")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if not password:
            raise ValidationError("Поле Пароль обязательно для заполнения")
        if len(password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")
        if len(password) > 128:
            raise ValidationError("Пароль слишком длинный")
        return password

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user_qs = User.objects.filter(email=email)
            if not user_qs.exists():
                raise ValidationError("Неверный email или пароль")
            user = user_qs.first()
            if not user.check_password(password):
                raise ValidationError("Неверный email или пароль")
        return cleaned_data



class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, label="Имя")
    last_name = forms.CharField(max_length=50, required=True, label="Фамилия")
    middle_name = forms.CharField(max_length=50, required=False, label="Отчество")
    email = forms.EmailField(required=True, label="Email")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Дата рождения"
    )
    theme = forms.BooleanField(required=False, label="Тёмная тема")

    class Meta:
        model = UserProfile
        fields = ['date_of_birth', 'theme']

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name')
        if not name.isalpha():
            raise ValidationError("Имя должно содержать только буквы")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name')
        if not name.isalpha():
            raise ValidationError("Фамилия должна содержать только буквы")
        return name

    def clean_middle_name(self):
        name = self.cleaned_data.get('middle_name')
        if name and not name.isalpha():
            raise ValidationError("Отчество должно содержать только буквы")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.user.pk).filter(email=email).exists():
            raise ValidationError("Этот email уже занят")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not re.fullmatch(r'^\+7\d{10}$', phone):
            raise ValidationError("Номер должен быть в формате +7XXXXXXXXXX")
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > datetime.date.today():
                raise ValidationError("Дата рождения не может быть в будущем")
        return dob

    def clean_theme(self):
        theme = self.cleaned_data.get('theme')
        if theme not in [True, False, None]:
            raise ValidationError("Некорректное значение темы")
        return theme


class CartAddForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, initial=1, label="Количество")

    class Meta:
        model = Cart
        fields = ['product', 'quantity']

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        product = self.cleaned_data.get('product')

        if product and quantity:
            total_stock = sum(stock.quantity for stock in product.stocks.all())
            if quantity > total_stock:
                raise forms.ValidationError(
                    f"Невозможно добавить {quantity} шт. товара '{product.name}'. В наличии только {total_stock} шт."
                )
        return quantity

    def clean_product(self):
        product = self.cleaned_data.get('product')
        if not product.is_active:
            raise forms.ValidationError("Выбранный товар недоступен")
        return product



class OrderForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Имя*'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Фамилия*'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email*'})
    )
    phone = forms.RegexField(
        regex=r'^\+7\d{10}$',
        error_messages={'invalid': 'Номер должен быть в формате +7XXXXXXXXXX'},
        widget=forms.TextInput(attrs={'placeholder': '+7XXXXXXXXXX'})
    )
    pickup_point = forms.ModelChoiceField(
        queryset=PickupPoint.objects.filter(is_active=True),
        required=True,
        empty_label="Выберите пункт выдачи*"
    )

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name.isalpha():
            raise forms.ValidationError("Имя должно содержать только буквы")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name.isalpha():
            raise forms.ValidationError("Фамилия должна содержать только буквы")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("Email не может быть пустым")
        return email

    def clean_pickup_point(self):
        pickup_point = self.cleaned_data.get('pickup_point')
        if pickup_point is None:
            raise forms.ValidationError("Выберите пункт выдачи")
        return pickup_point


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Ваш отзыв'}),
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Оценка должна быть от 1 до 5")
        return rating

    def clean_text(self):
        text = self.cleaned_data.get('text', '').strip()
        if not text:
            raise forms.ValidationError("Поле отзыва не может быть пустым")
        return text