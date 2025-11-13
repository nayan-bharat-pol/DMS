from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib import messages

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Count, Avg
from datetime import datetime, timedelta
import json

from .models import DatabaseConnection, MonitoringConfig, QueryLog, DatabaseStats
from .services import db_service
from .forms import DatabaseConnectionForm, MonitoringConfigForm, QueryForm
from .tasks import check_db_and_mail  # import from tasks.py




def dashboard(request):
    """Main dashboard view"""
    connections = DatabaseConnection.objects.filter(is_active=True)
    recent_logs = QueryLog.objects.select_related('database_connection').order_by('-executed_at')[:10]
    
    # Get statistics
    total_connections = connections.count()
    total_queries_today = QueryLog.objects.filter(
        executed_at__date=datetime.now().date()
    ).count()
    
    active_monitors = MonitoringConfig.objects.filter(is_monitoring_active=True).count()
    
    context = {
        'connections': connections,
        'recent_logs': recent_logs,
        'total_connections': total_connections,
        'total_queries_today': total_queries_today,
        'active_monitors': active_monitors,
    }
    
    return render(request, 'db_manager/dashboard.html', context)

def connection_list(request):
    """List all database connections"""
    connections = DatabaseConnection.objects.all().order_by('-created_at')
    
    context = {
        'connections': connections,
    }
    
    return render(request, 'db_manager/connection_list.html', context)

def add_connection(request):
    """Add new database connection"""
    if request.method == 'POST':
        form = DatabaseConnectionForm(request.POST)
        if form.is_valid():
            connection = form.save()
            
            # Test the connection
            result = db_service.test_connection(connection)
            if result['status'] == 'success':
                messages.success(request, f'Database connection "{connection.name}" added successfully!')
            else:
                messages.warning(request, f'Connection added but test failed: {result["message"]}')
            
            return redirect('db_manager:connection_list')
    else:
        form = DatabaseConnectionForm()
    
    context = {
        'form': form,
        'title': 'Add Database Connection'
    }
    
    return render(request, 'db_manager/connection_form.html', context)

def edit_connection(request, connection_id):
    """Edit database connection"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    
    if request.method == 'POST':
        form = DatabaseConnectionForm(request.POST, instance=connection)
        if form.is_valid():
            connection = form.save()
            messages.success(request, f'Connection "{connection.name}" updated successfully!')
            return redirect('db_manager:connection_list')
    else:
        form = DatabaseConnectionForm(instance=connection)
    
    context = {
        'form': form,
        'connection': connection,
        'title': f'Edit Connection: {connection.name}'
    }
    
    return render(request, 'db_manager/connection_form.html', context)

def test_connection_view(request, connection_id):
    """Test database connection"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    result = db_service.test_connection(connection)

    if result.get('status') == 'success':
        exec_time = result.get('execution_time', 0)
        messages.success(
            request,
            f'✅ Connection test successful! Response time: {exec_time:.2f}s'
        )
    else:
        messages.error(
            request,
            f'❌ Connection test failed: {result.get("message", "Unknown error")}'
        )

    return redirect('db_manager:connection_list')


def query_interface(request, connection_id):
    """Query interface for a specific database"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            timeout = form.cleaned_data.get('timeout', 8)
            
            result = db_service.execute_query(connection, query, timeout)
            
            context = {
                'connection': connection,
                'form': form,
                'result': result,
            }
            
            return render(request, 'db_manager/query_interface.html', context)
    else:
        form = QueryForm()
    
    # Get recent queries for this connection
    recent_queries = QueryLog.objects.filter(
        database_connection=connection
    ).order_by('-executed_at')[:5]
    
    context = {
        'connection': connection,
        'form': form,
        'recent_queries': recent_queries,
    }
    
    return render(request, 'db_manager/query_interface.html', context)

def monitoring_config(request, connection_id):
    """Configure monitoring for a database"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    
    try:
        monitor_config = MonitoringConfig.objects.get(database_connection=connection)
    except MonitoringConfig.DoesNotExist:
        monitor_config = None
    
    if request.method == 'POST':
        form = MonitoringConfigForm(request.POST, instance=monitor_config)
        if form.is_valid():
            config = form.save(commit=False)
            config.database_connection = connection
            config.save()
            
            # Start monitoring if active
            if config.is_monitoring_active:
                db_service.start_monitoring(config)
            
            messages.success(request, 'Monitoring configuration saved successfully!')
            return redirect('db_manager:connection_list')
    else:
        form = MonitoringConfigForm(instance=monitor_config)
    
    context = {
        'form': form,
        'connection': connection,
        'monitor_config': monitor_config,
    }
    
    return render(request, 'db_manager/monitoring_config.html', context)

def query_logs(request, connection_id=None):
    """View query logs"""
    logs = QueryLog.objects.select_related('database_connection').order_by('-executed_at')
    
    if connection_id:
        connection = get_object_or_404(DatabaseConnection, id=connection_id)
        logs = logs.filter(database_connection=connection)
    else:
        connection = None
    
    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'connection': connection,
    }
    
    return render(request, 'db_manager/query_logs.html', context)

def database_stats_view(request, connection_id):
    """View database statistics"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    
    # Get time period from request
    hours = int(request.GET.get('hours', 24))
    
    # Get statistics
    stats = db_service.get_database_stats(connection, hours)
    
    # Get historical data for charts
    since = datetime.now() - timedelta(hours=hours)
    historical_stats = DatabaseStats.objects.filter(
        database_connection=connection,
        timestamp__gte=since
    ).order_by('timestamp')
    
    context = {
        'connection': connection,
        'stats': stats,
        'historical_stats': historical_stats,
        'hours': hours,
    }
    
    return render(request, 'db_manager/database_stats.html', context)

@csrf_exempt
def api_execute_query(request):
    """API endpoint to execute queries"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        connection_id = data.get('connection_id')
        query = data.get('query')
        timeout = data.get('timeout', 8)
        
        if not connection_id or not query:
            return JsonResponse({'error': 'connection_id and query are required'}, status=400)
        
        connection = get_object_or_404(DatabaseConnection, id=connection_id)
        result = db_service.execute_query(connection, query, timeout)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_connection_stats(request, connection_id):
    """API endpoint to get connection statistics"""
    connection = get_object_or_404(DatabaseConnection, id=connection_id)
    hours = int(request.GET.get('hours', 24))
    
    stats = db_service.get_database_stats(connection, hours)
    
    return JsonResponse(stats)


def test_task(request):
    """
    Example endpoint to schedule task.
    Sends email every 300 seconds to a given person.
    """
    recipient = request.GET.get("recipient", "target_person@example.com")
    interval = int(request.GET.get("interval", 120))  # default 2 min

    # schedule the task
    check_db_and_mail(recipient, repeat=300)
    return HttpResponse(f"Task scheduled! Email will be sent to {recipient} every 5 minutes.")


# Automated Report Scheduling (PDF/Excel + Email Delivery)

def schedule_report(request):
    recipient = request.GET.get("recipient", "target_person@example.com")
    query = request.GET.get("query", "SELECT * FROM your_table LIMIT 10;")
    interval = int(request.GET.get("interval", 86400))  # default 1 day = 86400 sec

    




def delete_query_log(request, log_id):
    """Delete a query log"""
    log = get_object_or_404(QueryLog, id=log_id)
    log.delete()
    messages.success(request, "Query log deleted successfully ✅")
    return redirect('db_manager:query_logs')