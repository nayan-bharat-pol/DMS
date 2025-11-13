# docusense/urls.py (app urls)
from django.urls import path
from . import views
from . import excel_views


app_name = 'docusense'

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_document, name='upload_document'),
    path('upload-excel/', excel_views.upload_excel, name='upload_excel'),
    path('document/<int:document_id>/', views.document_detail, name='document_detail'),
    path('chat/', views.chat_with_document, name='chat_with_document'),
    path('analyze-excel/<int:document_id>/', excel_views.analyze_excel_data, name='analyze_excel_data'),
    path('toggle-status/<int:document_id>/', views.toggle_document_status, name='toggle_document_status'),
    path('delete-document/<int:document_id>/', views.delete_document, name='delete_document'),

     path('documents/all/', views.all_documents, name='all_documents'),
    path('documents/recent/', views.recent_documents, name='recent_documents'),
    path('documents/pdfs/', views.pdf_documents, name='pdf_documents'),
    path('documents/word/', views.word_documents, name='word_documents'),
    path('documents/excel/', views.excel_documents, name='excel_documents'),
]