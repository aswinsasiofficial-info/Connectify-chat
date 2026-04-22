from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('chat/<str:username>/', views.chat_room, name='chat_room'),
    path('media-section/', views.media_view, name='media_section'),
    path('status/', views.status_list, name='status_list'),
    path('status/create/', views.create_status, name='create_status'),
    path('status/view/<str:username>/', views.view_status, name='view_status'),
]
