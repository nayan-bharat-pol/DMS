# from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
import os

class Document(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('txt', 'Text File'),
        ('xlsx', 'Excel File'),
        ('xls', 'Excel File (Old Format)'),
    ]
    
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    size = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    content = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.name
    
    def get_file_size_display(self):
        size = self.file.size
        if size > 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / 1024:.1f} KB"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."