from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
from .forms import ImageUploadForm
from .models import UploadedImage, NumberRegion
from .utils import extract_number_regions_from_image, NumberRegionExtractor
import cv2

class ImageUploadView(View):
    def get(self, request):
        form = ImageUploadForm()
        recent_images = UploadedImage.objects.filter(processed=True).order_by('-uploaded_at')[:5]
        return render(request, 'extractor/upload.html', {
            'form': form,
            'recent_images': recent_images
        })
    
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            uploaded_image = form.save()
            
            try:
                # Process the image
                self.process_uploaded_image(uploaded_image)
                messages.success(request, f'Image processed successfully! Found {uploaded_image.total_regions_found} number regions.')
                return redirect('results', image_id=uploaded_image.id)
                
            except Exception as e:
                messages.error(request, f'Error processing image: {str(e)}')
                print(f"Full error details: {e}")
                import traceback
                traceback.print_exc()
                # Don't delete on error - keep for debugging
                uploaded_image.processed = False
                uploaded_image.save()
        
        else:
            messages.error(request, 'Please upload a valid image file.')
        
        recent_images = UploadedImage.objects.filter(processed=True).order_by('-uploaded_at')[:5]
        return render(request, 'extractor/upload.html', {
            'form': form,
            'recent_images': recent_images
        })
    
    def process_uploaded_image(self, uploaded_image):
        """Process uploaded image to extract number regions"""
        image_path = uploaded_image.original_image.path
        
        # Extract number regions
        cropped_regions = extract_number_regions_from_image(image_path)
        
        # Save each cropped region to database
        extractor = NumberRegionExtractor()
        regions_saved = 0
        
        for region_data in cropped_regions:
            try:
                # Generate filename
                filename = f"region_{uploaded_image.id}_{region_data['index']}.png"
                
                # Save cropped image
                django_file = extractor.save_cropped_image(region_data['image'], filename)
                
                # Create NumberRegion instance
                number_region = NumberRegion(
                    parent_image=uploaded_image,
                    region_index=region_data['index'],
                    bbox_x=region_data['bbox']['x'],
                    bbox_y=region_data['bbox']['y'],
                    bbox_width=region_data['bbox']['width'],
                    bbox_height=region_data['bbox']['height'],
                    confidence_score=region_data['confidence']
                )
                
                # Save the cropped image file
                number_region.cropped_image.save(filename, django_file, save=False)
                number_region.save()
                
                regions_saved += 1
                
            except Exception as e:
                print(f"Error saving region {region_data['index']}: {e}")
                continue
        
        # Update parent image
        uploaded_image.total_regions_found = regions_saved
        uploaded_image.processed = True
        uploaded_image.save()

class ResultsView(View):
    def get(self, request, image_id):
        uploaded_image = get_object_or_404(UploadedImage, id=image_id)
        number_regions = uploaded_image.number_regions.all()
        
        return render(request, 'extractor/results.html', {
            'uploaded_image': uploaded_image,
            'number_regions': number_regions
        })

class DebugView(View):
    """Debug view to see what the system is detecting"""
    def get(self, request, image_id):
        uploaded_image = get_object_or_404(UploadedImage, id=image_id)
        
        # Create debug visualization
        try:
            debug_info = self.create_debug_visualization(uploaded_image.original_image.path)
            return render(request, 'extractor/debug.html', {
                'uploaded_image': uploaded_image,
                'debug_info': debug_info
            })
        except Exception as e:
            messages.error(request, f'Error creating debug visualization: {str(e)}')
            return redirect('results', image_id=image_id)
    
    def create_debug_visualization(self, image_path):
        """Create debug information showing detection process"""
        from .utils import NumberRegionExtractor
        
        extractor = NumberRegionExtractor()
        image = cv2.imread(image_path)
        
        # Get all preprocessing results
        processed_images = extractor.preprocess_image(image)
        
        debug_info = {
            'original_shape': image.shape,
            'preprocessing_count': len(processed_images),
            'ocr_configs_count': len(extractor.ocr_configs)
        }
        
        return debug_info

class AllResultsView(View):
    def get(self, request):
        uploaded_images = UploadedImage.objects.filter(processed=True).order_by('-uploaded_at')
        return render(request, 'extractor/all_results.html', {
            'uploaded_images': uploaded_images
        })
    


# <--------------------------update---------------------------->

# from django.shortcuts import redirect, get_object_or_404
# from django.urls import reverse
# from .models import UploadedImage

# def delete_uploaded_image(request, pk):
#     image = get_object_or_404(UploadedImage, pk=pk)
    
#     # Delete the related number regions (cascades automatically because of FK)
#     # Delete the actual image files too
#     image.original_image.delete(save=False)
#     for region in image.number_regions.all():
#         region.cropped_image.delete(save=False)
    
#     image.delete()
#     return redirect(reverse('upload'))  # Change 'home' to your recent extractions view name
    

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from .models import UploadedImage

def delete_uploaded_image(request, pk):
    try:
        image = UploadedImage.objects.get(pk=pk)
    except UploadedImage.DoesNotExist:
        messages.error(request, "This extraction was already deleted or does not exist.")
        return redirect('all_results')   # go back to results list safely

    # Delete the actual image files
    if image.original_image:
        image.original_image.delete(save=False)
    for region in image.number_regions.all():
        if region.cropped_image:
            region.cropped_image.delete(save=False)

    # Delete DB entry
    image.delete()

    # messages.success(request, "Extraction deleted successfully.")
    # return redirect('all_results')   # redirect to your "Recent Extractions" or All Results page