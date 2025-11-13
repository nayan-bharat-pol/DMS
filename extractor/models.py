# from django.db import models
# from django.utils import timezone

# class UploadedImage(models.Model):
#     original_image = models.ImageField(upload_to='uploads/')
#     uploaded_at = models.DateTimeField(default=timezone.now)
#     processed = models.BooleanField(default=False)
#     total_regions_found = models.IntegerField(default=0)
    
#     def __str__(self):
#         return f"Image {self.id} - {self.original_image.name}"

# class NumberRegion(models.Model):
#     parent_image = models.ForeignKey(UploadedImage, on_delete=models.CASCADE, related_name='number_regions')
#     cropped_image = models.ImageField(upload_to='number_regions/')
#     region_index = models.IntegerField()  # Order of detection
#     bbox_x = models.IntegerField()  # Bounding box coordinates
#     bbox_y = models.IntegerField()
#     bbox_width = models.IntegerField()
#     bbox_height = models.IntegerField()
#     confidence_score = models.FloatField()
#     extracted_at = models.DateTimeField(default=timezone.now)
    
#     def __str__(self):
#         return f"Number Region {self.region_index} from Image {self.parent_image.id}"

#     class Meta:
#         ordering = ['parent_image', 'region_index']


# <---------------------------update---------------------->
# models.py
from django.db import models
from django.utils import timezone

class UploadedImage(models.Model):
    original_image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    total_regions_found = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Image {self.id} - {self.original_image.name}"

    def delete(self, *args, **kwargs):
        # Delete the main uploaded file
        if self.original_image:
            self.original_image.delete(save=False)
        # Delete related regions (and their files)
        for region in self.number_regions.all():
            if region.cropped_image:
                region.cropped_image.delete(save=False)
        super().delete(*args, **kwargs)


class NumberRegion(models.Model):
    parent_image = models.ForeignKey(
        UploadedImage, on_delete=models.CASCADE, related_name='number_regions'
    )
    cropped_image = models.ImageField(upload_to='number_regions/')
    region_index = models.IntegerField()
    bbox_x = models.IntegerField()
    bbox_y = models.IntegerField()
    bbox_width = models.IntegerField()
    bbox_height = models.IntegerField()
    confidence_score = models.FloatField()
    extracted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Number Region {self.region_index} from Image {self.parent_image.id}"

    class Meta:
        ordering = ['parent_image', 'region_index']

    def delete(self, *args, **kwargs):
        if self.cropped_image:
            self.cropped_image.delete(save=False)
        super().delete(*args, **kwargs)
