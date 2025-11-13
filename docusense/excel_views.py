import json
import uuid
import pandas as pd
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Document, ChatMessage
from .utils import read_document_content, ask_gemini

@csrf_exempt
@require_http_methods(["POST"])
def upload_excel(request):
    """
    Handle Excel file upload with additional processing
    """
    if 'excel_file' not in request.FILES:
        return JsonResponse({'error': 'No Excel file provided'}, status=400)
    
    uploaded_file = request.FILES['excel_file']
    
    # Validate file type
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in ['xlsx', 'xls']:
        return JsonResponse({'error': 'Only Excel files (.xlsx, .xls) are supported'}, status=400)
    
    try:
        # Read Excel file using pandas for better processing
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file)
        
        # Get basic info about the Excel file
        num_rows = len(df)
        num_cols = len(df.columns)
        column_names = df.columns.tolist()
        
        # Create a summary of the Excel data
        summary = {
            'total_rows': num_rows,
            'total_columns': num_cols,
            'column_names': column_names,
            'sample_data': df.head(5).to_dict('records')
        }
        
        # Read document content for AI processing
        uploaded_file.seek(0)
        content = read_document_content(uploaded_file)
        
        # Save document
        document = Document.objects.create(
            name=uploaded_file.name,
            file=uploaded_file,
            file_type='xlsx',
            size=get_file_size_display(uploaded_file.size),
            content=json.dumps(summary, indent=2) if content is None else content,
            user=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'success': True,
            'document': {
                'id': document.id,
                'name': document.name,
                'type': 'Excel',
                'size': document.size,
                'uploaded': 'Just now',
                'status': document.status,
                'summary': summary
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error processing Excel file: {str(e)}'}, status=400)

def get_file_size_display(size):
    """Helper function to format file size"""
    if size > 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    elif size > 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size} bytes"

@csrf_exempt
@require_http_methods(["POST"])
def analyze_excel_data(request, document_id):
    """
    Analyze Excel data with AI
    """
    try:
        data = json.loads(request.body)
        question = data.get('question')
        session_id = data.get('session_id')
        
        if not all([question, session_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        document = get_object_or_404(Document, id=document_id)
        
        if document.file_type != 'xlsx':
            return JsonResponse({'error': 'This is not an Excel file'}, status=400)
        
        # Save user message
        user_message = ChatMessage.objects.create(
            document=document,
            role='user',
            content=question,
            session_id=session_id
        )
        
        # Get AI response
        ai_response = ask_gemini(document.content, question)
        
        # Save AI response
        ai_message = ChatMessage.objects.create(
            document=document,
            role='assistant',
            content=ai_response,
            session_id=session_id
        )
        
        return JsonResponse({
            'success': True,
            'user_message': {
                'role': 'user',
                'content': question,
                'timestamp': user_message.timestamp.isoformat()
            },
            'ai_message': {
                'role': 'assistant',
                'content': ai_response,
                'timestamp': ai_message.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
