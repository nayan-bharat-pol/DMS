# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Document, ChatMessage

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_type', 'size', 'status', 'uploaded_at', 'user']
    list_filter = ['file_type', 'status', 'uploaded_at']
    search_fields = ['name', 'content']
    readonly_fields = ['uploaded_at', 'size', 'content']
    list_editable = ['status']
    
    fieldsets = (
        ('Document Info', {
            'fields': ('name', 'file', 'file_type', 'size', 'status', 'user')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['document', 'role', 'content_preview', 'timestamp', 'session_id']
    list_filter = ['role', 'timestamp', 'document__file_type']
    search_fields = ['content', 'document__name']
    readonly_fields = ['timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content Preview"