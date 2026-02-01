from core.models import Tenant, TenantSettings, Currency
from accounts.models import User

email = "suhailsammim1@gmail.com"
name="Suhail"
domain = None
currency_name = "United States Dollar"
currency_code = "USD"
currency_symbol = "$"


currency_name = currency_name or currency_code
domain = domain or name.lower()

tenant = Tenant.objects.create(
  name=name,
  domain=domain,
  contact_email=email,
  business_type="wholesale",
  status="active",
  subscription_plan="enterprise"
)

user = User.objects.create(
  tenant=tenant,
  username="suhail",
  email=email,
  first_name="Suhail",
  last_name="Sirat",
)

default_settings = [
    # {
    #     'setting_key': 'company_name',
    #     'setting_value': 'My Business',
    #     'setting_type': 'string',
    #     'category': 'general',
    #     'description': 'Company name displayed in the system'
    # },
    {
        'setting_key': 'base_currency_id',
        'setting_value': '1',
        'setting_type': 'integer',
        'category': 'finance',
        'description': 'Base currency for financial calculations'
    },
    {
        'setting_key': 'low_stock_threshold',
        'setting_value': '10',
        'setting_type': 'integer',
        'category': 'inventory',
        'description': 'Default low stock threshold for products'
    },
    {
        'setting_key': 'tax_rate',
        'setting_value': '0.00',
        'setting_type': 'decimal',
        'category': 'finance',
        'description': 'Default tax rate percentage'
    },
    {
        'setting_key': 'enable_multi_location',
        'setting_value': 'false',
        'setting_type': 'boolean',
        'category': 'inventory',
        'description': 'Enable multi-location inventory management'
    }
]
        
for setting_data in default_settings:
    if not TenantSettings.objects.filter(tenant=tenant,setting_key=setting_data['setting_key']).exists():
        TenantSettings.objects.create(
            tenant=tenant,
            # updated_by_user=user,
            **setting_data
        )

TenantSettings.objects.create(
  tenant=tenant,
  setting_key="system_initialized",
  
)

currency = Currency.objects.create(
  tenant=tenant,
  name=currency_name,
  code=currency_code,
  symbol=currency_symbol,
  is_base_currency=True
)

MODULES = [
  'users',
  'products',
  'inventory',
  'sales',
  'purchases',
  'customers',
  'vendors',
  'finance',
  'reports',
  'settings',
]
ACTIONS = [
  'add',
  'view',
  'change',
  'delete'
]

from core.models import Permission

for module in MODULES:
  for action in ACTIONS:
    Permission.objects.create(
      action=action,
      module=module,
    )

ROLES = [
    'owner',
    'admin',
    'manager',
    'employee',
    'cashier',
    'inventory_manager',
    'sales_rep',
    'accountant',
    'viewer',
    'custom',
]

PERMISSION_PER_ROLE = {
  'owner': [i for i in range(1, 41)],
  'admin': [i for i in range(1, 41)],
  'manager': [i for i in range(5, 41)],
  'employee': [i for i in range(13, 21)],
  'cashier': [29, 30, 31, 32],
  'inventory_manager': [9, 10, 11, 12],
  'sales_rep': [13, 14, 15, 16],
  'accountant': [21, 22, 23, 24],
  'viewer': [i for i in range(2, 40, 4)],
  'custom': [],
}

from accounts.models import RolePermission
for role_name, permissoin_ids in PERMISSION_PER_ROLE.items():
  for permission_id in permissoin_ids:
    RolePermission.objects.create(
      role_name=role_name,
      permission_id=permission_id
    )
    
from accounts.models import User, UserRole
user = User.objects.get(id=1)
tenant = Tenant.objects.get(id=1)
UserRole.objects.create(
  tenant=tenant,
  role_name="admin",
  user=user,
  assigned_by_user=user
)