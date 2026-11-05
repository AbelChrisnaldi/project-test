from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('import/', views.import_excel, name='import_excel'),
    path('import/load-default/', views.load_default_sample, name='load_default_sample'),
    path('import/template/', views.download_template, name='download_template'),
    path('students/', views.student_list, name='student_list'),
    path('students/edit/<int:student_id>/', views.student_edit, name='student_edit'),
    path('students/delete/<int:student_id>/', views.student_delete, name='student_delete'),
    path('students/clear/<int:student_id>/', views.student_clear_slot, name='student_clear_slot'),
    path('students/toggle-lock/<int:student_id>/', views.student_toggle_lock, name='student_toggle_lock'),
    path('settings/', views.settings_view, name='settings'),
    path('genetic/', views.genetic_view, name='genetic'),
    path('api/run-ga/', views.api_run_ga, name='api_run_ga'),
    path('manual/', views.manual_grid, name='manual_grid'),
    path('api/assign-slot/', views.api_assign_slot, name='api_assign_slot'),
    path('api/clear-slot/', views.api_clear_slot, name='api_clear_slot'),
    path('api/batch-action/', views.api_batch_action, name='api_batch_action'),
    path('export/', views.export_view, name='export_view'),
    path('export/download/', views.export_download, name='export_download'),
]
