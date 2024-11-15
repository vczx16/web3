from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic import RedirectView

# Swagger 文档配置
# Swagger 文档配置（只保留一个配置）
schema_view = get_schema_view(
    openapi.Info(
        title="AI Card Generator API",
        default_version='v1',
        description="API documentation for AI Card Generator",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # 重定向根URL到swagger
    path('', RedirectView.as_view(url='/swagger/', permanent=False)),
    
    # 主要URLs
    path('admin/', admin.site.urls),
    path('api/', include('ai_card_generator.urls')),
    
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 开发环境下的媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 添加重定向
from django.views.generic import RedirectView
urlpatterns = [
    path('', RedirectView.as_view(url='/swagger/', permanent=False)),
] + urlpatterns
# API 文档配置
schema_view = get_schema_view(
   openapi.Info(
      title="AI Card Generator API",
      default_version='v1',
      description="API for generating AI cards and NFTs",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)


# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, 
                         document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, 
                         document_root=settings.STATIC_ROOT)