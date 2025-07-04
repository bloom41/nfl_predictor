"""
Custom storage backends for NFL Django Assistant
Handles static files and media files for different environments
"""

import os
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """
    Static files storage backend for S3
    Used for CSS, JavaScript, images, etc.
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.STATICFILES_LOCATION
    default_acl = 'public-read'
    file_overwrite = True
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)


class MediaStorage(S3Boto3Storage):
    """
    Media files storage backend for S3
    Used for user uploads, generated reports, etc.
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.MEDIAFILES_LOCATION
    default_acl = 'private'
    file_overwrite = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)


class PublicMediaStorage(S3Boto3Storage):
    """
    Public media files storage backend for S3
    Used for publicly accessible uploads like logos, etc.
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = 'public-media'
    default_acl = 'public-read'
    file_overwrite = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)