from django.contrib import admin
from .models import UploadedImage, NumberRegion

@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_image', 'uploaded_at', 'processed', 'total_regions_found')
    list_filter = ('processed', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

@admin.register(NumberRegion)
class NumberRegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'parent_image', 'region_index', 'bbox_x', 'bbox_y', 'confidence_score', 'extracted_at')
    list_filter = ('extracted_at', 'confidence_score')
    readonly_fields = ('extracted_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent_image')