from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/student/login/', views.student_login, name='student_login'),
    path('accounts/guide/login/', views.guide_login, name='guide_login'),
    path('accounts/logout/', views.user_logout, name='logout'),
    path('accounts/dashboard/', views.dashboard_router, name='dashboard'),
    path('accounts/guide/change-password/', views.guide_change_password, name='guide_change_password'),
    path('accounts/student/change-password/', views.student_change_password, name='student_change_password'),
]
