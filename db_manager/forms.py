from django import forms
from django.core.validators import EmailValidator
from .models import DatabaseConnection, MonitoringConfig

class DatabaseConnectionForm(forms.ModelForm):
    """Form for creating/editing database connections"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter database password'
        })
    )
    
    class Meta:
        model = DatabaseConnection
        fields = ['name', 'db_type', 'host', 'port', 'database_name', 'username', 'password', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter connection name'
            }),
            'db_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'localhost or IP address'
            }),
            'port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '3306'
            }),
            'database_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Database name'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Database username'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default ports based on database type
        self.fields['port'].help_text = "Default ports: MySQL(3306), PostgreSQL(5432), Oracle(1521)"

class MonitoringConfigForm(forms.ModelForm):
    """Form for monitoring configuration"""
    
    email_recipients = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'admin@example.com, user@example.com'
        }),
        help_text="Enter comma-separated email addresses"
    )
    
    class Meta:
        model = MonitoringConfig
        fields = [
            'query_timeout', 'monitoring_interval', 'email_recipients', 
            'alert_threshold', 'is_monitoring_active'
        ]
        widgets = {
            'query_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 60
            }),
            'monitoring_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 60,
                'step': 60
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_monitoring_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_email_recipients(self):
        """Validate email addresses"""
        emails = self.cleaned_data['email_recipients']
        email_list = [email.strip() for email in emails.split(',')]
        
        validator = EmailValidator()
        for email in email_list:
            if email:  # Skip empty strings
                try:
                    validator(email)
                except forms.ValidationError:
                    raise forms.ValidationError(f'Invalid email address: {email}')
        
        return emails

class QueryForm(forms.Form):
    """Form for executing database queries"""
    
    query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Enter your SQL query here...',
            'style': 'font-family: monospace;'
        }),
        help_text="Enter SQL query to execute"
    )
    
    timeout = forms.IntegerField(
        initial=8,
        min_value=1,
        max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 100px;'
        }),
        help_text="Query timeout in seconds"
    )

class DatabaseSearchForm(forms.Form):
    """Form for searching databases"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search connections...'
        })
    )
    
    db_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + DatabaseConnection.DB_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    db_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + DatabaseConnection.DB_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
