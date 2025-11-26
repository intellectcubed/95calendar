# aws_config.py
"""
Configuration module that supports both local (.env) and AWS (Secrets Manager) environments.
"""
import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv


class ConfigManager:
    """Manages configuration from either .env file or AWS Secrets Manager."""

    def __init__(self):
        self._config_cache: Dict[str, str] = {}
        self._is_lambda = self._detect_lambda_environment()

        if self._is_lambda:
            self._init_aws_config()
        else:
            self._init_local_config()

    def _detect_lambda_environment(self) -> bool:
        """Detect if running in AWS Lambda environment."""
        return bool(os.environ.get('AWS_EXECUTION_ENV') or
                   os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

    def _init_local_config(self):
        """Initialize configuration from local .env file."""
        load_dotenv()
        print("📁 Loading configuration from .env file")

    def _init_aws_config(self):
        """Initialize configuration from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            secret_name = os.environ.get('SECRET_NAME', 'calendar-service-secrets')

            # AWS_REGION is automatically set by Lambda runtime
            # boto3 will automatically use it, no need to specify
            print(f"🔐 Loading configuration from AWS Secrets Manager: {secret_name}")

            session = boto3.session.Session()
            client = session.client(service_name='secretsmanager')

            # Log the region being used
            region = client.meta.region_name
            print(f"📍 Using AWS region: {region}")

            try:
                response = client.get_secret_value(SecretId=secret_name)
                secret_string = response['SecretString']
                secrets = json.loads(secret_string)
                self._config_cache = secrets
                print(f"✅ Loaded {len(secrets)} secrets from AWS Secrets Manager")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(f"❌ Error loading secrets from AWS: {error_code}")
                raise EnvironmentError(
                    f"Failed to load secrets from AWS Secrets Manager: {error_code}"
                )
        except ImportError:
            print("⚠️  boto3 not available, falling back to environment variables")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get configuration value.

        Args:
            key: Configuration key name
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._is_lambda and key in self._config_cache:
            return self._config_cache[key]

        return os.environ.get(key, default)

    def get_required(self, key: str) -> str:
        """
        Get required configuration value.

        Args:
            key: Configuration key name

        Returns:
            Configuration value

        Raises:
            EnvironmentError: If key is not found
        """
        value = self.get(key)
        if value is None:
            raise EnvironmentError(
                f"{key} is not set.\n"
                f"Local: Set it in .env file\n"
                f"Lambda: Ensure it exists in AWS Secrets Manager"
            )
        return value

    @property
    def is_lambda(self) -> bool:
        """Check if running in Lambda environment."""
        return self._is_lambda


# Global configuration instance
config = ConfigManager()
