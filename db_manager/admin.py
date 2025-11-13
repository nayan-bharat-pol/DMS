from django.contrib import admin
from .models import DatabaseConnection, MonitoringConfig, QueryLog, DatabaseStats

@admin.register(DatabaseConnection)
class DatabaseConnectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'db_type', 'host', 'port', 'database_name', 'is_active', 'created_at']
    list_filter = ['db_type', 'is_active', 'created_at']
    search_fields = ['name', 'host', 'database_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'db_type', 'is_active')
        }),
        ('Connection Details', {
            'fields': ('host', 'port', 'database_name', 'username', 'password')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MonitoringConfig)
class MonitoringConfigAdmin(admin.ModelAdmin):
    list_display = ['database_connection', 'monitoring_interval', 'alert_threshold', 'is_monitoring_active', 'created_at']
    list_filter = ['is_monitoring_active', 'created_at']
    search_fields = ['database_connection__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['database_connection', 'status', 'execution_time', 'result_count', 'executed_at']
    list_filter = ['status', 'database_connection', 'executed_at']
    search_fields = ['query', 'error_message']
    readonly_fields = ['executed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('database_connection')

@admin.register(DatabaseStats)
class DatabaseStatsAdmin(admin.ModelAdmin):
    list_display = ['database_connection', 'total_queries', 'successful_queries', 'failed_queries', 'average_response_time', 'timestamp']
    list_filter = ['database_connection', 'timestamp']
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('database_connection')