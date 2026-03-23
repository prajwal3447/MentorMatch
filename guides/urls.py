from django.urls import path
from . import views

urlpatterns = [
    path('guide/profile/complete/', views.complete_profile, name='guide_complete_profile'),
    path('guide/profile/edit/', views.edit_profile, name='guide_edit_profile'),
]
