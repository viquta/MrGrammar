from django.urls import path

from . import views

urlpatterns = [
    path('', views.ClassroomListCreateView.as_view(), name='classroom-list'),
    path('<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom-detail'),
    path('<int:classroom_id>/members/', views.ClassroomMembersView.as_view(), name='classroom-members'),
    path('<int:classroom_id>/members/add/', views.AddMemberView.as_view(), name='classroom-add-member'),
]
