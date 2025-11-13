from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
import json

class DatabaseConnection(models.Model):
    """Model to store database connection details"""
    
    DB_TYPES = [
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('oracle', 'Oracle'),
        ('sqlite', 'SQLite'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    db_type = models.CharField(max_length=20, choices=DB_TYPES)
    host = models.CharField(max_length=255)
    port = models.IntegerField()
    database_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)  # Consider encryption in production
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Database Connection"
        verbose_name_plural = "Database Connections"
    
    def __str__(self):
        return f"{self.name} ({self.db_type})"

class MonitoringConfig(models.Model):
    """Configuration for database monitoring"""
    
    database_connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    query_timeout = models.IntegerField(default=8, help_text="Query timeout in seconds")
    monitoring_interval = models.IntegerField(default=300, help_text="Monitoring interval in seconds")
    email_recipients = models.TextField(help_text="Comma-separated email addresses")
    alert_threshold = models.IntegerField(default=1000, help_text="Alert when query count exceeds this")
    is_monitoring_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Monitoring Configuration"
        verbose_name_plural = "Monitoring Configurations"
    
    def __str__(self):
        return f"Monitoring for {self.database_connection.name}"
    
    def get_email_list(self):
        """Return list of email addresses"""
        return [email.strip() for email in self.email_recipients.split(',') if email.strip()]

class QueryLog(models.Model):
    """Log of database queries and their results"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]
    
    database_connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    query = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    execution_time = models.FloatField(help_text="Execution time in seconds")
    result_count = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Query Log"
        verbose_name_plural = "Query Logs"
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.database_connection.name} - {self.status} - {self.executed_at}"

class DatabaseStats(models.Model):
    """Store database statistics over time"""
    
    database_connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    total_queries = models.IntegerField(default=0)
    successful_queries = models.IntegerField(default=0)
    failed_queries = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Database Statistics"
        verbose_name_plural = "Database Statistics"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.database_connection.name} Stats - {self.timestamp}"
    

