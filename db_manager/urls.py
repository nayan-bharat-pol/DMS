from django.urls import path
from . import views

app_name = 'db_manager'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
     path("test-task/", views.test_task, name="test_task"),
     path('logs/<int:log_id>/delete/', views.delete_query_log, name='delete_query_log'),

    
    # Database Connections
    path('connections/', views.connection_list, name='connection_list'),
    path('connections/add/', views.add_connection, name='add_connection'),
    path('connections/<int:connection_id>/edit/', views.edit_connection, name='edit_connection'),
    path('connections/<int:connection_id>/test/', views.test_connection_view, name='test_connection'), #for test button
    
    # Query Interface
    path('connections/<int:connection_id>/query/', views.query_interface, name='query_interface'),
    
    # Monitoring
    path('connections/<int:connection_id>/monitoring/', views.monitoring_config, name='monitoring_config'),
    path('connections/<int:connection_id>/stats/', views.database_stats_view, name='database_stats'),
    
    # Logs
    path('logs/', views.query_logs, name='query_logs'),
    path('connections/<int:connection_id>/logs/', views.query_logs, name='connection_logs'),
    
    # API Endpoints
    path('api/execute-query/', views.api_execute_query, name='api_execute_query'),
    path('api/connections/<int:connection_id>/stats/', views.api_connection_stats, name='api_connection_stats'),
]