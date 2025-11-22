from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from django.contrib.auth import login, authenticate
from django.db import transaction, connection
from .serializers import RegisterSerializer, ProfileSerializer, ReviewCreateSerializer, AddToCartSerializer, CartItemSerializer, ProductDetailSerializer, PurposeSerializer, CategorySerializer, BrandSerializer, AgeCategorySerializer, ProductTypeSerializer, SpeciesSerializer, ProductPurposeSerializer, PickupPointSerializer, ProductStockSerializer, OrderSerializer, OrderStatusUpdateSerializer, ProductSerializer, ProductCreateUpdateSerializer, UserSerializer, UserCreateUpdateSerializer, RestoreBackupSerializer
from rest_framework.permissions import IsAuthenticated
from petshop.models import UserProfile, User, Product, Cart, OrderItem, Review, Order, PickupPoint, ProductStock, Purpose, Category, Brand, AgeCategory, ProductType, Species, ProductPurpose, OrdersByCategory, OrdersByBrand, OrdersByMonth, Role
from django.contrib.auth import logout
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.views.generic.edit import FormView
from petshop.forms import ReviewForm
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import uuid
from django.db.models import Sum, Count
from .permissions import IsAdminUserRole
from django.http import HttpResponse, JsonResponse
import csv
from datetime import datetime, timedelta, date
from django.db.models import Q
import os
import json
import zipfile
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import FileResponse
import sqlite3
import tempfile
from decimal import Decimal
from django.contrib.auth import get_user_model
from io import TextIOWrapper, StringIO

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterAPIView(APIView):
    @swagger_auto_schema(
        tags=['Регистрация'],
        operation_summary="Регистрация нового пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль'),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Дата рождения'),
            },
        ),
        responses={
            201: openapi.Response(description="Регистрация успешна", examples={
                "application/json": {"message": "Регистрация успешна! Вы авторизованы."}
            }),
            400: openapi.Response(description="Ошибка валидации", examples={
                "application/json": {"Ошибка": {"email": ["Такой email уже зарегистрирован"]}}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."}
            }),
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    date_of_birth = serializer.validated_data.get('date_of_birth')
                    if date_of_birth:
                        today = date.today()
                        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                        if age < 18:
                            return Response(
                                {"errors": {"date_of_birth": ["Для регистрации должно быть больше 18 лет"]}},
                                status=status.HTTP_400_BAD_REQUEST
                            )

                    user = serializer.save()

                    try:
                        default_role = Role.objects.get(name="Покупатель")
                        user.role = default_role
                        user.save()
                    except Role.DoesNotExist:
                        logger.error("Роль 'Покупатель' не найдена в БД")
                        return Response(
                            {"Ошибка": "Произошла ошибка на сервера. Попробуйте позже."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

                    user_auth = authenticate(
                        request,
                        email=user.email,
                        password=request.data.get("password")
                    )
                    if not user_auth:
                        return Response(
                            {"Ошибка": "Не удалось автоматически войти после регистрации."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    login(request, user_auth)
                    return Response(
                        {"message": "Регистрация успешна! Вы авторизованы."},
                        status=status.HTTP_201_CREATED
                    )

            except Exception as e:
                logger.exception("Ошибка при регистрации")
                return Response(
                    {"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class LoginAPIView(APIView):
    @swagger_auto_schema(
        tags=['Авторизация'],
        operation_summary="Авторизация пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль'),
            },
        ),
        responses={
            200: openapi.Response(description="Успешный вход", examples={
                "application/json": {"message": "Вы успешно вошли в систему."}
            }),
            400: openapi.Response(description="Отсутствуют обязательные поля", examples={
                "application/json": {"Ошибка": "Email и пароль обязательны."}
            }),
            401: openapi.Response(description="Неверный логин или пароль", examples={
                "application/json": {"Ошибка": "Неверный email или пароль."}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."}
            }),
        }
    )
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")

            if not email or not password:
                return Response(
                    {"Ошибка": "Email и пароль обязательны."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return Response(
                    {"message": "Вы успешно вошли в систему."},
                    status=status.HTTP_200_OK
                )

            return Response(
                {"Ошибка": "Неверный email или пароль."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.exception("Ошибка при авторизации")
            return Response(
                {"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Просмотр профиля",
        tags=['Профиль пользователя'],
        responses={
            200: openapi.Response(description="Данные профиля", examples={
                "application/json": {
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "email": "ivan@example.com",
                    "phone": "+71234567890",
                    "date_of_birth": "2000-01-01",
                    "theme": True
                }
            }),
            401: openapi.Response(description="Не авторизован", examples={
                "application/json": {"Ошибка": "Требуется авторизация"}
            }),
        }
    )
    def get(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"Ошибка": "Профиль пользователя не найден."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Ошибка при получении профиля")
            return Response(
                {"Ошибка": "Не удалось загрузить профиль. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Обновление профиля",
        tags=['Профиль пользователя'],
        request_body=ProfileSerializer,
        responses={
            200: openapi.Response(description="Профиль успешно обновлён", examples={
                "application/json": {"message": "Профиль успешно обновлён"}
            }),
            400: openapi.Response(description="Ошибки валидации", examples={
                "application/json": {"errors": {"first_name": ["Это поле обязательно"], "email": ["Неверный формат"]}}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"Ошибка": "Не удалось обновить профиль. Попробуйте позже."}
            }),
        }
    )
    def put(self, request):
        try:
            serializer = ProfileSerializer(
                instance=request.user.profile,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                date_of_birth = serializer.validated_data.get('date_of_birth')
                if date_of_birth:
                    today = date.today()
                    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                    if age < 18:
                        return Response(
                            {"errors": {"date_of_birth": ["Для использования сервиса должно быть больше 18 лет"]}},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                serializer.save()
                return Response({"message": "Профиль успешно обновлён"}, status=status.HTTP_200_OK)
            else:
                errors = {field: [str(e) for e in msgs] for field, msgs in serializer.errors.items()}
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response(
                {"Ошибка": "Профиль пользователя не найден."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Ошибка при обновлении профиля")
            return Response(
                {"Ошибка": "Не удалось обновить профиль. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Удаление аккаунта",
        tags=['Профиль пользователя'],
        responses={
            200: openapi.Response(description="Аккаунт удалён", examples={
                "application/json": {"message": "Аккаунт удалён"}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"Ошибка": "Не удалось удалить аккаунт. Попробуйте позже."}
            }),
        }
    )
    def delete(self, request):
        try:
            request.user.delete()
            return Response({"message": "Аккаунт удалён"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при удалении аккаунта")
            return Response(
                {"Ошибка": "Не удалось удалить аккаунт. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Выход из аккаунта",
        tags=['Выход из аккаунта'],
        responses={
            200: openapi.Response(
                description="Успешный выход из системы",
                examples={
                    "application/json": {
                        "message": "Вы вышли"
                    }
                }
            ),
            401: openapi.Response(
                description="Пользователь не авторизован",
                examples={
                    "application/json": {
                        "detail": "Учетные данные не были предоставлены."
                    }
                }
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={
                    "application/json": {
                        "Ошибка": "Не удалось выйти. Попробуйте позже."
                    }
                }
            )
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            logout(request)
            return Response({'message': 'Вы вышли'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при выходе из аккаунта")
            return Response(
                {'Ошибка': 'Не удалось выйти. Попробуйте позже.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=['Товар'],
        operation_summary="Список товаров с фильтрацией",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по категориям"),
            openapi.Parameter('brand', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по брендам"),
            openapi.Parameter('type', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по типу"),
            openapi.Parameter('age', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по возрасту"),
            openapi.Parameter('species', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по виду животного"),
            openapi.Parameter('purpose', openapi.IN_QUERY, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), description="Фильтр по назначению"),
            openapi.Parameter('search_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Поиск по названию"),
            openapi.Parameter('price_min', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, description="Минимальная цена"),
            openapi.Parameter('price_max', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, description="Максимальная цена"),
            openapi.Parameter('pickup_point', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="ID пункта выдачи"),
        ],
        responses={
            200: openapi.Response(description="Список товаров", schema=ProductSerializer(many=True)),
            400: openapi.Response(description="Ошибка параметров фильтрации", examples={"application/json": {"error": "Некорректные параметры фильтрации"}}),
            404: openapi.Response(description="Пункт выдачи не найден", examples={"application/json": {"error": "Пункт выдачи не найден"}}),
            500: openapi.Response(description="Ошибка сервера", examples={"application/json": {"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."}})
        }
    )
    def get(self, request):
        try:
            products = Product.objects.filter(is_active=True)

            filters_map = {
                'category': 'category',
                'brand': 'brand',
                'type': 'product_type',
                'age': 'age_category',
                'species': 'species',
                'purpose': 'purposes'
            }

            for param, field_name in filters_map.items():
                ids = request.GET.getlist(param)
                if ids:
                    try:
                        ids_int = [int(i) for i in ids]
                    except ValueError:
                        return Response({"error": f"Некорректный формат параметра {param}"}, status=400)
                    
                    model_class = getattr(Product._meta.get_field(field_name), 'related_model', None)
                    if model_class:
                        valid_ids = model_class.objects.filter(id__in=ids_int).values_list('id', flat=True)
                        invalid_ids = set(ids_int) - set(valid_ids)
                        if invalid_ids:
                            return Response({"error": f"Некорректные {param} ID: {', '.join(map(str, invalid_ids))}"}, status=400)
                    products = products.filter(**{f"{field_name}__id__in": ids_int})

            search_name = request.GET.get('search_name')
            if search_name:
                products = products.filter(name__icontains=search_name)

            price_min = request.GET.get('price_min')
            price_max = request.GET.get('price_max')
            try:
                if price_min is not None:
                    price_min = float(price_min)
                    if price_min < 0:
                        return Response({"error": "Минимальная цена не может быть отрицательной"}, status=400)
                    products = products.filter(price__gte=price_min)

                if price_max is not None:
                    price_max = float(price_max)
                    if price_max < 0:
                        return Response({"error": "Максимальная цена не может быть отрицательной"}, status=400)
                    products = products.filter(price__lte=price_max)
            except ValueError:
                return Response({"error": "Некорректное значение цены"}, status=400)

            pickup_point_id = request.GET.get('pickup_point')
            if pickup_point_id:
                try:
                    pickup_point_id = int(pickup_point_id)
                except ValueError:
                    return Response({"error": "Некорректный ID пункта выдачи"}, status=400)
                
                pickup_point = PickupPoint.objects.filter(id=pickup_point_id, is_active=True).first()
                if not pickup_point:
                    return Response({"error": "Пункт выдачи не найден"}, status=404)

                stock_qs = ProductStock.objects.filter(
                    pickup_point=pickup_point,
                    quantity__gt=0,
                    product__is_active=True
                )
                product_ids = stock_qs.values_list('product_id', flat=True).distinct()
                products = products.filter(id__in=product_ids)
            else:
                stock_qs = ProductStock.objects.filter(quantity__gt=0, product__is_active=True)
                available_product_ids = stock_qs.values_list('product_id', flat=True).distinct()
                products = products.filter(id__in=available_product_ids)

            sort = request.GET.get('sort')
            if sort:
                if sort == 'price_asc':
                    products = products.order_by('price')
                elif sort == 'price_desc':
                    products = products.order_by('-price')
                elif sort == 'name_asc':
                    products = products.order_by('name')
                elif sort == 'name_desc':
                    products = products.order_by('-name')

            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Ошибка при получении списка товаров")
            return Response({"Ошибка": "Произошла ошибка на сервере. Попробуйте позже."}, status=500)


class ProductDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=['Товар'],
        operation_summary="Получение детальной информации о товаре",

        responses={
            200: openapi.Response(
                description="Успешное получение информации о товаре",
                schema=ProductDetailSerializer()
            ),
            404: openapi.Response(
                description="Товар не найден",
                examples={"application/json": {"error": "Товар не найден"}}
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                examples={"application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}}
            ),
        }
    )
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"error": "Товар не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Ошибка при получении товара")
            return Response(
                {"error": "Произошла ошибка на сервере. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)




class AddToCartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Добавление товара в корзину",
        tags=['Корзина'],
        request_body=AddToCartSerializer,
        manual_parameters=[
            openapi.Parameter(
                'product_id', openapi.IN_PATH, description="ID товара", type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response(description="Товар добавлен в корзину", examples={
                "application/json": {"message": "Товар добавлен в корзину"}
            }),
            400: openapi.Response(description="Ошибка валидации или превышено количество", examples={
                "application/json": {"error": "Максимальное кол-во товаров превышено"}
            }),
            404: openapi.Response(description="Товар не найден", examples={
                "application/json": {"error": "Товар не найден"}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}
            }),
        }
    )
    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id, is_active=True)

            serializer = AddToCartSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            quantity = serializer.validated_data['quantity']

            total_stock = product.stocks.aggregate(total=Sum('quantity'))['total'] or 0

            existing_item = Cart.objects.filter(user=request.user, product=product).first()
            existing_quantity = existing_item.quantity if existing_item else 0

            if quantity + existing_quantity > total_stock:
                return Response(
                    {"error": f"Максимальное количество товара превышено. Доступно {total_stock - existing_quantity}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if existing_item:
                existing_item.quantity += quantity
                existing_item.save()
            else:
                Cart.objects.create(user=request.user, product=product, quantity=quantity)

            return Response({"message": "Товар добавлен в корзину"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Ошибка при добавлении товара в корзину")
            return Response(
                {"error": "Произошла ошибка на сервере. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Корзина'],
        operation_summary="Просмотр корзины пользователя",
        responses={
            200: openapi.Response(
                description="Корзина пользователя",
                examples={
                    "application/json": {
                        "items": [
                            {
                                "id": 1,
                                "product": {
                                    "id": 10,
                                    "name": "Корм для кошек",
                                    "price": 500,
                                    "image": "/media/products/cat_food.jpg"
                                },
                                "quantity": 2,
                                "total": 1000
                            }
                        ],
                        "total_price": 1000
                    }
                }
            ),
            401: openapi.Response(
                description="Не авторизован",
                examples={"application/json": {"error": "Требуется авторизация"}}
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                examples={"application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}}
            ),
        }
    )
    def get(self, request):
        try:
            cart_items = Cart.objects.filter(user=request.user)
            serializer = CartItemSerializer(cart_items, many=True)
            total_price = sum([item['total'] for item in serializer.data])
            return Response({'items': serializer.data, 'total_price': total_price}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при получении корзины")
            return Response(
                {"error": "Произошла ошибка на сервере. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

@method_decorator(csrf_exempt, name='dispatch')
class UpdateCartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Обновление количества товара в корзине",
        tags=['Корзина'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['quantity'],
            properties={
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Новое количество товара')
            }
        ),
        responses={
            200: openapi.Response(description="Количество обновлено", examples={"application/json": {"message": "Количество обновлено"}}),
            400: openapi.Response(description="Некорректное количество", examples={"application/json": {"error": "Количество должно быть больше 0"}}),
            404: openapi.Response(description="Элемент корзины не найден", examples={"application/json": {"error": "Элемент корзины не найден"}}),
            500: openapi.Response(description="Ошибка сервера", examples={"application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}})
        }
    )
    def post(self, request, item_id):
        try:
            cart_item = Cart.objects.get(id=item_id, user=request.user)
            quantity = int(request.data.get('quantity', 1))
            if quantity < 1:
                return Response({"error": "Количество должно быть больше 0"}, status=status.HTTP_400_BAD_REQUEST)

            total_stock = sum(ps.quantity for ps in cart_item.product.stocks.all())
            if quantity > total_stock:
                return Response({
                    "error": f"Невозможно установить {quantity}. Доступно только {total_stock}",
                    "current_quantity": cart_item.quantity
                }, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = quantity
            cart_item.save()
            return Response({"message": "Количество обновлено"}, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({"error": "Элемент корзины не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Ошибка при обновлении корзины")
            return Response({"error": "Произошла ошибка на сервере. Попробуйте позже."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveFromCartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Удаление товара из корзины",
        tags=['Корзина'],
        responses={
            200: openapi.Response(description="Товар удалён", examples={"application/json": {"message": "Товар удалён"}}),
            404: openapi.Response(description="Элемент корзины не найден", examples={"application/json": {"error": "Элемент корзины не найден"}}),
            500: openapi.Response(description="Ошибка сервера", examples={"application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}})
        }
    )
    def delete(self, request, item_id):
        try:
            cart_item = Cart.objects.get(id=item_id, user=request.user)
            cart_item.delete()
            return Response({"message": "Товар удалён"}, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({"error": "Элемент корзины не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Ошибка при удалении из корзины")
            return Response({"error": "Произошла ошибка на сервере. Попробуйте позже."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PickupPointViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = PickupPoint.objects.all()
    serializer_class = PickupPointSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Список всех пунктов выдачи",
        tags=['Пункты выдачи'],
        responses={
            200: openapi.Response(
                description="Список успешно получен",
                examples={
                    "application/json": [
                        {"id": 1, "address": "ул. Ленина, д.10", "working_hours": "09:00-18:00", "is_active": True},
                        {"id": 2, "address": "пр. Мира, д.5", "working_hours": "10:00-19:00", "is_active": True}
                    ]
                }
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при получении списка пунктов выдачи")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получение пункта выдачи по ID",
        tags=['Пункты выдачи'],
        responses={
            200: PickupPointSerializer,
            404: openapi.Response(description="Пункт не найден", examples={"application/json": {"detail": "Пункт не найден"}}),
            500: openapi.Response(description="Ошибка сервера", examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}})
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при получении пункта выдачи")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создание нового пункта выдачи",
        tags=['Пункты выдачи'],
        request_body=PickupPointSerializer,
        responses={
            201: PickupPointSerializer,
            400: openapi.Response(description="Ошибка валидации"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Ошибка при создании пункта выдачи")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновление пункта выдачи",
        tags=['Пункты выдачи'],
        request_body=PickupPointSerializer,
        responses={
            200: PickupPointSerializer,
            400: openapi.Response(description="Ошибка валидации"),
            404: openapi.Response(description="Пункт не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при обновлении пункта выдачи")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удаление пункта выдачи",
        tags=['Пункты выдачи'],
        responses={
            204: openapi.Response(description="Пункт успешно удален"),
            404: openapi.Response(description="Пункт не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Пункт успешно удален"}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("Ошибка при удалении пункта выдачи")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PickupPointsAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Список пунктов выдачи",
        tags=['Пункт выдачи'],
        responses={
            200: openapi.Response(
                description="Список пунктов выдачи успешно получен",
                examples={
                    "application/json": [
                        {"id": 1, "name": "ул. Ленина, д.10"},
                        {"id": 2, "name": "пр. Мира, д.5"}
                    ]
                }
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def get(self, request):
        try:
            points = PickupPoint.objects.all()
            data = [{"id": p.id, "name": p.address} for p in points]
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при получении списка пунктов выдачи")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Создание нового заказа",
        tags=['Заказ'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['first_name', 'last_name', 'email', 'phone', 'pickup_point'],
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'pickup_point': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID пункта выдачи'),
            }
        ),
        responses={
            201: openapi.Response(
                description="Заказ успешно создан",
                examples={"application/json": {"message": "Заказ №1 успешно создан", "order_id": 1}}
            ),
            400: openapi.Response(
                description="Ошибка данных",
                examples={
                    "application/json": {
                        "error": "Корзина пуста"
                    }
                }
            ),
            404: openapi.Response(
                description="Пункт выдачи не найден",
                examples={"application/json": {"error": "Пункт выдачи не найден"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def post(self, request):
        user = request.user
        data = request.data

        cart_items = Cart.objects.filter(user=user)
        if not cart_items.exists():
            return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

        pickup_point_id = data.get('pickup_point')
        if not pickup_point_id:
            return Response({"error": "Не выбран пункт выдачи"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pickup_point = get_object_or_404(PickupPoint, id=pickup_point_id)
        except Exception:
            return Response({"error": "Пункт выдачи не найден"}, status=status.HTTP_404_NOT_FOUND)

        total_price = sum(item.get_total_price() for item in cart_items)

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE petshop_order DISABLE TRIGGER ALL")
                    cursor.execute("ALTER TABLE petshop_productstock DISABLE TRIGGER ALL")

                order_number = uuid.uuid4().hex[:20]
                order = Order.objects.create(
                    user=user,
                    order_number=order_number,
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    pickup_point=pickup_point,
                    total_price=total_price,
                    status='В обработке'
                )

                for item in cart_items:
                    order.items.create(
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )

                    stock = ProductStock.objects.filter(
                        product=item.product,
                        pickup_point=pickup_point
                    ).first()

                    if not stock:
                        raise ValueError(f"Товар '{item.product.name}' отсутствует на выбранном пункте выдачи")
                    if stock.quantity < item.quantity:
                        raise ValueError(f"Недостаточно товара '{item.product.name}' на пункте выдачи")
                    
                    stock.quantity -= item.quantity
                    stock.save()

                cart_items.delete()

                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE petshop_order ENABLE TRIGGER ALL")
                    cursor.execute("ALTER TABLE petshop_productstock ENABLE TRIGGER ALL")

                subject = f"Ваш заказ №{order.id} оформлен"
                html_content = render_to_string('shablons/email.html', {'order': order})
                email = EmailMultiAlternatives(
                    subject=subject,
                    body="Ваш email клиент не поддерживает HTML",
                    from_email="ksenpank03@mail.ru",
                    to=[order.email]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

            return Response(
                {"message": f"Заказ №{order.id} успешно создан", "order_id": order.id},
                status=status.HTTP_201_CREATED
            )

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Ошибка при создании заказа")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Просмотр деталей заказа",
        tags=['Заказ'],
        responses={
            200: openapi.Response(
                description="Детали заказа успешно получены",
                schema=OrderSerializer
            ),
            401: openapi.Response(
                description="Неавторизованный доступ",
                examples={"application/json": {"detail": "Требуется авторизация"}}
            ),
            403: openapi.Response(
                description="Доступ запрещён (пользователь пытается получить чужой заказ)",
                examples={"application/json": {"detail": "Нет прав для выполнения действия"}}
            ),
            404: openapi.Response(
                description="Заказ не найден",
                examples={"application/json": {"detail": "Заказ с данным ID не найден"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def get(self, request, pk):
        try:
            order = get_object_or_404(Order, id=pk)

            if order.user != request.user:
                return Response(
                    {"detail": "Нет прав для выполнения действия"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
            return Response(
                {"detail": "Заказ с данным ID не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.exception("Ошибка при получении деталей заказа: %s", str(e))
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Получение истории заказов текущего пользователя",
        tags=['Заказ'],
        responses={
            200: openapi.Response(
                description="Список заказов успешно получен",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "order_number": "a1b2c3d4e5f6g7h8i9j0",
                            "status": "В обработке",
                            "total_price": 6076.0,
                            "pickup_point": "ул. Ленина, д.10",
                            "date_created": "2025-09-29T15:30:00"
                        }
                    ]
                }
            ),
            401: openapi.Response(
                description="Неавторизованный доступ",
                examples={"application/json": {"detail": "Требуется авторизация"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def get(self, request):
        try:
            orders = request.user.orders.all().order_by('-date_created')
            data = [
                {
                    "id": o.id,
                    "order_number": o.order_number,
                    "status": o.status,
                    "total_price": o.total_price,
                    "pickup_point": o.pickup_point.address if o.pickup_point else None,
                    "date_created": o.date_created.isoformat()
                }
                for o in orders
            ]
            return Response(data, status=200)
        except Exception:
            logger.exception("Ошибка при получении истории заказов")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=500
            )



class CreateReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Отзывы'],
        operation_summary="Добавление отзыва к товару",
        request_body=ReviewCreateSerializer,
        manual_parameters=[
            openapi.Parameter(
                'product_id', openapi.IN_PATH, description="ID товара", type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            201: openapi.Response(description="Отзыв успешно создан", examples={
                "application/json": {"message": "Отзыв успешно создан"}
            }),
            400: openapi.Response(description="Ошибка валидации", examples={
                "application/json": {"errors": {"rating": ["Минимальная оценка 1"]}}
            }),
            403: openapi.Response(description="Нельзя оставить отзыв", examples={
                "application/json": {"error": "Вы можете оставить отзыв только после получения товара"}
            }),
            404: openapi.Response(description="Товар не найден", examples={
                "application/json": {"error": "Товар не найден"}
            }),
            500: openapi.Response(description="Ошибка сервера", examples={
                "application/json": {"error": "Произошла ошибка на сервере. Попробуйте позже."}
            }),
        }
    )
    def post(self, request, product_id):
        try:
            product = Product.objects.filter(id=product_id, is_active=True).first()
            if not product:
                return Response({"error": "Товар не найден"}, status=status.HTTP_404_NOT_FOUND)

            user = request.user

            received_count = OrderItem.objects.filter(
                product=product, order__user=user, order__status='Получен'
            ).count()

            existing_count = Review.objects.filter(product=product, user=user).count()

            if received_count == 0:
                return Response({"error": "Вы можете оставить отзыв только после получения товара"},
                                status=status.HTTP_403_FORBIDDEN)
            if existing_count >= received_count:
                return Response({"error": "Вы уже оставили все возможные отзывы на этот товар"},
                                status=status.HTTP_403_FORBIDDEN)

            serializer = ReviewCreateSerializer(data=request.data)
            if serializer.is_valid():
                Review.objects.create(
                    user=user,
                    product=product,
                    rating=serializer.validated_data['rating'],
                    text=serializer.validated_data['text']
                )
                return Response({"message": "Отзыв успешно создан"}, status=status.HTTP_201_CREATED)

            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Ошибка при создании отзыва")
            return Response({"error": "Произошла ошибка на сервере. Попробуйте позже."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class AgeCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = AgeCategory.objects.all()
    serializer_class = AgeCategorySerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех возрастных категорий",
        tags=['Возрастная категория'],
        responses={
            200: AgeCategorySerializer(many=True),
            404: openapi.Response(
                description="Не найдено",
                examples={"application/json": {"detail": "Возрастные категории не найдены"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            if not queryset.exists():
                return Response({"detail": "Возрастные категории не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при получении списка возрастных категорий")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить одну возрастную категорию по ID",
        tags=['Возрастная категория'],
        responses={
            200: AgeCategorySerializer,
            404: openapi.Response(
                description="Не найдено",
                examples={"application/json": {"detail": "Возрастная категория не найдена"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при получении возрастной категории")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новую возрастную категорию",
        tags=['Возрастная категория'],
        request_body=AgeCategorySerializer,
        responses={
            201: AgeCategorySerializer,
            400: openapi.Response(
                description="Некорректные данные",
                examples={"application/json": {"age_name": ["Это поле обязательно."]}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Ошибка при создании возрастной категории")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить возрастную категорию",
        tags=['Возрастная категория'],
        request_body=AgeCategorySerializer,
        responses={
            200: AgeCategorySerializer,
            400: openapi.Response(
                description="Некорректные данные",
                examples={"application/json": {"age_name": ["Это поле обязательно."]}}
            ),
            404: openapi.Response(
                description="Не найдено",
                examples={"application/json": {"detail": "Возрастная категория не найдена"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при обновлении возрастной категории")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить возрастную категорию",
        tags=['Возрастная категория'],
        responses={
            204: openapi.Response(description="Категория удалена"),
            404: openapi.Response(
                description="Не найдено",
                examples={"application/json": {"detail": "Возрастная категория не найдена"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            )
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Возрастная категория удалена"}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("Ошибка при удалении возрастной категории")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurposeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех назначений",
        tags=['Назначение'],
        responses={200: PurposeSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            purposes = self.get_queryset()
            if not purposes.exists():
                return Response({"detail": "Назначения не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(purposes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при получении списка назначений")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить одно назначение по ID",
        tags=['Назначение'],
        responses={200: PurposeSerializer, 404: "Не найдено"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            purpose = self.get_object()
            serializer = self.get_serializer(purpose)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении назначения")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новое назначение",
        tags=['Назначение'],
        request_body=PurposeSerializer,
        responses={201: PurposeSerializer, 400: "Некорректные данные"}
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании назначения")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить назначение по ID",
        tags=['Назначение'],
        request_body=PurposeSerializer,
        responses={200: PurposeSerializer, 404: "Не найдено"}
    )
    def update(self, request, *args, **kwargs):
        try:
            purpose = self.get_object()
            serializer = self.get_serializer(purpose, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении назначения")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить назначение по ID",
        tags=['Назначение'],
        responses={204: "Удалено", 404: "Не найдено"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            purpose = self.get_object()
            purpose.delete()
            return Response({"message": "Назначение удалено"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении назначения")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех категорий",
        tags=['Категории товаров'],
        responses={200: CategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            categories = self.get_queryset()
            if not categories.exists():
                return Response({"detail": "Категории не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при получении списка категорий")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить категорию по ID",
        tags=['Категории товаров'],
        responses={200: CategorySerializer, 404: "Не найдено"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            category = self.get_object()
            serializer = self.get_serializer(category)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении категории")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новую категорию",
        tags=['Категории товаров'],
        request_body=CategorySerializer,
        responses={201: CategorySerializer, 400: "Некорректные данные"}
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании категории")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить категорию по ID",
        tags=['Категории товаров'],
        request_body=CategorySerializer,
        responses={200: CategorySerializer, 404: "Не найдено"}
    )
    def update(self, request, *args, **kwargs):
        try:
            category = self.get_object()
            serializer = self.get_serializer(category, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении категории")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить категорию по ID",
        tags=['Категории товаров'],
        responses={204: "Удалено", 404: "Не найдено"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            category = self.get_object()
            category.delete()
            return Response({"message": "Категория успешно удалена"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении категории")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class BrandViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех брендов",
        tags=['Бренды товаров'],
        responses={200: BrandSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            brands = self.get_queryset()
            if not brands.exists():
                return Response({"detail": "Бренды не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(brands, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при получении списка брендов")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить бренд по ID",
        tags=['Бренды товаров'],
        responses={200: BrandSerializer, 404: "Не найдено"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            brand = self.get_object()
            serializer = self.get_serializer(brand)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении бренда")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новый бренд",
        tags=['Бренды товаров'],
        request_body=BrandSerializer,
        responses={201: BrandSerializer, 400: "Некорректные данные"}
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании бренда")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить бренд по ID",
        tags=['Бренды товаров'],
        request_body=BrandSerializer,
        responses={200: BrandSerializer, 404: "Не найдено"}
    )
    def update(self, request, *args, **kwargs):
        try:
            brand = self.get_object()
            serializer = self.get_serializer(brand, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении бренда")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить бренд по ID",
        tags=['Бренды товаров'],
        responses={204: "Удалено", 404: "Не найдено"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            brand = self.get_object()
            brand.delete()
            return Response({"message": "Бренд успешно удалён"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении бренда")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех типов товаров",
        tags=['Типы товаров'],
        responses={200: ProductTypeSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            types = self.get_queryset()
            if not types.exists():
                return Response({"detail": "Типы товаров не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(types, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Ошибка при получении списка типов товаров")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить тип товара по ID",
        tags=['Типы товаров'],
        responses={200: ProductTypeSerializer, 404: "Не найдено"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            product_type = self.get_object()
            serializer = self.get_serializer(product_type)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении типа товара")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новый тип товара",
        tags=['Типы товаров'],
        request_body=ProductTypeSerializer,
        responses={201: ProductTypeSerializer, 400: "Некорректные данные"}
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании типа товара")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить тип товара по ID",
        tags=['Типы товаров'],
        request_body=ProductTypeSerializer,
        responses={200: ProductTypeSerializer, 404: "Не найдено"}
    )
    def update(self, request, *args, **kwargs):
        try:
            product_type = self.get_object()
            serializer = self.get_serializer(product_type, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении типа товара")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить тип товара по ID",
        tags=['Типы товаров'],
        responses={204: "Удалено", 404: "Не найдено"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            product_type = self.get_object()
            product_type.delete()
            return Response({"message": "Тип товара успешно удалён"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении типа товара")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SpeciesViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список всех видов",
        tags=['Вид животного'],
        responses={200: SpeciesSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            species = self.get_queryset()
            if not species.exists():
                return Response({"detail": "Виды животных не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(species, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении списка видов")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получить вид животного по ID",
        tags=['Вид животного'],
        responses={200: SpeciesSerializer, 404: "Не найдено"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            species = self.get_object()
            serializer = self.get_serializer(species)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении вида")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создать новый вид животного",
        tags=['Вид животного'],
        request_body=SpeciesSerializer,
        responses={201: SpeciesSerializer, 400: "Некорректные данные"}
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании вида")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновить вид животного по ID",
        tags=['Вид животного'],
        request_body=SpeciesSerializer,
        responses={200: SpeciesSerializer, 404: "Не найдено"}
    )
    def update(self, request, *args, **kwargs):
        try:
            species = self.get_object()
            serializer = self.get_serializer(species, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении вида")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удалить вид животного по ID",
        tags=['Вид животного'],
        responses={204: "Удалено", 404: "Не найдено"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            species = self.get_object()
            species.delete()
            return Response({"message": "Вид успешно удалён"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении вида")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProductPurposeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = ProductPurpose.objects.all()
    serializer_class = ProductPurposeSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Список всех связей продуктов и назначений",
        tags=['Назначение товаров'],
        responses={
            200: openapi.Response(
                description="Список успешно получен",
                examples={
                    "application/json": [
                        {"id": 1, "product": 5, "purpose": 2},
                        {"id": 2, "product": 6, "purpose": 3}
                    ]
                }
            ),
            404: openapi.Response(
                description="Связи не найдены",
                examples={"application/json": {"detail": "Связи продуктов и назначений не найдены"}}
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            if not queryset.exists():
                return Response({"detail": "Связи продуктов и назначений не найдены"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении списка ProductPurpose")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Получение связи продукта и назначения по ID",
        tags=['Назначение товаров'],
        responses={
            200: ProductPurposeSerializer,
            404: openapi.Response(
                description="Связь не найдена",
                examples={"application/json": {"detail": "Связь не найдена"}}
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}
            ),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при получении ProductPurpose")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Создание новой связи продукта и назначения",
        tags=['Назначение товаров'],
        request_body=ProductPurposeSerializer,
        responses={
            201: openapi.Response(description="Связь успешно создана", schema=ProductPurposeSerializer),
            400: openapi.Response(description="Ошибка валидации", examples={"application/json": {"product": ["Обязательное поле."], "purpose": ["Обязательное поле."]}}),
            500: openapi.Response(description="Ошибка сервера", examples={"application/json": {"error": "Произошла внутренняя ошибка сервера"}}),
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Ошибка при создании ProductPurpose")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Обновление связи продукта и назначения",
        tags=['Назначение товаров'],
        request_body=ProductPurposeSerializer,
        responses={
            200: ProductPurposeSerializer,
            400: openapi.Response(description="Ошибка валидации"),
            404: openapi.Response(description="Связь не найдена"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Ошибка при обновлении ProductPurpose")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Удаление связи продукта и назначения",
        tags=['Назначение товаров'],
        responses={
            204: openapi.Response(description="Связь успешно удалена"),
            404: openapi.Response(description="Связь не найдена"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Связь успешно удалена"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Ошибка при удалении ProductPurpose")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProductStockViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = ProductStock.objects.all()
    serializer_class = ProductStockSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    @swagger_auto_schema(
        operation_summary="Получить список остатков товаров",
        tags=['Остатки товаров'],
        responses={
            200: openapi.Response(
                description="Список остатков успешно получен",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "product": 3,
                            "product_name": "Корм для кошек",
                            "pickup_point": "ул. Ленина, 10",
                            "quantity": 25
                        }
                    ]
                }
            ),
            500: openapi.Response(description="Ошибка сервера")
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            stocks = self.get_queryset()
            serializer = self.get_serializer(stocks, many=True)
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при получении остатков товаров")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Получить остаток товара по ID",
        tags=['Остатки товаров'],
        responses={
            200: ProductStockSerializer,
            404: openapi.Response(description="Остаток не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при получении остатка товара")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Создать новый остаток товара",
        tags=['Остатки товаров'],
        request_body=ProductStockSerializer,
        responses={
            201: ProductStockSerializer,
            400: openapi.Response(description="Ошибка валидации"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Ошибка при создании записи об остатке товара")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Обновить остаток товара",
        tags=['Остатки товаров'],
        request_body=ProductStockSerializer,
        responses={
            200: ProductStockSerializer,
            400: openapi.Response(description="Ошибка валидации"),
            404: openapi.Response(description="Остаток не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при обновлении записи об остатке товара")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Удалить запись об остатке товара",
        tags=['Остатки товаров'],
        responses={
            204: openapi.Response(description="Запись успешно удалена"),
            404: openapi.Response(description="Остаток не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"message": "Запись успешно удалена"}, status=status.HTTP_204_NO_CONTENT)
        except Exception:
            logger.exception("Ошибка при удалении записи об остатке товара")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Order.objects.all().order_by('-date_created')
    serializer_class = OrderSerializer
    http_method_names = ['get', 'put']

    @swagger_auto_schema(
        operation_summary="Получить список заказов",
        tags=['Управление заказами'],
        responses={
            200: openapi.Response(
                description="Список заказов успешно получен",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "order_number": "ORD-001",
                            "status": "В обработке",
                            "pickup_point": "ул. Ленина, 10",
                            "total_price": "1200.00"
                        }
                    ]
                }
            ),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            orders = self.get_queryset()
            serializer = self.get_serializer(orders, many=True)
            return Response(serializer.data)
        except Exception:
            logger.exception("Ошибка при получении списка заказов")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Получить заказ по ID",
        tags=['Управление заказами'],
        responses={
            200: OrderSerializer,
            404: openapi.Response(description="Заказ не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Заказ не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            logger.exception("Ошибка при получении заказа")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Изменить статус заказа",
        tags=['Управление заказами'],
        request_body=OrderStatusUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Статус успешно обновлён",
                examples={"application/json": {"message": "Статус заказа обновлён", "status": "В работе"}}
            ),
            400: openapi.Response(description="Ошибка валидации"),
            404: openapi.Response(description="Заказ не найден"),
            500: openapi.Response(description="Ошибка сервера"),
        }
    )

    def update(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            serializer = OrderStatusUpdateSerializer(order, data=request.data, context={'request': request})

            if serializer.is_valid():
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("ALTER TABLE petshop_auditlog DISABLE TRIGGER ALL")

                    serializer.save() 

                    with connection.cursor() as cursor:
                        cursor.execute("ALTER TABLE petshop_auditlog ENABLE TRIGGER ALL")

                return Response(
                    {"message": "Статус заказа обновлён", "status": serializer.data['status']},
                    status=status.HTTP_200_OK
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)

        except Exception:
            logger.exception("Ошибка при обновлении статуса заказа")
            return Response(
                {"error": "Произошла внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductSerializer

    @swagger_auto_schema(
        operation_summary="Список всех товаров",
        tags=['Товары'],
        responses={
            200: ProductSerializer(many=True),
            500: openapi.Response(description="Внутренняя ошибка сервера")
        }
    )
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset().filter(is_active=True)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при получении списка товаров")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Просмотр конкретного товара",
        tags=['Товары'],
        responses={200: ProductSerializer, 404: "Товар не найден"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при получении товара")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Создание нового товара",
        tags=['Товары'],
        request_body=ProductCreateUpdateSerializer,
        responses={201: ProductSerializer, 400: "Ошибка валидации"}
    )
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при создании товара")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Редактирование товара",
        tags=['Товары'],
        request_body=ProductCreateUpdateSerializer,
        responses={200: ProductSerializer, 400: "Ошибка валидации", 404: "Товар не найден"}
    )
    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при обновлении товара")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Частичное редактирование товара",
        tags=['Товары'],
        request_body=ProductCreateUpdateSerializer,
        responses={200: ProductSerializer, 400: "Ошибка валидации", 404: "Товар не найден"}
    )
    def partial_update(self, request, *args, **kwargs):
        try:
            return super().partial_update(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при частичном обновлении товара")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Удаление товара",
        tags=['Товары'],
        responses={204: "Товар успешно удалён", 404: "Товар не найден"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при удалении товара")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)
        
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUserRole]
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer

    @swagger_auto_schema(
        operation_summary="Список всех пользователей",
        tags=['Пользователи'],
        responses={200: UserSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Ошибка при получении списка пользователей")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Просмотр пользователя",
        tags=['Пользователи'],
        responses={200: UserSerializer, 404: "Пользователь не найден"}
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при получении пользователя")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Создание нового пользователя",
        tags=['Пользователи'],
        request_body=UserCreateUpdateSerializer,
        responses={201: UserSerializer, 400: "Ошибка валидации"}
    )
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при создании пользователя")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Редактирование пользователя",
        tags=['Пользователи'],
        request_body=UserCreateUpdateSerializer,
        responses={200: UserSerializer, 400: "Ошибка валидации", 404: "Пользователь не найден"}
    )
    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при обновлении пользователя")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)

    @swagger_auto_schema(
        operation_summary="Удаление пользователя",
        tags=['Пользователи'],
        responses={204: "Пользователь успешно удалён", 404: "Пользователь не найден"}
    )
    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception("Ошибка при удалении пользователя")
            return Response({"error": "Произошла внутренняя ошибка сервера"}, status=500)
        

class OrdersReportAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    @swagger_auto_schema(
        operation_summary="Получение отчета по заказам",
        tags=['Отчеты'],
        operation_description="Возвращает отчет по заказам в формате JSON или CSV в зависимости от параметра export",
        manual_parameters=[
            openapi.Parameter('type', openapi.IN_QUERY, description="Тип отчета", type=openapi.TYPE_STRING,
                              enum=['day', 'week', 'month', 'filtered'], default='day'),
            openapi.Parameter('date', openapi.IN_QUERY, description="Дата для фильтрации",
                              type=openapi.TYPE_STRING, format='date'),
            openapi.Parameter('product_id', openapi.IN_QUERY, description="ID товара для фильтрации",
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('category_id', openapi.IN_QUERY, description="ID категории для фильтрации",
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('brand_id', openapi.IN_QUERY, description="ID бренда для фильтрации",
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('user_id', openapi.IN_QUERY, description="ID пользователя для фильтрации",
                              type=openapi.TYPE_INTEGER),
            openapi.Parameter('export', openapi.IN_QUERY, description="Экспорт в CSV",
                              type=openapi.TYPE_STRING, enum=['csv']),
        ],
        responses={
            200: openapi.Response(
                description="Успешный ответ",
                examples={
                    "application/json": {
                        "data": [
                            {
                                "id": 1,
                                "user": "Иван Иванов",
                                "total_price": "1500.00",
                                "date_created": "10.10.2025 14:30"
                            }
                        ],
                        "total_count": 1,
                        "columns": {
                            "id": "ID заказа",
                            "user": "Пользователь",
                            "total_price": "Итоговая цена",
                            "date_created": "Дата создания"
                        },
                        "report_type": "day"
                    }
                }
            ),
            400: openapi.Response(description="Ошибка валидации"),
            401: openapi.Response(description="Не авторизован"),
            500: openapi.Response(description="Внутренняя ошибка сервера"),
        }
    )
    def get(self, request):
        try:
            user_format = getattr(getattr(request.user, 'profile', None), 'date_format', '%d.%m.%Y')
            python_format = user_format.replace('ГГГГ', '%Y').replace('ММ', '%m').replace('ДД', '%d')

            report_type = request.GET.get('type', 'day')
            date_str = request.GET.get('date')
            product_id = request.GET.get('product_id')
            category_id = request.GET.get('category_id')
            brand_id = request.GET.get('brand_id')
            user_id = request.GET.get('user_id')
            export = request.GET.get('export')

            if report_type not in ['day', 'week', 'month', 'filtered']:
                return Response(
                    {"detail": "Неверный тип отчета. Допустимые значения: day, week, month, filtered."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            orders = Order.objects.all().prefetch_related('items', 'items__product', 'user', 'pickup_point')

            if date_str:
                try:
                    target_date = datetime.strptime(date_str, python_format).date()

                    today = date.today()
                    if target_date > today:
                        return Response(
                            {"detail": f"Дата не может быть в будущем. Сегодня: {today.strftime(python_format)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    if report_type == 'day':
                        orders = orders.filter(date_created__date=target_date)
                    elif report_type == 'week':
                        start_date = target_date
                        end_date = target_date + timedelta(days=6)
                        orders = orders.filter(date_created__date__range=[start_date, end_date])
                    elif report_type == 'month':
                        orders = orders.filter(
                            date_created__year=target_date.year,
                            date_created__month=target_date.month
                        )

                except ValueError:
                    return Response(
                        {"detail": f"Некорректный формат даты. Используйте формат: {user_format}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )


            if user_id:
                orders = orders.filter(user_id=user_id)
            if product_id:
                orders = orders.filter(items__product_id=product_id)
            if category_id:
                orders = orders.filter(items__product__category_id=category_id)
            if brand_id:
                orders = orders.filter(items__product__brand_id=brand_id)

            if export == 'csv':
                return self.export_to_csv(orders, report_type, date_str, python_format, product_id, category_id, brand_id)

            return self.get_table_data(orders, report_type, python_format, product_id, category_id, brand_id)

        except Exception as e:
            print(f"Unexpected error: {e}")
            return Response(
                {"detail": f"Произошла непредвиденная ошибка: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_filtered_items(self, order_items, product_id=None, category_id=None, brand_id=None):
        filtered_items = order_items
        if product_id:
            filtered_items = filtered_items.filter(product_id=product_id)
        if category_id:
            filtered_items = filtered_items.filter(product__category_id=category_id)
        if brand_id:
            filtered_items = filtered_items.filter(product__brand_id=brand_id)
        return filtered_items

    def get_table_data(self, orders, report_type, python_format, product_id=None, category_id=None, brand_id=None):
        columns_config = self.get_columns_config(report_type)
        data = []

        for order in orders.distinct():
            filtered_items = self.get_filtered_items(order.items.all(), product_id, category_id, brand_id)
            if not filtered_items.exists():
                continue

            filtered_total = sum(item.quantity * item.price for item in filtered_items)

            data.append({
                'id': order.id,
                'user': f"{order.first_name} {order.last_name}",
                'total_price': f"{filtered_total:.2f}",
                'date_created': order.date_created.strftime(f"{python_format} %H:%M"),
            })

        return Response({
            'data': data,
            'total_count': len(data),
            'columns': columns_config,
            'report_type': report_type
        })

    def export_to_csv(self, orders, report_type, date_str, python_format, product_id=None, category_id=None, brand_id=None):
        response = HttpResponse(content_type='application/vnd.ms-excel; charset=utf-8')

        filename = f"orders_report_{report_type}"
        if date_str:
            filename += f"_{date_str}"
        filename += ".csv"

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff'.encode('utf-8'))

        writer = csv.writer(response, delimiter=';')
        columns_config = self.get_columns_config(report_type)
        writer.writerow(list(columns_config.values()))

        for order in orders.distinct():
            filtered_items = self.get_filtered_items(order.items.all(), product_id, category_id, brand_id)
            if not filtered_items.exists():
                continue

            filtered_total = sum(item.quantity * item.price for item in filtered_items)

            row = [
                order.id,
                f"{order.first_name} {order.last_name}",
                f"{filtered_total:.2f}",
                order.date_created.strftime(f"{python_format} %H:%M")
            ]
            writer.writerow(row)

        return response

    def get_columns_config(self, report_type):
        if report_type in ['day', 'week', 'month']:
            return {
                'id': 'ID заказа',
                'user': 'Пользователь',
                'total_price': 'Итоговая цена',
                'date_created': 'Дата создания',
            }
        elif report_type == 'filtered':
            return {
                'id': 'ID заказа',
                'user': 'Пользователь',
                'total_price': 'Сумма заказа',
                'date_created': 'Дата создания',
            }
        else:
            return {
                'id': 'ID заказа',
                'user': 'Пользователь',
                'total_price': 'Итоговая цена',
                'date_created': 'Дата создания',
            }
    def reports_view(request):
        user_format = getattr(getattr(request.user, 'profile', None), 'date_format', '%Y-%m-%d')
        return render(request, 'admin/reports.html', {
            'products': Product.objects.all(),
            'categories': Category.objects.all(),
            'brands': Brand.objects.all(),
            'users': User.objects.all(),
            'user_date_format': user_format,
        })


BACKUP_DIR = os.path.join(settings.MEDIA_ROOT, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)


BACKUP_DIR = os.path.join(settings.MEDIA_ROOT, 'backups')
if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class CreateBackupAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    @swagger_auto_schema(
        operation_summary="Создать резервную копию базы данных",
        tags=["Резервное копирование и восстановление"],
        responses={
            200: openapi.Response(
                description="Резервная копия успешно создана",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Файл backup_20251018_151030.zip успешно создан"
                    }
                }
            ),
            500: openapi.Response(
                description="Ошибка при создании резервной копии",
                examples={"application/json": {"success": False, "message": "Ошибка при создании резервной копии"}}
            ),
        }
    )
    def post(self, request):
        try:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f'backup_{timestamp}.zip'
            zip_filepath = os.path.join(BACKUP_DIR, zip_filename)

            backup_data = {
                'metadata': {'created_at': timezone.now().isoformat()},
                'tables': {}
            }

            tables_to_backup = [
                'petshop_role', 'petshop_user', 'petshop_userprofile',
                'petshop_category', 'petshop_brand', 'petshop_agecategory',
                'petshop_species', 'petshop_producttype', 'petshop_purpose',
                'petshop_product', 'petshop_productpurpose', 'petshop_pickuppoint',
                'petshop_productstock', 'petshop_cart', 'petshop_order',
                'petshop_orderitem', 'petshop_review', 'petshop_auditlog'
            ]

            with connection.cursor() as cursor:
                for table in tables_to_backup:
                    cursor.execute(f"SELECT * FROM {table}")
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    table_data = []

                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            if isinstance(value, (datetime, date)):
                                row_dict[col] = value.isoformat()
                            elif isinstance(value, Decimal):
                                row_dict[col] = float(value)
                            else:
                                row_dict[col] = value
                        table_data.append(row_dict)

                    backup_data['tables'][table] = {
                        'columns': columns,
                        'data': table_data,
                        'count': len(table_data)
                    }

            backup_data['metadata']['total_tables'] = len(backup_data['tables'])

            with tempfile.TemporaryDirectory() as temp_dir:
                json_path = os.path.join(temp_dir, f'backup_{timestamp}.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)

                sql_path = os.path.join(temp_dir, f'backup_{timestamp}.sql')
                with open(sql_path, 'w', encoding='utf-8') as f:
                    for table in tables_to_backup:
                        f.write(f"\n-- Table {table}\nDROP TABLE IF EXISTS {table} CASCADE;\n")
                        for row in backup_data['tables'][table]['data']:
                            values = []
                            for col in backup_data['tables'][table]['columns']:
                                val = row[col]
                                if val is None:
                                    values.append('NULL')
                                elif isinstance(val, str):
                                    values.append("'" + val.replace("'", "''") + "'")
                                elif isinstance(val, bool):
                                    values.append('TRUE' if val else 'FALSE')
                                elif isinstance(val, float):
                                    values.append(str(val))
                                else:
                                    values.append(str(val))
                            f.write(
                                f"INSERT INTO {table} ({', '.join(backup_data['tables'][table]['columns'])}) "
                                f"VALUES ({', '.join(values)});\n"
                            )

                with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(json_path, os.path.basename(json_path))
                    zf.write(sql_path, os.path.basename(sql_path))

            return FileResponse(
                open(zip_filepath, 'rb'),
                as_attachment=True,
                filename=zip_filename
            )

        except Exception as e:
            return Response(
                {'success': False, 'message': f'Ошибка при создании резервной копии: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RestoreBackupAPIView(APIView):
    permission_classes = [IsAdminUserRole]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Восстановление базы данных из резервной копии",
        tags=["Резервное копирование и восстановление"],
        operation_description=(
            "Загружает ZIP-архив резервной копии, извлекает JSON-файл с данными "
            "и полностью восстанавливает таблицы базы данных. "
            "⚠️ Внимание: все текущие данные в таблицах будут удалены и заменены!"
        ),
        request_body=RestoreBackupSerializer,
        responses={
            200: openapi.Response(
                description="Успешное восстановление",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "База данных успешно восстановлена"
                    }
                },
            ),
            400: openapi.Response(
                description="Ошибка запроса (например, не передан файл)",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Файл для восстановления не указан"
                    }
                },
            ),
            500: openapi.Response(
                description="Внутренняя ошибка при восстановлении",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Ошибка восстановления базы данных"
                    }
                },
            ),
        }
    )
    def post(self, request):
        file_name = request.data.get('filename')
        if file_name:
            filepath = os.path.join(BACKUP_DIR, file_name)
            if not os.path.exists(filepath):
                return Response({'success': False, 'message': 'Файл не найден на сервере'}, status=400)
        else:
            file = request.FILES.get('backup_file')
            if not file:
                return Response({'success': False, 'message': 'Файл для восстановления не выбран'}, status=400)

            filepath = os.path.join(BACKUP_DIR, file.name)
            with open(filepath, 'wb+') as dest:
                for chunk in file.chunks():
                    dest.write(chunk)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    zf.extractall(temp_dir)

                json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
                if not json_files:
                    return Response(
                        {'success': False, 'message': 'JSON файл с данными не найден в архиве'},
                        status=400
                    )

                json_path = os.path.join(temp_dir, json_files[0])
                with open(json_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

                with connection.cursor() as cursor:
                    cursor.execute("SET session_replication_role = 'replica';")
                    for table, info in backup_data['tables'].items():
                        cursor.execute(f'DELETE FROM {table};')
                        columns = info['columns']
                        for row in info['data']:
                            placeholders = ', '.join(['%s'] * len(columns))
                            values = [row[col] for col in columns]
                            cursor.execute(
                                f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})',
                                values
                            )
                    cursor.execute("SET session_replication_role = 'origin';")

            return Response({'success': True, 'message': 'База данных успешно восстановлена'})

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=500)

class ListBackupsAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    @swagger_auto_schema(
        operation_summary="Получение списка резервных копий",
        tags=["Резервное копирование и восстановление"],
        operation_description=(
            "Возвращает список всех резервных копий, сохранённых в директории BACKUP_DIR. "
            "Для каждой копии указывается имя файла, размер в байтах и дата создания. "
            "Список отсортирован по дате создания в порядке убывания."
        ),
        responses={
            200: openapi.Response(
                description="Список резервных копий успешно получен",
                examples={
                    "application/json": {
                        "success": True,
                        "backups": [
                            {
                                "name": "backup_20251018_153000.zip",
                                "size": 24821,
                                "created": 1734567890.123
                            },
                            {
                                "name": "backup_20251017_120045.zip",
                                "size": 23014,
                                "created": 1734481645.331
                            }
                        ]
                    }
                },
            ),
            500: openapi.Response(
                description="Ошибка при получении списка резервных копий",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Ошибка чтения каталога резервных копий"
                    }
                },
            ),
        }
    )
    def get(self, request):
        try:
            backups = []
            for fname in os.listdir(BACKUP_DIR):
                fpath = os.path.join(BACKUP_DIR, fname)
                if os.path.isfile(fpath):
                    backups.append({
                        'name': fname,
                        'size': os.path.getsize(fpath),
                        'created': os.path.getctime(fpath)
                    })
            backups.sort(key=lambda x: x['created'], reverse=True)
            return Response({'success': True, 'backups': backups})
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChartsDataAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    @swagger_auto_schema(
        operation_summary="Получение статистических данных для графиков",
        operation_description=(
            "Возвращает агрегированные данные о продажах по категориям и по месяцам. "
            "**category_data** — общие продажи по категориям.\n"
            "**month_data** — общие продажи по месяцам."
        ),
        tags=["Графики"],
        responses={
            200: openapi.Response(
                description="Статистические данные успешно получены",
                examples={
                    "application/json": {
                        "success": True,
                        "category_data": [
                            {"category": "Корм", "total_sales": 12500.50},
                            {"category": "Игрушки", "total_sales": 8200.00}
                        ],
                        "month_data": [
                            {"month": "2025-08", "total_sales": 9300.00},
                            {"month": "2025-09", "total_sales": 11200.75}
                        ]
                    }
                }
            ),
            500: openapi.Response(
                description="Ошибка при получении данных для графиков",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Ошибка соединения с базой данных"
                    }
                }
            ),
        }
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_sales_by_category()")
                category_rows = cursor.fetchall()

            category_data = [
                {'category': row[0], 'total_sales': float(row[1])}
                for row in category_rows
            ]

            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_sales_by_month()")
                month_rows = cursor.fetchall()

            month_data = []
            for row in month_rows:
                month_date = row[0]
                if isinstance(month_date, str):
                    formatted_month = month_date[:7] 
                else:
                    formatted_month = month_date.strftime('%Y-%m')

                month_data.append({
                    'month': formatted_month,
                    'total_sales': float(row[1])
                })

            return Response({
                'success': True,
                'category_data': category_data,
                'month_data': month_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SummaryTablesAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    @swagger_auto_schema(
        operation_summary="Получение сводных таблиц по продажам",
        tags=["Сводные таблицы"],
        operation_description=(
            "Возвращает данные для таблиц по категориям, месяцам или брендам.\n\n"
            "Параметр запроса `type` может принимать значения:\n"
            "- `categories` — продажи по категориям,\n"
            "- `months` — продажи по месяцам,\n"
            "- `brands` — продажи по брендам."
        ),
        manual_parameters=[
            openapi.Parameter(
                'type', openapi.IN_QUERY, description="Тип сводной таблицы", type=openapi.TYPE_STRING, required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Сводная таблица успешно получена",
                examples={
                    "application/json": {
                        "success": True,
                        "title": "Продажи по категориям",
                        "fields": ["category_name", "total_orders", "total_sales", "avg_order_value"],
                        "column_names": {
                            "category_name": "Категория",
                            "total_orders": "Количество заказов",
                            "total_sales": "Общая сумма продаж",
                            "avg_order_value": "Средний чек"
                        },
                        "data": [
                            {"category_name": "Корм", "total_orders": 12, "total_sales": 12500.5, "avg_order_value": 1041.7},
                            {"category_name": "Игрушки", "total_orders": 8, "total_sales": 8200.0, "avg_order_value": 1025.0}
                        ]
                    }
                }
            ),
            400: openapi.Response(
                description="Некорректный тип таблицы",
                examples={"application/json": {"success": False, "error": "Unknown table type"}}
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={"application/json": {"success": False, "error": "Ошибка соединения с базой данных"}}
            ),
        }
    )
    def get(self, request):
        try:
            table_type = request.GET.get('type', 'categories')
            if table_type == 'categories':
                return self.get_categories_summary()
            elif table_type == 'months':
                return self.get_months_summary()
            elif table_type == 'brands':
                return self.get_brands_summary()
            else:
                return Response(
                    {'success': False, 'error': 'Unknown table type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_categories_summary(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT category_name, total_orders, total_sales, avg_order_value FROM petshop_orders_by_category")
            rows = cursor.fetchall()

        data = [
            {
                'category_name': row[0],
                'total_orders': row[1],
                'total_sales': float(row[2]) if row[2] else 0,
                'avg_order_value': float(row[3]) if row[3] else 0
            }
            for row in rows
        ]

        return Response({
            'success': True,
            'title': 'Продажи по категориям',
            'fields': ['category_name', 'total_orders', 'total_sales', 'avg_order_value'],
            'column_names': {
                'category_name': 'Категория',
                'total_orders': 'Количество заказов',
                'total_sales': 'Общая сумма продаж',
                'avg_order_value': 'Средний чек'
            },
            'data': data
        })

    def get_months_summary(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT month, total_orders, total_sales, avg_order_value FROM petshop_orders_by_month")
            rows = cursor.fetchall()

        data = []
        for row in rows:
            month_date = row[0]
            formatted_month = month_date[:7] if isinstance(month_date, str) else month_date.strftime('%Y-%m')
            data.append({
                'month': formatted_month,
                'total_orders': row[1],
                'total_sales': float(row[2]) if row[2] else 0,
                'avg_order_value': float(row[3]) if row[3] else 0
            })

        return Response({
            'success': True,
            'title': 'Продажи по месяцам',
            'fields': ['month', 'total_orders', 'total_sales', 'avg_order_value'],
            'column_names': {
                'month': 'Месяц',
                'total_orders': 'Количество заказов',
                'total_sales': 'Общая сумма продаж',
                'avg_order_value': 'Средний чек'
            },
            'data': data
        })

    def get_brands_summary(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT brand_name, total_orders, total_sales, avg_order_value FROM petshop_orders_by_brand")
            rows = cursor.fetchall()

        data = [
            {
                'brand_name': row[0] if row[0] else 'Без бренда',
                'total_orders': row[1],
                'total_sales': float(row[2]) if row[2] else 0,
                'avg_order_value': float(row[3]) if row[3] else 0
            }
            for row in rows
        ]

        return Response({
            'success': True,
            'title': 'Продажи по брендам',
            'fields': ['brand_name', 'total_orders', 'total_sales', 'avg_order_value'],
            'column_names': {
                'brand_name': 'Бренд',
                'total_orders': 'Количество заказов',
                'total_sales': 'Общая сумма продаж',
                'avg_order_value': 'Средний чек'
            },
            'data': data
        })



class UsersImportAPIView(APIView):
    permission_classes = [IsAdminUserRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('users_file')
        if not file:
            return Response({'success': False, 'message': 'Файл не предоставлен'}, status=400)

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE petshop_auditlog DISABLE TRIGGER ALL")

                if file.name.endswith('.csv'):
                    try:
                        content = file.read().decode('utf-8')
                    except UnicodeDecodeError:
                        file.seek(0)
                        content = file.read().decode('cp1251')

                    f = StringIO(content)
                    reader = csv.DictReader(f)

                    for row in reader:
                        email = row.get('Email') or row.get('email')
                        if not email:
                            continue

                        role_name = row.get('Роль') or row.get('role')
                        role = Role.objects.filter(name=role_name).first()
                        if not role:
                            role, _ = Role.objects.get_or_create(name='Пользователь')

                        user, _ = User.objects.update_or_create(
                            email=email,
                            defaults={
                                'first_name': row.get('Имя') or row.get('first_name', ''),
                                'last_name': row.get('Фамилия') or row.get('last_name', ''),
                                'middle_name': row.get('Отчество') or row.get('middle_name', ''),
                                'phone': row.get('Телефон') or row.get('phone', ''),
                                'role': role,
                                'is_active': str(row.get('Активен', 'True')).lower() in ['true', '1', 'yes'],
                                'is_staff': str(row.get('Сотрудник', 'False')).lower() in ['true', '1', 'yes'],
                                'is_superuser': str(row.get('Суперпользователь', 'False')).lower() in ['true', '1', 'yes']
                            }
                        )

                        dob_str = row.get('Дата рождения') or row.get('date_of_birth')
                        dob = None
                        if dob_str:
                            for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
                                try:
                                    dob = datetime.strptime(dob_str, fmt).date()
                                    break
                                except ValueError:
                                    continue

                        if user:
                            UserProfile.objects.update_or_create(user=user, defaults={'date_of_birth': dob})

                elif file.name.endswith('.json'):
                    data = json.load(file)
                    for row in data:
                        email = row.get('email')
                        if not email:
                            continue

                        role_name = row.get('role')
                        role = Role.objects.filter(name=role_name).first()
                        if not role:
                            role, _ = Role.objects.get_or_create(name='Пользователь')

                        user, _ = User.objects.update_or_create(
                            email=email,
                            defaults={
                                'first_name': row.get('first_name', ''),
                                'last_name': row.get('last_name', ''),
                                'middle_name': row.get('middle_name', ''),
                                'phone': row.get('phone', ''),
                                'role': role,
                                'is_active': row.get('is_active', True),
                                'is_staff': row.get('is_staff', False),
                                'is_superuser': row.get('is_superuser', False)
                            }
                        )

                        dob_str = row.get('date_of_birth')
                        dob = None
                        if dob_str:
                            try:
                                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                            except ValueError:
                                dob = None

                        if user:
                            UserProfile.objects.update_or_create(user=user, defaults={'date_of_birth': dob})

                else:
                    return Response({'success': False, 'message': 'Поддерживаются только CSV и JSON'}, status=400)

                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE petshop_auditlog ENABLE TRIGGER ALL")

            return Response({'success': True, 'message': 'Пользователи успешно импортированы'})

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=500)


class UsersExportAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request, *args, **kwargs):
        try:
            format_type = request.GET.get('format', 'json').lower()
            print(f"Export requested for format: {format_type}") 
            
            if format_type != 'json':
                return JsonResponse(
                    {
                        'success': False, 
                        'message': 'Поддерживается только формат JSON'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            users_qs = User.objects.all().select_related('profile', 'role').order_by('id')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            try:
                data = []
                for user in users_qs:
                    role_name = user.role.name if user.role else ''
                    dob = user.profile.date_of_birth if hasattr(user, 'profile') and user.profile else None
                    dob_str = dob.strftime("%Y-%m-%d") if dob else ''

                    data.append({
                        'id': user.id,
                        'email': user.email or '',
                        'last_name': user.last_name or '',
                        'first_name': user.first_name or '',
                        'middle_name': user.middle_name or '',
                        'phone': user.phone or '',
                        'role': role_name,
                        'date_joined': user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
                        'date_of_birth': dob_str,
                        'is_active': user.is_active,
                        'is_staff': user.is_staff,
                        'is_superuser': user.is_superuser
                    })

                response = JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
                response['Content-Disposition'] = f'attachment; filename="users_export_{timestamp}.json"'
                print("JSON export completed successfully") 
                return response

            except Exception as json_error:
                print(f"JSON export error: {str(json_error)}") 
                return JsonResponse(
                    {
                        'success': False, 
                        'message': f'Ошибка при создании JSON: {str(json_error)}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            print(f"General export error: {str(e)}") 
            return JsonResponse(
                {
                    'success': False, 
                    'message': f'Ошибка при экспорте: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )