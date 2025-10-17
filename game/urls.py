from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_or_join_room, name='create_or_join_room'),
    path('game/<uuid:room_code>/', views.game_room, name='game_room'),
]
