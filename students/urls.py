from django.urls import path
from . import views

urlpatterns = [
    path('students/register/', views.student_register, name='student_register'),
]
