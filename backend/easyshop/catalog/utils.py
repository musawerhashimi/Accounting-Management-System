
import uuid
import os
from django.utils.text import slugify


def product_image_path(instance, filename):
    """
    Generate a readable and unique file path for a new product image.
    e.g., 'products/images/my-awesome-product-a1b2c3.jpg'
    """
    # Get the file extension
    ext = os.path.splitext(filename)[1]

    variant_name = instance.variant_name
    if not variant_name:
        variant_name = instance.default_variant.variant_name
        
    # Sanitize the product name to be used in a URL/filename
    sanitized_name = slugify(instance.variant_name)
    
    # Generate a short unique hash to prevent name collisions
    unique_hash = uuid.uuid4().hex[:6]
    
    # Combine them for the final filename
    filename = f'{sanitized_name}-{unique_hash}{ext}'
    
    return os.path.join('products/images/', filename)


def generate_barcode(existingBarcodes: list[str] = []):
    """Generate batch number for variant"""
    from catalog.models import ProductVariant
    try:
        last_barcode = int(
            ProductVariant.objects.order_by(
            '-id'
            ).first().barcode
        )
    except (ValueError, AttributeError):
        last_barcode = 0

    new_barcode = last_barcode + 1
    while True:
        barcode = f"{(new_barcode):08d}"
        if barcode in existingBarcodes:
            new_barcode += 1
            continue
        try:
            ProductVariant.objects.get(barcode=barcode)
            new_barcode += 1
        except:
            break
    print(f"{(new_barcode):08d}")
    return f"{(new_barcode):08d}"


def check_barcode(barcode):

    from catalog.models import ProductVariant
    
    try:
        ProductVariant.objects.get(barcode=barcode)
        return False
    except:
        return True