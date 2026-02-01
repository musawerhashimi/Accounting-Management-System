 
import os
import uuid
from django.utils.text import slugify
from core.threads import get_current_tenant


def upload_image_path(instance, filename, folder_name='uploads', instance_field_name='name', name=None):
    """
    Generate a readable and unique file path for uploaded images.

    Example output:
    'products/images/my-awesome-name-a1b2c3.jpg'
    """
    # Get file extension
    ext = os.path.splitext(filename)[1]

    # Get Tenant
    tenant = get_current_tenant()
    sanitized_tenant_name = slugify(tenant.name)

    # Try to get a meaningful name from the instance (fallback to model name)
    if not name:
        name = getattr(instance, instance_field_name, str(instance.__class__.__name__))
    # Sanitize name
    sanitized_name = slugify(name)

    # Generate short unique hash
    unique_hash = uuid.uuid4().hex[:6]

    # Final filename
    filename = f"{sanitized_name}-{unique_hash}{ext}"

    # Directory based on model
    return os.path.join(sanitized_tenant_name, folder_name, filename)
