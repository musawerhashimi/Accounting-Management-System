
from vendors.utils import upload_image_path
def upload_user_photo(instance, filename):
    """Generate upload path for user profile photos"""
    return upload_image_path(
        instance=instance,
        filename=filename,
        folder_name='users',
        instance_field_name='first_name',
    )
    