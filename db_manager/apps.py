from django.apps import AppConfig
from django.db.models.signals import post_migrate

class DbManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'db_manager'
    verbose_name = 'Database Manager'
    
    def ready(self):
        """Initialize app after Django is ready"""
        import logging
        from django.dispatch import receiver
        from .services import db_service
        from .models import MonitoringConfig

        logger = logging.getLogger(__name__)

        @receiver(post_migrate)
        def start_monitors(sender, **kwargs):
            try:
                active_monitors = MonitoringConfig.objects.filter(is_monitoring_active=True)
                for config in active_monitors:
                    db_service.start_monitoring(config)
                logger.info("✅ Monitoring services started after migration")
            except Exception as e:
                logger.warning(f"❌ Could not start monitoring services: {e}")


#IF NOT WORKING USE THIS BELOW CODE UPPER EXTRA CODE IS FOR MAKING AUTOMATED REPORTS

# class DbManagerConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'db_manager'
#     verbose_name = 'Database Manager'
    
#     def ready(self):
#         """Initialize the app when Django starts"""
#         # Import and start any monitoring services
#         try:
#             from .services import db_service
#             from .models import MonitoringConfig
            
#             # Start monitoring for active configurations
#             active_monitors = MonitoringConfig.objects.filter(is_monitoring_active=True)
#             for config in active_monitors:
#                 db_service.start_monitoring(config)
#         except Exception as e:
#             # Handle any import errors during startup
#             import logging
#             logger = logging.getLogger(__name__)
#             logger.warning(f"Could not start monitoring services: {e}")