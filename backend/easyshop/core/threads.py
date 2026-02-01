
import threading

_thread_locals = threading.local()


# Thread-local tenant context functions
def set_current_tenant(tenant):
    """Set current tenant in thread-local storage."""
    _thread_locals.tenant = tenant

def get_current_tenant():
    """Get current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)


def clear_current_tenant():
    """Clear current tenant from thread-local storage."""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant