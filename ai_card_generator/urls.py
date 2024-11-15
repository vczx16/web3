from django.urls import path
from .views import CardGeneratorView, CardListView  # 修改这里，使用正确的视图名称

app_name = 'ai_card_generator'

urlpatterns = [
    path('cards/generate/', 
         CardGeneratorView.as_view(),  # 修改这里
         name='generate_card'),
    path('cards/list/', 
         CardListView.as_view(), 
         name='card_list'),
]