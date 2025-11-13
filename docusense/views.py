import json
import uuid
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
from .models import Document, ChatMessage
from .utils import read_document_content, ask_gemini
import google.generativeai as genai
from . import gemini_config  # This will run the proxy + API key setup

from django.utils import timezone
from datetime import timedelta


genai.configure(api_key=settings.GOOGLE_API_KEY)

def home(request):
    documents = Document.objects.all()
    
    # Get session ID for chat
    session_id = request.session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['session_id'] = session_id
    
    context = {
        'documents': documents,
        'session_id': session_id,
        'csrf_token': get_token(request),
    }
    return render(request, 'docusense/home.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def upload_document(request):
    if 'document' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    uploaded_file = request.FILES['document']
    
    # Determine file type
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension == 'pdf':
        file_type = 'pdf'
    elif file_extension == 'docx':
        file_type = 'docx'
    elif file_extension == 'txt':
        file_type = 'txt'
    elif file_extension == 'xlsx':
        file_type = 'xlsx'
    else:
        return JsonResponse({'error': 'Unsupported file type'}, status=400)
    
    # Read document content
    content = read_document_content(uploaded_file)
    if content is None:
        return JsonResponse({'error': 'Failed to read document content'}, status=400)
    
    # Save document
    document = Document.objects.create(
        name=uploaded_file.name,
        file=uploaded_file,
        file_type=file_type,
        size=get_file_size_display(uploaded_file.size),
        content=content,
        user=request.user if request.user.is_authenticated else None
    )
    
    return JsonResponse({
        'success': True,
        'document': {
            'id': document.id,
            'name': document.name,
            'type': document.file_type,
            'size': document.size,
            'uploaded': 'Just now',
            'status': document.status
        }
    })

def get_file_size_display(size):
    if size > 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / 1024:.1f} KB"

def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    session_id = request.session.get('session_id', str(uuid.uuid4()))
    
    # Get chat history for this document and session
    chat_messages = ChatMessage.objects.filter(
        document=document, 
        session_id=session_id
    )
    
    context = {
        'document': document,
        'chat_messages': chat_messages,
        'session_id': session_id,
    }
    return render(request, 'docusense/document_detail.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def chat_with_document(request):
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        question = data.get('question')
        session_id = data.get('session_id')
        
        if not all([document_id, question, session_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        document = get_object_or_404(Document, id=document_id)
        
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
    


def chat_with_ai(request):
    if request.method == "POST":
        user_message = request.POST.get("message")

        # Proxy setup
        proxies = {
            "http": "http://mio1na:PassioM@!2022@10.171.234.13:8080",
            "https": "http://mio1na:PassioM@!2022@10.171.234.13:8080"
        }

        # API request with proxy
        ai_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer YOUR_API_KEY"},
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": user_message}]},
            proxies=proxies
        )

        return JsonResponse(ai_response.json())
    
    # return render(request, 'base.html')
    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_document_status(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    document.status = not document.status
    document.save()

    return JsonResponse({
        'success': True,
        'status': document.status
    })


# <------------------DELETE FUNCTIONALITY--------------------->
def delete_document(request, document_id):
    if request.method == "POST":
        document = get_object_or_404(Document, id=document_id)

        # Delete file from storage
        if document.file:
            document.file.delete(save=False)

        # Delete record from DB
        document.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)



def all_documents(request):
    documents = Document.objects.all()
    return render(request, 'docusense/home.html', {'documents': documents})

def recent_documents(request):
    one_week_ago = timezone.now() - timedelta(days=7)
    documents = Document.objects.filter(created_at__gte=one_week_ago)
    return render(request, 'docusense/home.html', {'documents': documents})

def pdf_documents(request):
    documents = Document.objects.filter(file_type='pdf')
    return render(request, 'docusense/home.html', {'documents': documents})

def word_documents(request):
    documents = Document.objects.filter(file_type='docx')
    return render(request, 'docusense/home.html', {'documents': documents})

def excel_documents(request):
    documents = Document.objects.filter(file_type__in=['xls', 'xlsx'])
    return render(request, 'docusense/home.html', {'documents': documents})


def recent_documents(request):
    one_week_ago = timezone.now() - timedelta(days=7)
    documents = Document.objects.filter(uploaded_at__gte=one_week_ago)
    return render(request, 'docusense/home.html', {'documents': documents})

