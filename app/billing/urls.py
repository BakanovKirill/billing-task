"""URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
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

from billing.views import index

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
    path("admin/", admin.site.urls),
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
    path("", index),
    url(r"^api/token/$", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    url(r"^api/token/refresh/$", TokenRefreshView.as_view(), name="token_refresh"),
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
