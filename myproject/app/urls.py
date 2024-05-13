from django.contrib import admin
from django.urls import path
from . import views
# from views import process_image

urlpatterns = [
    path('admin/', admin.site.urls),    
    path('', views.home, name='home'),    
    path('upload/', views.process_file, name='process_file'),
    path('search/', views.search_documents, name='search_documents'),
    path('tables/', views.tables, name='tables'),
    path('tables/<str:document_id>/delete/', views.delete_document, name='delete_document'),
    path('tables/<str:document_id>/edit/', views.edit_document, name='edit_document'),
    path('tables/<str:document_id>/download/', views.download_document, name='download_document'),
    path('tables/<str:document_id>/update/', views.update_document, name='update_document'), 


]
