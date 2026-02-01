from django.urls import path, include
from rest_framework_nested import routers
from .views import CustomerViewSet, CustomerStatementViewSet

app_name = 'customers'

# Main router
router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'customer-statements', CustomerStatementViewSet, basename='customer-statements')

# Nested routers for customer-related resources
customers_router = routers.NestedSimpleRouter(router, r'customers', lookup='customer')

urlpatterns = [
    # Main customer and group endpoints
    path('', include(router.urls)),
    
    # Nested customer endpoints
    path('', include(customers_router.urls)),
    
    # Additional custom endpoints can be added here if needed
]

"""
Available URL patterns:

Main Customer Endpoints:
- GET /customers/                           - List customers (with pagination, search, filtering)
- POST /customers/                          - Create new customer
- GET /customers/{id}/                      - Get customer details
- PUT /customers/{id}/                      - Update customer
- PATCH /customers/{id}/                    - Partial update customer
- DELETE /customers/{id}/                   - Delete customer (soft delete)

Customer Statistics & Reports:
- GET /customers/statistics/                - Get customer statistics
- GET /customers/over_credit_limit/         - Get customers over credit limit
- GET /customers/inactive_customers/        - Get inactive customers (with days parameter)
- GET /customers/top_customers/             - Get top customers by purchase amount

Customer Actions:
- POST /customers/{id}/update_balance/      - Update customer balance
- GET /customers/{id}/purchase_history/     - Get customer purchase history
- GET /customers/{id}/transaction_history/  - Get customer transaction history

Customer Groups:
- GET /groups/                              - List customer groups
- POST /groups/                             - Create new group
- GET /groups/{id}/                         - Get group details
- PUT /groups/{id}/                         - Update group
- PATCH /groups/{id}/                       - Partial update group
- DELETE /groups/{id}/                      - Delete group

Group Actions:
- POST /groups/{id}/add_customers/          - Add customers to group
- POST /groups/{id}/remove_customers/       - Remove customers from group
- GET /groups/{id}/customers/               - Get customers in group

Customer Contacts:
- GET /customers/{customer_id}/contacts/    - List customer contacts
- POST /customers/{customer_id}/contacts/   - Create new contact
- GET /customers/{customer_id}/contacts/{id}/ - Get contact details
- PUT /customers/{customer_id}/contacts/{id}/ - Update contact
- DELETE /customers/{customer_id}/contacts/{id}/ - Delete contact

Customer Notes:
- GET /customers/{customer_id}/notes/       - List customer notes
- POST /customers/{customer_id}/notes/      - Create new note
- GET /customers/{customer_id}/notes/{id}/  - Get note details
- PUT /customers/{customer_id}/notes/{id}/  - Update note
- DELETE /customers/{customer_id}/notes/{id}/ - Delete note
- GET /customers/{customer_id}/notes/follow_ups/ - Get notes needing follow up

Query Parameters for Filtering:
Customer List:
- name, email, phone, customer_number, company_name (text search)
- customer_type, status, gender (exact match)
- tax_exempt, has_email, has_phone, over_credit_limit (boolean)
- credit_limit_min/max, balance_min/max, discount_percentage_min/max (numeric ranges)
- date_joined_after/before, birth_date_month, anniversary_month (date filters)
- sales_rep, preferred_currency, groups (related fields)
- city, state, country (address filters)
- search (global search), inactive_days (custom filters)
- ordering: name, customer_number, created_at, balance, credit_limit

Customer Group List:
- name, description (text search)
- is_active (boolean)
- discount_percentage_min/max, credit_limit_default_min/max (numeric ranges)
- created_after/before (date filters)
- has_customers, customer_count_min/max (custom filters)
- ordering: name, created_at, discount_percentage

Examples:
- GET /customers/?status=active&customer_type=business&credit_limit_min=1000
- GET /customers/?search=john&has_email=true&ordering=-created_at
- GET /customers/?over_credit_limit=true&status=active
- GET /customers/statistics/
- GET /customers/inactive_customers/?days=90
- GET /groups/?is_active=true&has_customers=true
- POST /customers/123/update_balance/ {"amount": 100.00, "reason": "Payment received"}
"""