import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import os
import io
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

class NumberRegionExtractor:
    def __init__(self):
        # Multiple OCR configurations for better detection
        self.ocr_configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,-+()[]{}/',  # Numbers with punctuation
            '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',  # Single text line numbers only
            '--oem 3 --psm 8 -c tesseract_char_whitelist=0123456789',  # Single word numbers
            '--oem 3 --psm 13',  # Raw line, treat as single text line
            '--oem 3 --psm 6',   # Uniform block of text
            '--oem 1 --psm 6',   # Original LSTM engine
        ]
    
    def preprocess_image(self, image):
        """Enhanced preprocessing for better OCR accuracy with multiple techniques"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        processed_images = []
        
        # 1. Original grayscale
        processed_images.append(('original', gray))
        
        # 2. Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        clahe_img = clahe.apply(gray)
        processed_images.append(('clahe', clahe_img))
        
        # 3. Multiple threshold techniques
        # Otsu's thresholding
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(('otsu', otsu))
        
        # Otsu's thresholding inverted (for white text on dark background)
        _, otsu_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        processed_images.append(('otsu_inv', otsu_inv))
        
        # 4. Adaptive thresholding
        adaptive_mean = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append(('adaptive_mean', adaptive_mean))
        
        adaptive_gaussian = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append(('adaptive_gaussian', adaptive_gaussian))
        
        # 5. Morphological operations to enhance text
        kernel = np.ones((2, 2), np.uint8)
        
        # Closing to connect text components
        morph_close = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
        processed_images.append(('morph_close', morph_close))
        
        # Opening to remove noise
        morph_open = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel)
        processed_images.append(('morph_open', morph_open))
        
        # 6. Gaussian blur variations
        for sigma in [0.5, 1.0, 1.5]:
            blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
            _, blur_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append((f'blur_{sigma}', blur_thresh))
        
        # 7. Edge detection followed by dilation
        edges = cv2.Canny(gray, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        processed_images.append(('edges_dilated', dilated_edges))
        
        # 8. Unsharp masking for enhancement
        gaussian = cv2.GaussianBlur(gray, (0, 0), 2.0)
        unsharp = cv2.addWeighted(gray, 1.5, gaussian, -0.5, 0)
        _, unsharp_thresh = cv2.threshold(unsharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(('unsharp', unsharp_thresh))
        
        return processed_images
    
    def detect_number_regions(self, image_path):
        """Enhanced detection of regions containing numbers in the image"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read image")
        
        original_height, original_width = image.shape[:2]
        
        # Preprocess image with multiple techniques
        processed_images = self.preprocess_image(image)
        
        all_detections = []
        
        # Try different OCR configurations on different preprocessed versions
        for config in self.ocr_configs:
            for img_name, processed_img in processed_images:
                try:
                    # Get detailed OCR data
                    data = pytesseract.image_to_data(processed_img, config=config, output_type=pytesseract.Output.DICT)
                    
                    # Extract regions with numbers (lower confidence threshold)
                    detections = self.extract_number_regions(data, processed_img.shape, confidence_threshold=10)
                    
                    # Add source info for debugging
                    for detection in detections:
                        detection['source'] = f"{img_name}_{config[:10]}"
                    
                    all_detections.extend(detections)
                    
                except Exception as e:
                    print(f"Error processing {img_name} with config {config}: {e}")
                    continue
        
        # Additional: Try contour-based detection for handwritten numbers
        contour_detections = self.detect_by_contours(image)
        all_detections.extend(contour_detections)
        
        # Additional: Try template matching for common number patterns
        template_detections = self.detect_by_templates(image)
        all_detections.extend(template_detections)
        
        # Additional: Specific method for handwritten numbers on lined paper
        handwritten_detections = self.detect_handwritten_numbers(image)
        all_detections.extend(handwritten_detections)
        
        print(f"Total raw detections: {len(all_detections)}")
        
        # Remove duplicates and merge overlapping regions (more permissive)
        merged_detections = self.merge_overlapping_regions(all_detections, overlap_threshold=0.2)
        
        # If still no detections found, try more aggressive fallback methods
        if len(merged_detections) == 0:
            print("No detections found, trying fallback methods...")
            
            # Fallback 1: Create regions based on text-like areas in the image
            fallback_detections = self.detect_text_like_regions(image)
            all_detections.extend(fallback_detections)
            
            # Fallback 2: Grid-based sampling for handwritten content
            grid_detections = self.detect_by_grid_sampling(image)
            all_detections.extend(grid_detections)
            
            # Re-merge with all detections including fallbacks
            merged_detections = self.merge_overlapping_regions(all_detections, overlap_threshold=0.1)
            
        print(f"Final detections after fallback: {len(merged_detections)}")
        
        # Extract and save cropped regions
        cropped_regions = []
        for i, detection in enumerate(merged_detections):
            try:
                cropped_img = self.crop_number_region(image, detection)
                if cropped_img is not None:
                    cropped_regions.append({
                        'image': cropped_img,
                        'bbox': detection,
                        'index': i,
                        'confidence': detection.get('confidence', 0)
                    })
            except Exception as e:
                print(f"Error cropping region {i}: {e}")
                continue
        
        return cropped_regions
    
    def detect_by_contours(self, image):
        """Detect number regions using contour analysis - good for handwritten numbers"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply multiple threshold techniques
        detections = []
        
        threshold_methods = [
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
            cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        ]
        
        for thresh in threshold_methods:
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size - numbers should be within reasonable size range
                area = cv2.contourArea(contour)
                aspect_ratio = w / float(h)
                
                # More permissive size and ratio constraints
                if (15 < w < image.shape[1] * 0.8 and 
                    15 < h < image.shape[0] * 0.8 and 
                    area > 200 and 
                    0.1 < aspect_ratio < 10):
                    
                    # Add padding
                    padding = 5
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(image.shape[1] - x, w + 2 * padding)
                    h = min(image.shape[0] - y, h + 2 * padding)
                    
                    detections.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'confidence': 50,  # Medium confidence for contour-based
                        'text': 'contour_detected',
                        'source': 'contour'
                    })
        
        return detections
    
    def detect_handwritten_numbers(self, image):
        """Specialized detection for handwritten numbers on lined/grid paper"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = []
        
        # Remove lines first (common in notebook paper)
        gray_clean = self.remove_lines(gray)
        
        # Enhanced preprocessing for handwritten text
        # 1. Bilateral filter to reduce noise while keeping edges sharp
        bilateral = cv2.bilateralFilter(gray_clean, 9, 75, 75)
        
        # 2. Multiple threshold approaches
        _, thresh1 = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, thresh2 = cv2.threshold(bilateral, 127, 255, cv2.THRESH_BINARY)
        
        # 3. Morphological operations to connect broken characters
        kernel_connect = np.ones((2, 3), np.uint8)  # Horizontal connection
        connected = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel_connect)
        
        # Find contours in the processed image
        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # Check if this could be a handwritten number region
            if self.is_potential_number_region(gray_clean[y:y+h, x:x+w], w, h, area):
                # Add padding for context
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.shape[1] - x, w + 2 * padding)
                h = min(image.shape[0] - y, h + 2 * padding)
                
                detections.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'confidence': 40,
                    'text': 'handwritten_candidate',
                    'source': 'handwritten'
                })
        
        return detections
    
    def remove_lines(self, gray):
        """Remove horizontal and vertical lines from lined paper"""
        # Create kernels for line detection
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Detect horizontal lines
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detect vertical lines
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combine line masks
        lines_mask = cv2.add(horizontal_lines, vertical_lines)
        
        # Remove lines from original image
        result = cv2.subtract(gray, lines_mask)
        
        return result
    
    def is_potential_number_region(self, region, width, height, area):
        """Check if a region could potentially contain handwritten numbers"""
        # Size constraints
        if width < 15 or height < 15 or width > 500 or height > 100:
            return False
        
        if area < 100 or area > 5000:
            return False
        
        # Aspect ratio check (numbers can be various shapes)
        aspect_ratio = width / float(height)
        if aspect_ratio < 0.2 or aspect_ratio > 8:
            return False
        
        # Check pixel density (should have some dark pixels for text)
        dark_pixel_ratio = np.sum(region < 128) / (width * height)
        if dark_pixel_ratio < 0.05 or dark_pixel_ratio > 0.8:
            return False
        
        # Check for variation in the region (text should have contrast)
        if np.std(region) < 15:
            return False
        
        return True
    
    def detect_by_templates(self, image):
        """Detect number regions using template matching for common patterns"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = []
        
        # Create simple number-like templates
        templates = []
        for size in [(20, 30), (30, 40), (40, 50)]:
            # Create a simple rectangular template (simulates number block)
            template = np.ones(size, dtype=np.uint8) * 255
            cv2.rectangle(template, (2, 2), (size[0]-2, size[1]-2), 0, -1)
            templates.append(template)
        
        # Try template matching with different scales
        for template in templates:
            try:
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= 0.1)  # Very low threshold
                
                for pt in zip(*locations[::-1]):
                    x, y = pt
                    w, h = template.shape[1], template.shape[0]
                    
                    # Add padding
                    padding = 10
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(image.shape[1] - x, w + 2 * padding)
                    h = min(image.shape[0] - y, h + 2 * padding)
                    
                    if w > 20 and h > 20:  # Minimum size
                        detections.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'confidence': 30,  # Lower confidence for template
                            'text': 'template_match',
                            'source': 'template'
                        })
            except:
                continue
        
        return detections
    def extract_number_regions(self, ocr_data, image_shape, confidence_threshold=10):
        """Extract bounding boxes of regions containing numbers with enhanced detection"""
        detections = []
        height, width = image_shape      
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            confidence = float(ocr_data['conf'][i])
            
            # Skip if confidence is too low or text is empty
            if confidence < confidence_threshold or not text:
                continue
            
            # Enhanced number detection patterns
            has_numbers = (
                re.search(r'\d', text) or  # Contains digits
                re.search(r'[0-9]', text) or  # Explicit digit range
                any(char.isdigit() for char in text) or  # Python digit check
                # Common OCR misrecognitions of numbers
                any(char in 'lI|!oO()[]{}' for char in text)  # Characters often confused with numbers
            )
            
            # Also check for mathematical symbols that often accompany numbers
            has_math_symbols = any(symbol in text for symbol in ['+', '-', '=', '×', '÷', '*', '/', '.', ','])
            
            if has_numbers or has_math_symbols:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                # More generous padding around the detected region
                padding = 15
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(width - x, w + 2 * padding)
                h = min(height - y, h + 2 * padding)
                
                # More lenient size requirements
                if w > 10 and h > 10:  # Reduced minimum size
                    detections.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'confidence': confidence,
                        'text': text
                    })
        
        return detections
    
    def merge_overlapping_regions(self, detections, overlap_threshold=0.2):
        """Merge overlapping or very close regions with more permissive settings"""
        if not detections:
            return []
        
        # Sort by confidence first, then by area (larger regions first)
        detections.sort(key=lambda x: (x.get('confidence', 0), x['width'] * x['height']), reverse=True)
        
        merged = []
        used = set()
        
        for i, detection in enumerate(detections):
            if i in used:
                continue
            
            current_region = detection.copy()
            used.add(i)
            
            # Check for overlapping regions with more permissive threshold
            for j, other in enumerate(detections[i+1:], i+1):
                if j in used:
                    continue
                
                if self.regions_overlap(current_region, other, overlap_threshold) or self.regions_nearby(current_region, other):
                    # Merge regions
                    current_region = self.merge_two_regions(current_region, other)
                    used.add(j)
            
            merged.append(current_region)
        
        return merged
    
    def regions_nearby(self, region1, region2, distance_threshold=50):
        """Check if two regions are close enough to potentially be part of the same number sequence"""
        x1, y1, w1, h1 = region1['x'], region1['y'], region1['width'], region1['height']
        x2, y2, w2, h2 = region2['x'], region2['y'], region2['width'], region2['height']
        
        # Calculate center points
        center1_x, center1_y = x1 + w1/2, y1 + h1/2
        center2_x, center2_y = x2 + w2/2, y2 + h2/2
        
        # Calculate distance between centers
        distance = np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
        
        # Check if they're on roughly the same horizontal line (for multi-digit numbers)
        vertical_alignment = abs(center1_y - center2_y) < max(h1, h2) * 0.8
        
        return distance < distance_threshold and vertical_alignment
    
    def detect_text_like_regions(self, image):
        """Fallback method to detect any areas that look like they contain text/numbers"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = []
        
        # Use edge detection to find text-like regions
        edges = cv2.Canny(gray, 30, 100)
        
        # Dilate to connect nearby edges (typical in text)
        kernel = np.ones((3, 15), np.uint8)  # Horizontal kernel for connecting letters
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours of dilated regions
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # Look for regions that could contain text (wider than tall, reasonable size)
            if (w > 30 and h > 15 and 
                area > 500 and 
                aspect_ratio > 1.5 and  # Text is usually wider than tall
                aspect_ratio < 15):     # But not too wide
                
                # Add generous padding
                padding = 20
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.shape[1] - x, w + 2 * padding)
                h = min(image.shape[0] - y, h + 2 * padding)
                
                detections.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'confidence': 25,
                    'text': 'text_like_region',
                    'source': 'text_fallback'
                })
        
        return detections
    
    def detect_by_grid_sampling(self, image):
        """Sample the image in a grid and look for regions with content"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = []
        
        h, w = gray.shape
        
        # Create a grid of potential regions
        grid_size = 100  # Size of each grid cell
        overlap = 20     # Overlap between grid cells
        
        for y in range(0, h - grid_size, grid_size - overlap):
            for x in range(0, w - grid_size, grid_size - overlap):
                # Extract region
                region = gray[y:y+grid_size, x:x+grid_size]
                
                # Calculate statistics for this region
                mean_val = np.mean(region)
                std_val = np.std(region)
                
                # Look for regions with high contrast (likely to contain text)
                if std_val > 30:  # High standard deviation means varied content
                    # Check if there are dark areas on light background or vice versa
                    dark_pixels = np.sum(region < mean_val - std_val)
                    light_pixels = np.sum(region > mean_val + std_val)
                    
                    if dark_pixels > 50 and light_pixels > 50:  # Mixed content
                        detections.append({
                            'x': x,
                            'y': y,
                            'width': grid_size,
                            'height': grid_size,
                            'confidence': 20,
                            'text': 'grid_sampled',
                            'source': 'grid_sampling'
                        })
        
        return detections
    
    def regions_overlap(self, region1, region2, threshold=0.3):
        """Check if two regions overlap significantly"""
        x1, y1, w1, h1 = region1['x'], region1['y'], region1['width'], region1['height']
        x2, y2, w2, h2 = region2['x'], region2['y'], region2['width'], region2['height']
        
        # Calculate intersection
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        
        if left >= right or top >= bottom:
            return False
        
        intersection_area = (right - left) * (bottom - top)
        area1 = w1 * h1
        area2 = w2 * h2
        
        # Check if intersection is significant
        overlap_ratio = intersection_area / min(area1, area2)
        return overlap_ratio > threshold
    
    def merge_two_regions(self, region1, region2):
        """Merge two overlapping regions"""
        x1, y1, w1, h1 = region1['x'], region1['y'], region1['width'], region1['height']
        x2, y2, w2, h2 = region2['x'], region2['y'], region2['width'], region2['height']
        
        # Calculate merged bounding box
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1 + w1, x2 + w2)
        bottom = max(y1 + h1, y2 + h2)
        
        return {
            'x': left,
            'y': top,
            'width': right - left,
            'height': bottom - top,
            'confidence': max(region1['confidence'], region2['confidence']),
            'text': f"{region1.get('text', '')} {region2.get('text', '')}".strip()
        }
    
    def crop_number_region(self, original_image, detection):
        """Crop the number region from original image"""
        x, y, w, h = detection['x'], detection['y'], detection['width'], detection['height']
        
        # Ensure coordinates are within image bounds
        img_height, img_width = original_image.shape[:2]
        x = max(0, min(x, img_width - 1))
        y = max(0, min(y, img_height - 1))
        w = min(w, img_width - x)
        h = min(h, img_height - y)
        
        if w <= 0 or h <= 0:
            return None
        
        # Crop the region
        cropped = original_image[y:y+h, x:x+w]
        
        # Convert to PIL Image
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(cropped_rgb)
        
        return pil_image
    
    def save_cropped_image(self, pil_image, filename):
        """Save PIL image to Django file field"""
        # Convert PIL image to bytes
        img_io = io.BytesIO()
        pil_image.save(img_io, format='PNG', quality=95)
        img_io.seek(0)
        
        # Create Django file
        django_file = ContentFile(img_io.getvalue())
        django_file.name = filename
        
        return django_file

def extract_number_regions_from_image(image_path):
    """Enhanced main function to extract number regions from uploaded image"""
    extractor = NumberRegionExtractor()
    
    try:
        print(f"Starting extraction for image: {image_path}")
        
        # Detect and crop number regions
        cropped_regions = extractor.detect_number_regions(image_path)
        
        print(f"Extraction completed. Found {len(cropped_regions)} regions.")
        
        return cropped_regions
        
    except Exception as e:
        print(f"Error extracting number regions: {e}")
        import traceback
        traceback.print_exc()
        return []