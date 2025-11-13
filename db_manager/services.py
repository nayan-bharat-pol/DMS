import logging
import time
import threading
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.db.models import Avg

from django.conf import settings
from django.db import transaction
from .models import DatabaseConnection, MonitoringConfig, QueryLog, DatabaseStats

# Import database drivers
try:
    import mysql.connector
    import psycopg2
    # import cx_Oracle
    import oracledb
    import sqlite3
except ImportError as e:
    logging.warning(f"Database driver import error: {e}")

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service to handle database connections and operations"""
    
    def __init__(self):
        self.connections = {}
        self.monitoring_threads = {}
    
    @contextmanager
    def get_connection(self, db_config: DatabaseConnection):
        """Get database connection based on type"""
        connection = None
        try:
            if db_config.db_type == 'mysql':
                connection = mysql.connector.connect(
                    host=db_config.host,
                    port=db_config.port,
                    database=db_config.database_name,
                    user=db_config.username,
                    password=db_config.password,
                    connection_timeout=8
                )
            elif db_config.db_type == 'postgresql':
                connection = psycopg2.connect(
                    host=db_config.host,
                    port=db_config.port,
                    database=db_config.database_name,
                    user=db_config.username,
                    password=db_config.password,
                    connect_timeout=8
                )
            elif db_config.db_type == 'oracle':
                dsn = f"{db_config.host}:{db_config.port}/{db_config.database_name}"
                connection = oracledb.connect(
                    user=db_config.username,
                    password=db_config.password,
                    dsn=dsn
                )
            elif db_config.db_type == 'sqlite':
                connection = sqlite3.connect(db_config.database_name, timeout=8)
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def test_connection(self, db_config: DatabaseConnection) -> Dict[str, Any]:
        """Test database connection"""   # ⬅️ fixed: exactly 4 spaces
        start_time = time.time()
        db_type = db_config.db_type.lower()

        try:
            with self.get_connection(db_config) as conn:
                cursor = conn.cursor()

                # Simple test query based on database type
                if db_type in ['mysql', 'postgresql']:
                    cursor.execute("SELECT 1")
                elif db_type == 'oracle':
                    cursor.execute("SELECT 1 FROM DUAL")
                else:  # sqlite or fallback
                    cursor.execute("SELECT 1")

                result = cursor.fetchone()
                cursor.close()
                execution_time = time.time() - start_time

                return {
                    'status': 'success',
                    'message': 'Connection successful',
                    'execution_time': execution_time,
                    'result': result
                }

        except ImportError as e:
            execution_time = time.time() - start_time
            return {
                'status': 'error',
                'message': f'Missing driver or library: {e}',
                'execution_time': execution_time,
                'result': None
            }

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'status': 'error',
                'message': str(e),
                'execution_time': execution_time,
                'result': None
            }


    
    def execute_query(self, db_config: DatabaseConnection, query: str, timeout: int = 8) -> Dict[str, Any]:
        """Execute a query with timeout"""
        start_time = time.time()
        
        try:
            with self.get_connection(db_config) as conn:
                cursor = conn.cursor()
                
                # Set query timeout if supported
                if hasattr(cursor, 'execute'):
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                    result_count = len(results)
                else:
                    results = cursor.rowcount
                    column_names = []
                    result_count = cursor.rowcount
                    conn.commit()
                
                execution_time = time.time() - start_time
                
                # Log the query
                self.log_query(db_config, query, 'success', execution_time, result_count)
                
                return {
                    'status': 'success',
                    'results': results,
                    'column_names': column_names,
                    'result_count': result_count,
                    'execution_time': execution_time,
                    'message': f'Query executed successfully in {execution_time:.2f}s'
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            # Determine if it's a timeout
            status = 'timeout' if execution_time >= timeout else 'error'
            
            # Log the failed query
            self.log_query(db_config, query, status, execution_time, 0, error_message)
            
            return {
                'status': status,
                'results': [],
                'column_names': [],
                'result_count': 0,
                'execution_time': execution_time,
                'message': error_message
            }
    
    def log_query(self, db_config: DatabaseConnection, query: str, status: str, 
                  execution_time: float, result_count: int = 0, error_message: str = None):
        """Log query execution"""
        try:
            QueryLog.objects.create(
                database_connection=db_config,
                query=query,
                status=status,
                execution_time=execution_time,
                result_count=result_count,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Error logging query: {e}")
    
    def get_database_stats(self, db_config: DatabaseConnection, hours: int = 24) -> Dict[str, Any]:
        """Get database statistics for the last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        
        logs = QueryLog.objects.filter(
            database_connection=db_config,
            executed_at__gte=since
        )
        
        total_queries = logs.count()
        successful_queries = logs.filter(status='success').count()
        failed_queries = logs.filter(status__in=['error', 'timeout']).count()
        
        if total_queries > 0:
            avg_response_time = logs.aggregate(
                avg_time=models.Avg('execution_time')
            )['avg_time'] or 0
        else:
            avg_response_time = 0
        
        return {
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'failed_queries': failed_queries,
            'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
            'average_response_time': round(avg_response_time, 3)
        }
    
    def start_monitoring(self, monitoring_config: MonitoringConfig):
        """Start monitoring for a database"""
        if monitoring_config.id in self.monitoring_threads:
            return
        
        def monitor():
            while monitoring_config.is_monitoring_active:
                try:
                    # Test connection and log stats
                    result = self.test_connection(monitoring_config.database_connection)
                    
                    # Get current stats
                    stats = self.get_database_stats(monitoring_config.database_connection, 1)
                    
                    # Check if alert threshold is exceeded
                    if stats['total_queries'] > monitoring_config.alert_threshold:
                        self.send_alert(monitoring_config, stats)
                    
                    # Store stats
                    DatabaseStats.objects.create(
                        database_connection=monitoring_config.database_connection,
                        total_queries=stats['total_queries'],
                        successful_queries=stats['successful_queries'],
                        failed_queries=stats['failed_queries'],
                        average_response_time=stats['average_response_time']
                    )
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                
                time.sleep(monitoring_config.monitoring_interval)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        self.monitoring_threads[monitoring_config.id] = thread
    
    def send_alert(self, monitoring_config: MonitoringConfig, stats: Dict[str, Any]):
        """Send email alert"""
        try:
            subject = f"Database Alert: {monitoring_config.database_connection.name}"
            message = f"""
            Database monitoring alert for {monitoring_config.database_connection.name}:
            
            Total Queries (last hour): {stats['total_queries']}
            Successful Queries: {stats['successful_queries']}
            Failed Queries: {stats['failed_queries']}
            Success Rate: {stats['success_rate']:.1f}%
            Average Response Time: {stats['average_response_time']}s
            
            Threshold exceeded: {monitoring_config.alert_threshold}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=monitoring_config.get_email_list(),
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"Error sending alert email: {e}")

# Global service instance
db_service = DatabaseService()