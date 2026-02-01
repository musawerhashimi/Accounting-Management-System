
import os
import uuid

import slugify


def customer_image_path(instance, filename):
    """
    Generate a readable and unique file path for a new customer image.
    e.g., 'products/images/my-awesome-product-a1b2c3.jpg'
    """
    # Get the file extension
    ext = os.path.splitext(filename)[1]

    customer_name = instance.name

    # Sanitize the customer name to be used in a URL/filename
    sanitized_name = slugify.slugify(customer_name)
    
    # Generate a short unique hash to prevent name collisions
    unique_hash = uuid.uuid4().hex[:6]
    
    # Combine them for the final filename
    filename = f'{sanitized_name}-{unique_hash}{ext}'
    
    return os.path.join('customers/images/', filename)
