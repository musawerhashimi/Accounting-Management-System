> **Project Overview**  
# Complete SaaS Multi-Tenant Business Management Database Schema

## Core Multi-Tenant & System Tables

---

## 📋 Database Tables and Their Fields

1. **tenants**  
   `id`, `name`, `domain`, `contact_email`, `contact_phone`, `business_type`, `status`, `trial_ends_at`, `subscription_plan`, `max_users`, `max_products`, `max_locations`, `max_storage_mb`, `created_at`, `updated_at`, `deleted_at`

2. **tenant_settings**  
   `id`, `tenant_id`, `setting_key`, `setting_value`, `setting_type`, `description`, `created_at`, `updated_at`

3. **tenant_subscriptions**  
   `id`, `tenant_id`, `plan_name`, `price`, `currency_id`, `billing_cycle`, `current_period_start`, `current_period_end`, `status`, `payment_method`, `next_billing_date`, `created_at`, `updated_at`

4. **units**  
   `id`, `tenant_id`, `name`, `abbreviation`, `unit_type`, `base_unit_id`, `conversion_factor`, `is_base_unit`, `created_at`, `updated_at`, `deleted_at`

5. **currencies**  
   `id`, `tenant_id`, `name`, `code`, `symbol`, `decimal_places`, `is_base_currency`, `is_active`, `created_at`, `updated_at`

6. **currency_rates**  
   `id`, `tenant_id`, `currency_id`, `rate`, `effective_date`, `created_at`

7. **departments**  
   `id`, `tenant_id`, `name`, `description`, `is_active`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

8. **categories**  
   `id`, `tenant_id`, `department_id`, `name`, `description`, `is_active`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

9. **attributes**  
   `id`, `tenant_id`, `name`, `attribute_type`, `is_required`, `sort_order`, `is_active`, `created_at`, `updated_at`

10. **attribute_values**  
    `id`, `attribute_id`, `value`, `sort_order`, `is_active`, `created_at`, `updated_at`

11. **products**  
    `id`, `tenant_id`, `name`, `category_id`, `base_unit_id`, `description`, `reorder_level`, `has_variants`, `is_active`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

12. **product_variants**  
    `id`, `product_id`, `sku`, `variant_name`, `image`, `is_default`, `is_active`, `created_at`, `updated_at`, `deleted_at`

13. **product_variant_attributes**  
    `variant_id`, `attribute_value_id`

14. **product_batches**  
    `id`, `tenant_id`, `variant_id`, `batch_number`, `manufacture_date`, `expiry_date`, `supplier_batch_ref`, `notes`, `is_active`, `created_at`, `updated_at`

15. **barcodes**
    `id`, `tenant_id`, `barcode`, `reference_type (batch | variant)`, `variant_id`, `batch_id`, `created_at`

16. **product_prices**  
    `id`, `tenant_id`, `variant_id`, `product_id`, `cost_price`, `cost_currency_id`, `selling_price`, `selling_currency_id`, `effective_date`, `end_date`, `is_current`, `created_by_user_id`, `created_at`

17. **addresses**  
    `id`, `tenant_id`, `addressable_type`, `addressable_id`, `address_type`, `address_line_1`, `address_line_2`, `city`, `state`, `postal_code`, `country`, `is_default`, `created_at`, `updated_at`

18. **locations**  
    `id`, `tenant_id`, `name`, `address_id`, `location_type`, `is_active`, `manager_id`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

19. **inventory**  
    `id`, `tenant_id`, `variant_id`, `batch_id`, `location_id`, `quantity_on_hand`, `reserved_quantity`, `reorder_level`, `last_counted_date`, `created_at`, `updated_at`

20. **stock_movements**  
    `id`, `tenant_id`, `variant_id`, `batch_id`, `location_id`, `movement_type`, `quantity`, `reference_type`, `reference_id`, `notes`, `created_by_user_id`, `created_at`

21. **vendors**  
    `id`, `tenant_id`, `name`, `contact_person`, `phone`, `email`, `credit_limit`, `payment_terms`, `tax_id`, `balance`, `status`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

22. **purchases**  
    `id`, `tenant_id`, `purchase_number`, `vendor_id`, `location_id`, `purchase_date`, `delivery_date`, `subtotal`, `tax_amount`, `total_amount`, `currency_id`, `status`, `notes`, `created_by_user_id`, `created_at`, `updated_at`

23. **purchase_items**  
    `id`, `purchase_id`, `variant_id`, `batch_id`, `quantity`, `unit_cost`, `line_total`, `received_quantity`, `created_at`

24. **customers**  
    `id`, `tenant_id`, `customer_number`, `name`, `gender`, `email`, `phone`, `customer_type`, `credit_limit`, `discount_percentage`, `tax_exempt`, `balance`, `date_joined`, `status`, `notes`, `photo_url`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

25. **sales**  
    `id`, `tenant_id`, `sale_number`, `customer_id`, `location_id`, `sale_date`, `subtotal`, `discount_amount`, `tax_amount`, `total_amount`, `currency_id`, `payment_status`, `status`, `notes`, `created_by_user_id`, `created_at`, `updated_at`

26. **sale_items**  
    `id`, `sale_id`, `variant_id`, `batch_id`, `quantity`, `unit_price`, `line_total`, `discount_amount`, `created_at`

27. **returns**  
    `id`, `tenant_id`, `return_number`, `original_sale_id`, `customer_id`, `return_date`, `reason`, `total_refund_amount`, `currency_id`, `status`, `processed_by_user_id`, `created_at`, `updated_at`

28. **return_items**  
    `id`, `return_id`, `sale_item_id`, `variant_id`, `batch_id`, `quantity_returned`, `condition`, `refund_amount`, `restocked`, `created_at`

29. **cash_drawers**  
    `id`, `tenant_id`, `name`, `location_id`, `is_active`, `created_by_user_id`, `created_at`, `updated_at`

30. **cash_drawer_money**  
    `id`, `cash_drawer_id`, `currency_id`, `amount`, `last_counted_date`, `created_at`, `updated_at`

31. **payments**  
    `id`, `tenant_id`, `payment_number`, `amount`, `currency_id`, `payment_method`, `payment_date`, `reference_type`, `reference_id`, `cash_drawer_id`, `card_transaction_id`, `notes`, `processed_by_user_id`, `created_at`

32. **transactions**  
    `id`, `tenant_id`, `transaction_date`, `amount`, `currency_id`, `description`, `party_type`, `party_id`, `transaction_type`, `reference_type`, `reference_id`, `cash_drawer_id`, `created_by_user_id`, `created_at`

33. **expense_categories**  
    `id`, `tenant_id`, `name`, `description`, `parent_category_id`, `is_active`, `created_at`, `updated_at`

34. **expenses**  
    `id`, `tenant_id`, `expense_number`, `expense_category_id`, `vendor_id`, `amount`, `currency_id`, `expense_date`, `description`, `receipt_reference`, `payment_method`, `status`, `approved_by_user_id`, `created_by_user_id`, `created_at`, `updated_at`

35. **monthly_payments**  
    `id`, `tenant_id`, `name`, `amount`, `currency_id`, `payment_method`, `start_date`, `end_date`, `payment_day`, `expense_category_id`, `vendor_id`, `is_active`, `description`, `created_at`, `updated_at`

36. **employees**  
    `id`, `tenant_id`, `employee_number`, `name`, `phone`, `email`, `hire_date`, `status`, `balance`, `created_by_user_id`, `created_at`, `updated_at`, `deleted_at`

37. **employee_positions**  
    `id`, `tenant_id`, `position_name`, `department_id`, `base_salary`, `currency_id`, `description`, `is_active`, `created_at`, `updated_at`

38. **employee_careers**  
    `id`, `employee_id`, `position_id`, `start_date`, `end_date`, `salary`, `currency_id`, `status`, `notes`, `created_by_user_id`, `created_at`, `updated_at`

39. **members**  
    `id`, `tenant_id`, `name`, `ownership_percentage`, `investment_amount`, `currency_id`, `start_date`, `end_date`, `balance`, `profit_share`, `asset_share`, `status`, `created_at`, `updated_at`

40. **inventory_adjustments**  
    `id`, `tenant_id`, `adjustment_number`, `variant_id`, `batch_id`, `location_id`, `adjustment_quantity`, `reason`, `cost_impact`, `currency_id`, `notes`, `approved_by_user_id`, `created_by_user_id`, `adjustment_date`, `created_at`

41. **inventory_counts**  
    `id`, `tenant_id`, `count_number`, `location_id`, `count_date`, `status`, `total_items_counted`, `variances_found`, `created_by_user_id`, `completed_by_user_id`, `created_at`, `updated_at`

42. **inventory_count_items**  
    `id`, `count_id`, `variant_id`, `batch_id`, `system_quantity`, `counted_quantity`, `variance`, `notes`, `counted_by_user_id`, `created_at`

43. **users** (extends Django’s `AbstractUser`)  
    `id`, `username`, `email`, `password`, `first_name`, `last_name`, `tenant_id`, `employee_id`, `is_active`, `last_login_date`, `preferred_currency_id`, `language_preference`, `timezone`, `date_joined`, `updated_at`, `deleted_at`

44. **permissions**  
    `id`, `action`, `description`, `module`, `created_at`

45. **user_roles**  
    `id`, `tenant_id`, `user_id`, `role_name`, `assigned_by_user_id`, `assigned_date`, `is_active`, `created_at`, `updated_at`

46. **role_permissions**  
    `id`, `role_name`, `permission_id`

46. **user_permissions**
    `id`, `user_id`, `permission_id`, `allow (boolean)`, `created_at`

47. **user_product_preferences**  
    `user_id`, `product_id`, `tenant_id`, `is_favorite`, `is_bookmarked`, `last_viewed_at`, `view_count`, `created_at`

48. **activity_logs**  
    `id`, `tenant_id`, `user_id`, `action`, `table_name`, `record_id`, `old_values`, `new_values`, `ip_address`, `user_agent`, `session_id`, `timestamp`, `created_at`

49. **system_settings**  
    `id`, `tenant_id`, `setting_key`, `setting_value`, `setting_type`, `description`, `category`, `updated_by_user_id`, `updated_at`, `created_at`

---

# Working with Django and DRF to build an API

## 🚀 Django Apps & Models

- **core**  
  `Tenants`, `TenantSettings`, `TenantSubscriptions`, `Units`, `Currencies`, `CurrencyRates`, `Addresses`, `SystemSettings`, `Permissions`, `ActivityLogs`

- **accounts**  
  `Users`, `UserRoles`, `RolePermissions`, `UserPermissions`, `UserProductPreferences`

- **catalog**  
  `Departments`, `Categories`, `Attributes`, `AttributeValues`, `Products`, `ProductVariants`, `ProductVariantAttributes`, `ProductPrices`, `barcodes`

- **inventory**  
  `Locations`, `ProductBatches`, `Inventory`, `StockMovements`, `InventoryAdjustments`, `InventoryCounts`, `InventoryCountItems`

- **vendors**  
  `Vendors`, `Purchases`, `PurchaseItems`

- **customers**  
  `Customers`

- **sales**  
  `Sales`, `SaleItems`, `Returns`, `ReturnItems`

- **finance**  
  `CashDrawers`, `CashDrawerMoney`, `Payments`, `Transactions`, `Expenses`, `ExpenseCategories`, `MonthlyPayments`

- **hr**  
  `Employees`, `EmployeePositions`, `EmployeeCareers`, `Members`

---


for authentication i have these class and decorators in core/permissions.py file.

* **IsTenantUser**: lets only authenticated users (or superusers) access tenant data and ensures `request.tenant` matches `request.user.tenant`.

* **HasModulePermission**: reads `view.permission_module` & `view.permission_action` (or maps HTTP verbs to CRUD), and checks it against the user’s role‑permissions and user-permissions.
* **IsTenantOwnerOrAdmin**: allows superusers or users whose roles include “owner”, “admin”, or “manager” for that tenant.
* **IsSystemAdmin**: only allows Django superusers.
* **CanAccessTenantSettings**: lets any tenant user read settings; only admins (via roles) or superusers can modify.
* **TenantPermissionMixin**: auto‑applies `IsTenantUser` (plus `HasModulePermission` if `permission_module` is set), filters querysets by `tenant_id`, and injects `tenant_id` on create.
* **@tenant_required**: decorator for function views that blocks non‑tenant or unauthenticated users.
* **@permission_required(codename)**: decorator that raises `PermissionDenied` unless the user’s roles include that codename (or is superuser).

---

and a middleware.py file in core app
> **Middleware Overview**  
> Handles per‐request tenant resolution and automatic activity logging using Django’s `MiddlewareMixin`, thread‑local storage, and the `ActivityLog` model.

---

- **TenantMiddleware**  
  - **process_request**: reads `X-Tenant-ID` header or request domain to fetch an active `Tenant`; sets `request.tenant` and thread‑local via `set_current_tenant()`.  
  - **process_response**: calls `clear_current_tenant()` to wipe the thread‑local tenant.

- **ActivityLogMiddleware**  
  - **process_request**: stamps `request._activity_log_start_time = timezone.now()`.  
  - **process_response**: if method in `['POST','PUT','PATCH','DELETE']`, status < 400, and path not in `IGNORED_PATHS`, calls `_log_activity()`.  
    - **_log_activity**: maps HTTP verb to action (`create`, `update`, `delete`), parses `object_type` & `object_id` from URL segments, grabs client IP, and creates an `ActivityLog` entry (silent on errors).

- **Thread‑local tenant helpers**  
  - `set_current_tenant(tenant)`, `get_current_tenant()`, `clear_current_tenant()` store/clear the current tenant in module‐level thread‑local.

and for base models i have these models in core/base_models.py (you can use them if needed):

> **Base Models & Managers Summary**

- **SoftDeleteManager**  
  Overrides `get_queryset()` to exclude objects where `deleted_at` is set (soft-deleted).

- **TenantManager**  
  Like `SoftDeleteManager`, but filters by tenant ID from `get_current_tenant()` if the model has `tenant` field.

- **BaseModel**  
  Abstract model with `created_at`, `updated_at`, and `deleted_at` fields.  
  - Default manager: hides soft-deleted records.  
  - Methods: `soft_delete()` and `restore()`.

- **TenantBaseModel**  
  Extends `BaseModel` with a `tenant` FK field.  
  - Uses `TenantManager` as default to apply both tenant and soft-delete filtering.



This is my project, and there is always a default variant to the product. i have generated models and other things as needed.
now i want you to handle for me the sale flow, different status, PROPER UPDATE LOGIC,
payments ....


if you have any question ask.