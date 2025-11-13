from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageUploadView.as_view(), name='upload'),
    path('results/<int:image_id>/', views.ResultsView.as_view(), name='results'),
    path('debug/<int:image_id>/', views.DebugView.as_view(), name='debug'),
    path('all/', views.AllResultsView.as_view(), name='all_results'),
    path('delete/<int:pk>/', views.delete_uploaded_image, name='delete_uploaded_image'),
]
