from django.urls import path
from . import views

urlpatterns = [
    # Dashboards
    path('allocation/student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('allocation/guide/dashboard/', views.guide_dashboard, name='guide_dashboard'),

    # Guide profile
    path('allocation/guide/complete-profile/', views.guide_complete_profile, name='guide_complete_profile'),
    path('allocation/guide/edit-profile/', views.guide_edit_profile, name='guide_edit_profile'),

    # Group management
    path('allocation/group/create/', views.create_group_view, name='create_group'),
    path('allocation/group/<uuid:group_id>/', views.manage_group, name='manage_group'),
    path('allocation/group/<uuid:group_id>/add-member/', views.add_member, name='add_member'),
    path('allocation/group/<uuid:group_id>/remove/<uuid:student_id>/', views.remove_member, name='remove_member'),
    path('allocation/group/<uuid:group_id>/submit/', views.submit_group, name='submit_group'),
    path('allocation/group/<uuid:group_id>/accept/', views.accept_group, name='accept_group'),
    path('allocation/group/<uuid:group_id>/reject/', views.reject_group, name='reject_group'),

    # File uploads
    path('allocation/group/<uuid:group_id>/upload/', views.upload_submission, name='upload_submission'),

    # To-do
    path('allocation/group/<uuid:group_id>/todo/add/', views.add_todo_view, name='add_todo'),
    path('allocation/group/<uuid:group_id>/todo/<uuid:todo_id>/edit/', views.edit_todo_view, name='edit_todo'),
    path('allocation/group/<uuid:group_id>/todo/<uuid:todo_id>/delete/', views.delete_todo_view, name='delete_todo'),
    path('allocation/group/<uuid:group_id>/todo/<uuid:todo_id>/toggle/', views.toggle_todo_view, name='toggle_todo'),

    path('allocation/about/', views.about, name='about'),
]
