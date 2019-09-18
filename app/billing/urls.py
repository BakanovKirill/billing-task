"""URL Configuration"""
from __future__ import print_function
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path

# Custom admin header
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from billing.views import index, TopUpWalletView, ExchangeRateList, SignupView

admin.site.site_header = "Billing Administration"
schema_view = get_schema_view(
    openapi.Info(
        title="Billing API",
        default_version="v1",
        description="Billing test project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="kirill.bakanov@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/auth/", include("rest_framework.urls")),
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    path("api/signup/", SignupView.as_view(), name="signup"),
    path("api/login/", TokenObtainPairView.as_view(), name="login"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/wallets/top-up/", TopUpWalletView.as_view(), name="top-up-wallet"),
    path("api/exchange-rates/", ExchangeRateList.as_view(), name="exchange-rates"),
]

# Host the static from uWSGI
if settings.IS_WSGI:
    print("uWSGI mode, adding static file patterns")
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()

# Add debug toolbar
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
