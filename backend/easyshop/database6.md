# Complete SaaS Multi-Tenant Business Management Database Schema

## Core Multi-Tenant & System Tables

### 1. tenants
**Purpose**: Master table for all business accounts in the SaaS platform
```sql
id                     -- Primary key
name                  -- Business name ("Ahmed Electronics", "City Pharmacy")
domain                -- Custom subdomain (ahmed-electronics.yoursaas.com)
contact_email         -- Primary contact email
contact_phone         -- Primary contact phone
business_type         -- ENUM: 'retail', 'wholesale', 'pharmacy', 'restaurant', 'service'
status               -- ENUM: 'active', 'suspended', 'trial', 'cancelled'
trial_ends_at        -- When trial expires (NULL if not trial)
subscription_plan    -- ENUM: 'basic', 'standard', 'premium', 'enterprise'
max_users           -- Maximum users allowed
max_products        -- Maximum products allowed
max_locations       -- Maximum locations allowed
max_storage_mb      -- Storage limit in MB
created_at
updated_at
deleted_at
```
**Examples**: 
- id=1, name="Ahmed Electronics", domain="ahmed-electronics", status="active", subscription_plan="premium"
- id=2, name="City Pharmacy", domain="city-pharmacy", status="trial", max_users=5

### 2. tenant_settings
**Purpose**: Feature flags and configuration per tenant
```sql
id                     -- Primary key
tenant_id             -- FK to tenants
setting_key           -- Setting identifier
setting_value         -- Setting value (JSON for complex values)
setting_type          -- ENUM: 'boolean', 'string', 'number', 'json'
description           -- What this setting controls
created_at
updated_at
-- UNIQUE constraint on (tenant_id, setting_key)
```
**Key Settings Examples**:
- tenant_id=1, setting_key="enable_variants", setting_value="true", setting_type="boolean"
- tenant_id=1, setting_key="enable_expiry_tracking", setting_value="false", setting_type="boolean"
- tenant_id=2, setting_key="enable_expiry_tracking", setting_value="true", setting_type="boolean"
- tenant_id=1, setting_key="default_tax_rate", setting_value="0.05", setting_type="number"

### 3. tenant_subscriptions
**Purpose**: Subscription and billing tracking
```sql
id                     -- Primary key
tenant_id             -- FK to tenants
plan_name             -- Current plan name
price                 -- Monthly/yearly price
currency_id           -- Price currency
billing_cycle         -- ENUM: 'monthly', 'yearly'
current_period_start  -- Billing period start
current_period_end    -- Billing period end
status               -- ENUM: 'active', 'past_due', 'cancelled', 'unpaid'
payment_method       -- ENUM: 'card', 'bank_transfer', 'cash'
next_billing_date    -- When next payment is due
created_at
updated_at
```

## Core System Tables (Tenant-Aware)

### 4. units
**Purpose**: Measurement units (pieces, kg, liters, etc.) - tenant-specific
```sql
id                    -- Primary key
tenant_id            -- FK to tenants (each tenant has their own units)
name                 -- Unit name (e.g., "Piece", "Kilogram", "Liter")
abbreviation         -- Short form (e.g., "pcs", "kg", "L")
unit_type            -- ENUM: 'weight', 'volume', 'length', 'count', 'area'
base_unit_id         -- Links to base unit for conversions (NULL if this IS the base)
conversion_factor    -- How many base units = 1 of this unit
is_base_unit         -- Is this the primary unit for its type?
created_at
updated_at
deleted_at
-- INDEX on (tenant_id)
```

### 5. currencies
**Purpose**: All currencies used by tenants
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Currency name
code                 -- ISO code (USD, EUR, CNY, AED, etc.)
symbol               -- Currency symbol ($, €, ¥, د.إ, etc.)
decimal_places       -- How many decimal places
is_base_currency     -- Is this tenant's base currency?
is_active            -- Still in use?
created_at
updated_at
-- INDEX on (tenant_id)
-- UNIQUE constraint on (tenant_id, code)
```

### 6. currency_rates
**Purpose**: Exchange rates to base currency per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
currency_id          -- FK to currencies
rate                 -- Exchange rate to tenant's base currency
effective_date       -- Date this rate applies from
created_at
-- INDEX on (tenant_id, currency_id, effective_date)
```

## Product Catalog with Variants

### 7. departments
**Purpose**: Main business categories per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Department name
description          -- Optional description
is_active            -- Whether department is currently in use
created_by_user_id   -- Who created this department
created_at
updated_at
deleted_at
-- INDEX on (tenant_id)
```

### 8. categories
**Purpose**: Sub-categories within departments per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
department_id        -- FK to departments
name                 -- Category name
description          -- Optional description
is_active            -- Active status
created_by_user_id   -- Who created this category
created_at
updated_at
deleted_at
-- INDEX on (tenant_id, department_id)
-- FK constraint: categories.department_id → departments.id WHERE departments.tenant_id = categories.tenant_id
```

### 9. attributes
**Purpose**: Product variant attributes (Color, Size, etc.) per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Attribute name (e.g., "Color", "Size", "Material")
attribute_type       -- ENUM: 'text', 'number', 'select', 'multi_select'
is_required          -- Must variants have this attribute?
sort_order           -- Display order
is_active            -- Still using this attribute?
created_at
updated_at
-- INDEX on (tenant_id)
```
**Examples**:
- tenant_id=1, name="Color", attribute_type="select", is_required=true
- tenant_id=1, name="Size", attribute_type="select", is_required=false

### 10. attribute_values
**Purpose**: Possible values for each attribute
```sql
id                    -- Primary key
attribute_id         -- FK to attributes
value                -- The actual value (e.g., "Red", "Large", "Cotton")
sort_order           -- Display order
is_active            -- Still available?
created_at
updated_at
-- INDEX on (attribute_id)
```
**Examples**:
- attribute_id=1(Color), value="Red", sort_order=1
- attribute_id=1(Color), value="Blue", sort_order=2
- attribute_id=2(Size), value="Small", sort_order=1

### 11. products
**Purpose**: Master product templates (parent products) per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Product name (e.g., "Nike Air Max 90")
category_id          -- FK to categories
base_unit_id         -- Default measurement unit
description          -- Product details
base_cost_price      -- Base cost price (variants can modify)
base_selling_price   -- Base selling price (variants can modify)
cost_currency_id     -- Currency for cost price
selling_currency_id  -- Currency for selling price
reorder_level        -- Minimum stock before reordering
image                -- Product image path/URL
has_variants         -- Does this product have variants?
is_active            -- Whether product is still sold
created_by_user_id   -- Who added this product
created_at
updated_at
deleted_at
-- INDEX on (tenant_id, category_id)
-- FK constraint: products.category_id → categories.id WHERE categories.tenant_id = products.tenant_id
```
**Examples**:
- id=1, tenant_id=1, name="T-Shirt Basic", has_variants=true, base_cost_price=50, base_selling_price=100
- id=2, tenant_id=1, name="iPhone Cable", has_variants=false, base_cost_price=20, base_selling_price=50

### 12. product_variants
**Purpose**: Individual SKUs/variations of products
```sql
id                    -- Primary key
product_id           -- FK to products (parent product)
sku                  -- Unique SKU for this variant
barcode              -- Unique barcode for this variant
variant_name         -- Generated name (e.g., "T-Shirt Basic - Red - Large")
cost_price_modifier  -- Amount to add/subtract from base cost (+10, -5, NULL for same)
selling_price_modifier -- Amount to add/subtract from base selling price
final_cost_price     -- Calculated: base_cost_price + cost_price_modifier
final_selling_price  -- Calculated: base_selling_price + selling_price_modifier
weight               -- Variant-specific weight
dimensions           -- Variant-specific dimensions (JSON: {length, width, height})
image                -- Variant-specific image (overrides product image)
is_default           -- Is this the default/main variant?
is_active            -- Is this variant still available?
created_at
updated_at
deleted_at
-- INDEX on (product_id, sku)
-- INDEX on (barcode) -- Global barcode uniqueness
```
**Examples**:
- id=1, product_id=1, sku="TSHIRT-RED-L", variant_name="T-Shirt Basic - Red - Large", cost_price_modifier=0, selling_price_modifier=0
- id=2, product_id=1, sku="TSHIRT-BLUE-S", variant_name="T-Shirt Basic - Blue - Small", cost_price_modifier=-5, selling_price_modifier=-10

### 13. product_variant_attributes
**Purpose**: Links variants to their attribute values (many-to-many)
```sql
variant_id           -- FK to product_variants
attribute_value_id   -- FK to attribute_values
-- PRIMARY KEY (variant_id, attribute_value_id)
-- INDEX on (variant_id)
```
**Examples**:
- variant_id=1, attribute_value_id=1 (Red)
- variant_id=1, attribute_value_id=4 (Large)
- variant_id=2, attribute_value_id=2 (Blue)
- variant_id=2, attribute_value_id=3 (Small)

### 14. product_batches
**Purpose**: Batch/lot tracking for expiry dates and FEFO
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
variant_id           -- FK to product_variants (what product/variant)
batch_number         -- Unique batch identifier
manufacture_date     -- When produced
expiry_date          -- When expires (NULL if no expiry)
supplier_batch_ref   -- Supplier's batch reference
notes                -- Additional batch information
is_active            -- Is this batch still sellable?
created_at
updated_at
-- INDEX on (tenant_id, variant_id, expiry_date)
-- INDEX on (batch_number, tenant_id) -- Unique within tenant
```
**Examples**:
- id=1, tenant_id=2, variant_id=5(Medicine-A), batch_number="BATCH-001", expiry_date="2025-12-31"
- id=2, tenant_id=1, variant_id=1(T-Shirt), batch_number=NULL, expiry_date=NULL (no expiry)

### 15. product_prices
**Purpose**: Historical pricing for products/variants
```sql
id                   -- Primary key
tenant_id           -- FK to tenants
variant_id          -- FK to product_variants (NULL if for base product)
product_id          -- FK to products (for non-variant products)
cost_price          -- Purchase cost at this time
cost_currency_id    -- Cost price currency
selling_price       -- Selling price at this time
selling_currency_id -- Selling price currency
effective_date      -- When this price started
end_date           -- When this price ended (NULL for current)
is_current         -- Is this the currently active price?
created_by_user_id  -- Who changed the price
created_at
-- INDEX on (tenant_id, variant_id, is_current)
-- INDEX on (tenant_id, product_id, is_current)
```

## Location & Inventory Management

### 16. addresses
**Purpose**: Flexible address storage for all entities per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
addressable_type     -- What type: 'customer', 'vendor', 'location'
addressable_id       -- ID of the customer/vendor/location
address_type         -- ENUM: 'billing', 'shipping', 'primary'
address_line_1       -- Street address
address_line_2       -- Apartment, suite, etc.
city                -- City name
state               -- State/province
postal_code         -- ZIP/postal code
country             -- Country name
is_default          -- Is this the main address?
created_at
updated_at
-- INDEX on (tenant_id, addressable_type, addressable_id)
```

### 17. locations
**Purpose**: Physical places where inventory is stored per tenant
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Location name
address_id        -- FK to addresses
location_type     -- ENUM: 'warehouse', 'store', 'supplier'
is_active         -- Whether location is operational
manager_id        -- FK to employees who manages this location
created_by_user_id -- Who created this location
created_at
updated_at
deleted_at
-- INDEX on (tenant_id)
-- FK constraint: locations.address_id → addresses.id WHERE addresses.tenant_id = locations.tenant_id
```

### 18. inventory
**Purpose**: Current stock levels with batch tracking
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
variant_id           -- FK to product_variants (what specific variant)
batch_id             -- FK to product_batches (NULL if no batch tracking)
location_id          -- FK to locations (where stored)
quantity_on_hand     -- Current stock count
reserved_quantity    -- Stock reserved for pending orders
reorder_level        -- Minimum before reordering (location-specific)
last_counted_date    -- When physical count was last done
created_at
updated_at
-- INDEX on (tenant_id, variant_id, location_id)
-- INDEX on (tenant_id, batch_id) WHERE batch_id IS NOT NULL
-- UNIQUE constraint on (tenant_id, variant_id, batch_id, location_id) -- One record per variant-batch-location combo
```
**Examples**:
- tenant_id=1, variant_id=1(T-Shirt Red-L), batch_id=NULL, location_id=1(Main Store), quantity_on_hand=25
- tenant_id=2, variant_id=5(Medicine-A), batch_id=1(BATCH-001), location_id=2(Pharmacy), quantity_on_hand=100

### 19. stock_movements
**Purpose**: Complete audit trail of all inventory changes
```sql
id                   -- Primary key
tenant_id           -- FK to tenants
variant_id          -- FK to product_variants
batch_id            -- FK to product_batches (NULL if no batch)
location_id         -- FK to locations
movement_type       -- ENUM: 'in', 'out', 'transfer', 'adjustment'
quantity            -- How many moved (positive or negative)
reference_type      -- What caused this: 'purchase', 'sale', 'adjustment', 'transfer'
reference_id        -- ID of the purchase/sale/adjustment record
notes              -- Optional explanation
created_by_user_id -- Who made this movement
created_at
-- INDEX on (tenant_id, variant_id)
-- INDEX on (tenant_id, reference_type, reference_id)
```

## Supplier & Purchase Management

### 20. vendors
**Purpose**: Companies/people we buy products from per tenant
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Vendor company name
contact_person    -- Main contact name
phone             -- Phone number
email             -- Email address
credit_limit      -- Maximum we can owe them
payment_terms     -- How many days to pay (30, 60, etc.)
tax_id            -- Their tax identification
balance           -- Current amount we owe them (auto-calculated)
status            -- ENUM: 'active', 'inactive', 'blocked'
created_by_user_id -- Who added this vendor
created_at
updated_at
deleted_at
-- INDEX on (tenant_id)
```

### 21. purchases
**Purpose**: Purchase orders/invoices from vendors per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
purchase_number      -- Our internal PO number
vendor_id           -- FK to vendors
location_id         -- FK to locations (which location receives goods)
purchase_date       -- When we ordered
delivery_date       -- When we received
subtotal           -- Cost before any taxes/duties
tax_amount         -- Any import duties or taxes
total_amount       -- Total purchase cost
currency_id        -- FK to currencies
status             -- ENUM: 'pending', 'received', 'cancelled'
notes              -- Additional information
created_by_user_id -- Who created this purchase
created_at
updated_at
-- INDEX on (tenant_id, vendor_id)
-- FK constraints ensure vendor and location belong to same tenant
```

### 22. purchase_items
**Purpose**: Individual products within each purchase
```sql
id                 -- Primary key
purchase_id       -- FK to purchases
variant_id        -- FK to product_variants (specific variant ordered)
batch_id          -- FK to product_batches (created when received)
quantity          -- How many ordered
unit_cost         -- Price per unit
line_total        -- quantity × unit_cost
received_quantity -- How many actually arrived
created_at
-- INDEX on (purchase_id, variant_id)
```

## Customer Management

### 23. customers
**Purpose**: People/companies who buy from us per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
customer_number      -- Unique customer ID within tenant
name                -- Customer name
gender              -- Optional: 'male', 'female', 'other'
email               -- Email address
phone               -- Phone number
customer_type       -- ENUM: 'individual', 'business', 'vip'
credit_limit        -- Maximum they can owe us
discount_percentage -- Default discount they get
tax_exempt          -- Do they pay tax? (boolean)
balance             -- Current amount they owe us (auto-calculated)
date_joined         -- When they became customer
status              -- ENUM: 'active', 'inactive', 'blocked'
notes              -- Additional information
photo_url           -- Customer photo path
created_by_user_id  -- Who added this customer
created_at
updated_at
deleted_at
-- INDEX on (tenant_id, customer_number)
-- UNIQUE constraint on (tenant_id, customer_number)
```

## Sales Management

### 24. sales
**Purpose**: Individual sales transactions per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
sale_number          -- Receipt/invoice number (unique within tenant)
customer_id          -- FK to customers (NULL for walk-in)
location_id          -- FK to locations (which store made sale)
sale_date           -- When sale happened
subtotal            -- Total before discount/tax
discount_amount     -- Total discount given
tax_amount          -- Tax charged
total_amount        -- Final amount customer pays
currency_id         -- FK to currencies
payment_status      -- ENUM: 'paid', 'partial', 'pending'
status              -- ENUM: 'draft', 'completed', 'cancelled', 'refunded'
notes              -- Special instructions
created_by_user_id  -- Which employee made the sale
created_at
updated_at
-- INDEX on (tenant_id, customer_id)
-- INDEX on (tenant_id, sale_date)
```

### 25. sale_items
**Purpose**: Products sold in each sale
```sql
id                 -- Primary key
sale_id           -- FK to sales
variant_id        -- FK to product_variants (specific variant sold)
batch_id          -- FK to product_batches (which batch was used, NULL if no tracking)
quantity          -- How many sold
unit_price        -- Price per unit (at time of sale)
line_total        -- quantity × unit_price
discount_amount   -- Discount on this line item
created_at
-- INDEX on (sale_id, variant_id)
```

### 26. returns
**Purpose**: When customers return products per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
return_number        -- Unique return ID within tenant
original_sale_id     -- FK to sales (which sale is being returned)
customer_id          -- FK to customers (who is returning)
return_date         -- When return happened
reason              -- Why returning: 'defective', 'unwanted', etc.
total_refund_amount -- How much money refunded
currency_id         -- FK to currencies
status              -- ENUM: 'pending', 'approved', 'completed'
processed_by_user_id -- Who handled the return
created_at
updated_at
-- INDEX on (tenant_id, original_sale_id)
```

### 27. return_items
**Purpose**: Specific products being returned
```sql
id                    -- Primary key
return_id            -- FK to returns
sale_item_id         -- FK to sale_items (original item being returned)
variant_id           -- FK to product_variants
batch_id             -- FK to product_batches (which batch returned)
quantity_returned    -- How many being returned
condition           -- ENUM: 'new', 'used', 'damaged'
refund_amount       -- Money refunded for this item
restocked           -- Put back in inventory? (boolean)
created_at
-- INDEX on (return_id, sale_item_id)
```

## Financial Management

### 28. cash_drawers
**Purpose**: Physical cash registers/tills per tenant
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Drawer name ("Main Register", "Counter 2")
location_id       -- FK to locations
is_active         -- Currently in use?
created_by_user_id -- Who set up this register
created_at
updated_at
-- INDEX on (tenant_id, location_id)
```

### 29. cash_drawer_money
**Purpose**: How much cash is in each drawer, by currency
```sql
id                 -- Primary key
cash_drawer_id    -- FK to cash_drawers
currency_id       -- FK to currencies
amount            -- Current amount (calculated from transactions)
last_counted_date -- When last physically counted
created_at
updated_at
-- UNIQUE constraint on (cash_drawer_id, currency_id)
```

### 30. payments
**Purpose**: All money received from customers per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
payment_number       -- Unique payment reference within tenant
amount              -- Payment amount
currency_id         -- FK to currencies
payment_method      -- ENUM: 'cash', 'card', 'bank_transfer', 'check'
payment_date        -- When payment received
reference_type      -- What was paid: 'sale', 'account_payment'
reference_id        -- ID of sale or customer account
cash_drawer_id      -- FK to cash_drawers (where cash deposited)
card_transaction_id -- Bank transaction reference
notes              -- Additional details
processed_by_user_id -- Who processed payment
created_at
-- INDEX on (tenant_id, reference_type, reference_id)
```

### 31. transactions
**Purpose**: Complete financial audit trail per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
transaction_date     -- When transaction occurred
amount              -- Transaction amount (positive or negative)
currency_id         -- FK to currencies
description         -- What happened
party_type          -- Who: 'customer', 'vendor', 'employee', 'expense'
party_id            -- ID of the customer/vendor/employee
transaction_type    -- ENUM: 'sale_payment', 'purchase_payment', 'expense', 'withdrawal', 'deposit'
reference_type      -- Source document: 'sale', 'purchase', 'payment', 'expense'
reference_id        -- ID of the source document
cash_drawer_id      -- FK to cash_drawers (affected drawer)
created_by_user_id  -- Who created this transaction
created_at
-- INDEX on (tenant_id, transaction_date)
-- INDEX on (tenant_id, party_type, party_id)
```

### 32. expense_categories
**Purpose**: Organize business expenses per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Category name
description          -- What expenses go here
parent_category_id   -- FK to self (for subcategories)
is_active           -- Still using this category?
created_at
updated_at
-- INDEX on (tenant_id, parent_category_id)
```

### 33. expenses
**Purpose**: All business expenses per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
expense_number       -- Unique expense reference within tenant
expense_category_id  -- FK to expense_categories
vendor_id           -- FK to vendors (if vendor expense)
amount              -- Expense amount
currency_id         -- FK to currencies
expense_date        -- When expense occurred
description         -- What was purchased/paid for
receipt_reference   -- Receipt number or reference
payment_method      -- How was it paid
status              -- ENUM: 'pending', 'approved', 'paid'
approved_by_user_id -- Who approved this expense
created_by_user_id  -- Who recorded this expense
created_at
updated_at
-- INDEX on (tenant_id, expense_category_id)
```

### 34. monthly_payments
**Purpose**: Recurring expenses per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Payment name ("Office Rent", "Internet Bill")
amount              -- Monthly amount
currency_id         -- FK to currencies
payment_method      -- How it's paid
start_date          -- When recurring payments started
end_date            -- When they end (NULL if ongoing)
payment_day         -- Which day of month (1-31)
expense_category_id -- FK to expense_categories
vendor_id          -- FK to vendors (who receives payment)
is_active          -- Still active?
description        -- Additional details
created_at
updated_at
-- INDEX on (tenant_id, payment_day)
```

## Human Resources

### 35. employees
**Purpose**: Staff members per tenant
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
employee_number   -- Unique employee ID within tenant (E001, E002)
name             -- Full name
phone            -- Phone number
email            -- Email address
hire_date        -- When they started
status           -- ENUM: 'active', 'inactive', 'terminated'
balance          -- Money owed to/by employee (auto-calculated)
created_by_user_id -- Who added this employee record
created_at
updated_at
deleted_at
-- INDEX on (tenant_id, employee_number)
-- UNIQUE constraint on (tenant_id, employee_number)
```

### 36. employee_positions
**Purpose**: Job roles per tenant
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
position_name     -- Job title
department_id     -- FK to departments
base_salary       -- Standard salary for this position
currency_id       -- FK to currencies
description       -- Job responsibilities
is_active         -- Still hiring for this position?
created_at
updated_at
-- INDEX on (tenant_id, department_id)
```

### 37. employee_careers
**Purpose**: Track employee job history per tenant
```sql
id                    -- Primary key
employee_id          -- FK to employees
position_id          -- FK to employee_positions
start_date          -- When they started this role
end_date            -- When role ended (NULL if current)
salary              -- Salary for this role
currency_id         -- FK to currencies
status              -- ENUM: 'active', 'ended'
notes              -- Performance notes, reason for change
created_by_user_id  -- Who recorded this job change
created_at
updated_at
-- INDEX on (employee_id, start_date)
```

## Business Partnership

### 38. members
**Purpose**: Business partners/investors per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Partner name
ownership_percentage -- What % of business they own
investment_amount   -- How much money they invested
currency_id         -- FK to currencies
start_date         -- When partnership started
end_date           -- When partnership ended (NULL if active)
balance            -- Current account balance (auto-calculated)
profit_share       -- Accumulated profits owed to them
asset_share        -- Their share of business assets
status             -- ENUM: 'active', 'inactive', 'withdrawn'
created_at
updated_at
-- INDEX on (tenant_id)
```

## Advanced Inventory Management

### 39. inventory_adjustments
**Purpose**: Manual corrections to inventory per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
adjustment_number    -- Unique reference within tenant
variant_id          -- FK to product_variants
batch_id            -- FK to product_batches (NULL if no batch tracking)
location_id         -- FK to locations
adjustment_quantity -- How many added/removed (+ or -)
reason              -- ENUM: 'damaged', 'theft', 'count_correction', 'expired'
cost_impact         -- Financial impact of adjustment
currency_id         -- FK to currencies
notes              -- Detailed explanation
approved_by_user_id -- Who approved this adjustment
created_by_user_id  -- Who made the adjustment
adjustment_date     -- When adjustment happened
created_at
-- INDEX on (tenant_id, variant_id)
```

### 40. inventory_counts
**Purpose**: Physical inventory counting sessions per tenant
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
count_number         -- Unique count reference within tenant
location_id         -- FK to locations
count_date          -- When counting happened
status              -- ENUM: 'in_progress', 'completed', 'cancelled'
total_items_counted -- How many different products counted
variances_found     -- How many products had differences
created_by_user_id  -- Who organized the count
completed_by_user_id -- Who finished the count
created_at
updated_at
-- INDEX on (tenant_id, location_id)
```

### 41. inventory_count_items
**Purpose**: Individual product counts during physical inventory
```sql
id                    -- Primary key
count_id             -- FK to inventory_counts
variant_id          -- FK to product_variants
batch_id            -- FK to product_batches (NULL if no batch)
system_quantity     -- What computer says we have
counted_quantity    -- What was physically counted
variance            -- Difference (counted - system)
notes              -- Explanation for variance
counted_by_user_id  -- Who counted this product
created_at
-- INDEX on (count_id, variant_id)
```

## User Management & Security

### 42. users (Django User Model Extension)
**Purpose**: System login accounts - extends Django's AbstractUser with multi-tenant support
```sql
# Django provides: id, username, email, password, first_name, last_name, etc.
tenant_id             -- FK to tenants (users belong to specific tenant)
employee_id          -- Links to employee record (NULL for non-employees)
is_active            -- Can they log in? (Django built-in)
last_login_date      -- When they last accessed system (Django built-in as last_login)
preferred_currency_id -- FK to currencies (for display preferences)
language_preference -- User's preferred language
timezone           -- User's timezone
created_at           -- Django built-in as date_joined
updated_at           -- Custom field
deleted_at           -- Soft delete
```
**Example**: john@acme.com belongs to tenant_id=5 (ACME Electronics), linked to employee_id=12

### 43. permissions
**Purpose**: Master list of all system permissions - defines what actions exist
```sql
id                   -- Primary key
name                -- Unique permission identifier (e.g., 'catalog.add_product')
description         -- User-friendly explanation
module              -- Which app/module (e.g., 'catalog', 'sales', 'inventory')
created_at
```
**Examples**:
- name='catalog.add_product', description='Can create new products'
- name='sales.view_reports', description='Can view sales reports'
- name='inventory.adjust_stock', description='Can make inventory adjustments'

### 44. user_roles
**Purpose**: Roles assigned to users within their tenant
```sql
id                   -- Primary key
tenant_id           -- FK to tenants (roles are tenant-specific)
user_id             -- FK to users (which user)
role_name           -- ENUM: 'admin', 'manager', 'cashier', 'inventory_clerk', 'accountant'
assigned_by_user_id -- Who gave them this role
assigned_date       -- When role was assigned
is_active           -- Is this role currently active?
created_at
updated_at
```
**Example**: User john@acme.com has role 'manager' in tenant ACME Electronics

### 45. role_permissions
**Purpose**: Which permissions each role has (many-to-many relationship)
```sql
id                   -- Primary key
role_name           -- ENUM matching user_roles.role_name
permission_id       -- FK to permissions table
-- UNIQUE constraint on (role_name, permission_id)
```
**Example**: Role 'manager' has permissions: catalog.add_product, sales.view_reports, inventory.view_stock

### 46. user_product_preferences
**Purpose**: User-specific product preferences (favorites, bookmarks, etc.)
```sql
user_id             -- Composite primary key part 1, FK to users
product_id          -- Composite primary key part 2, FK to products
tenant_id           -- FK to tenants (for data isolation)
is_favorite         -- (boolean) User marked as favorite
is_bookmarked       -- (boolean) User bookmarked for quick access
last_viewed_at      -- When user last accessed this product
view_count          -- How many times user accessed this product
created_at
-- PRIMARY KEY (user_id, product_id)
-- INDEX on (tenant_id, user_id) for performance
```

### 47. activity_logs
**Purpose**: Complete audit trail of all user actions within each tenant
```sql
id                   -- Primary key
tenant_id           -- FK to tenants (logs are tenant-specific)
user_id             -- Who performed the action
action              -- What they did: 'create', 'update', 'delete', 'login', 'logout'
table_name          -- Which database table was affected
record_id           -- Which specific record (product_id, sale_id, etc.)
old_values          -- Data before change (JSON)
new_values          -- Data after change (JSON)
ip_address          -- Client IP address
user_agent          -- Browser/device information
session_id          -- User session identifier
timestamp           -- When action happened
created_at
```
**Example**: User john@acme.com (tenant_id=5) updated product iPhone 15 (record_id=123), changed price from AED3000 to AED3200

### 48. system_settings
**Purpose**: Tenant-specific configuration options
```sql
id                   -- Primary key
tenant_id           -- FK to tenants (settings are tenant-specific)
setting_key         -- What setting (e.g., 'base_currency_id', 'tax_rate')
setting_value       -- The value
setting_type        -- ENUM: 'string', 'number', 'boolean', 'json'
description         -- What this setting does
category            -- Group settings: 'general', 'inventory', 'sales', 'finance'
updated_by_user_id  -- Who last changed this setting
updated_at
created_at
```
**Examples**:
- tenant_id=5, setting_key='base_currency_id', setting_value='1' (AED)
- tenant_id=5, setting_key='tax_rate', setting_value='0.05' (5%)
- tenant_id=5, setting_key='low_stock_alert_threshold', setting_value='10'

## Multi-Tenant Schema Modifications

### Key Changes to Your 41 Tables:

#### 1. Tenant ID Addition
**Every table with business data must include:**
```sql
tenant_id            -- FK to tenants table
-- INDEX on tenant_id for query performance
-- All queries MUST include WHERE tenant_id = current_tenant_id
```

**Tables that need tenant_id:**
- products, product_variants, product_batches, product_prices
- customers, vendors, employees, members
- sales, sale_items, purchases, purchase_items, returns, return_items
- inventory, stock_movements, inventory_adjustments, inventory_counts, inventory_count_items
- locations, cash_drawers, cash_drawer_money, payments, transactions
- expenses, expense_categories, monthly_payments
- departments, categories, attributes, attribute_values
- addresses (when linked to tenant-specific entities)

#### 2. Reference ID Changes
**Critical Schema Updates:**

**inventory table structure:**
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
variant_id           -- FK to product_variants (replaces product_id)
batch_id             -- FK to product_batches (NULL if no expiry tracking)
location_id          -- FK to locations
quantity_on_hand     -- Current stock
reserved_quantity    -- Reserved for orders
reorder_level        -- Location-specific minimum stock
last_counted_date    -- Last physical count
created_at
updated_at
-- UNIQUE constraint on (tenant_id, variant_id, batch_id, location_id)
```

**All transaction tables now reference variants:**
- stock_movements: variant_id + batch_id (not product_id)
- sale_items: variant_id + batch_id
- purchase_items: variant_id + batch_id
- inventory_adjustments: variant_id + batch_id
- inventory_count_items: variant_id + batch_id

#### 3. Product Hierarchy Structure
```sql
-- products (parent/template)
id, tenant_id, name, category_id, description, is_active...

-- product_variants (actual sellable items)
id, tenant_id, product_id, sku, barcode, cost_price, selling_price...

-- product_variant_attributes (variant properties)
variant_id, attribute_id, attribute_value_id

-- product_batches (expiry tracking)
id, tenant_id, variant_id, batch_number, expiry_date, purchase_date...
```

## Django Apps Structure

### 1. **core** app - Base/shared functionality
**Models:**
- tenants, tenant_settings, tenant_subscriptions
- units, currencies, currency_rates
- addresses, system_settings
- permissions, activity_logs

**Purpose:** Foundation models that other apps depend on

### 2. **accounts** app - User management
**Models:**
- users (Django User extension)
- user_roles, role_permissions
- user_product_preferences

**Purpose:** Authentication, authorization, user preferences

### 3. **catalog** app - Product catalog management
**Models:**
- departments, categories
- attributes, attribute_values
- products, product_variants, product_variant_attributes
- product_prices

**Purpose:** Product information and pricing

### 4. **inventory** app - Stock management
**Models:**
- locations, product_batches
- inventory, stock_movements
- inventory_adjustments, inventory_counts, inventory_count_items

**Purpose:** Stock tracking and warehouse management

### 5. **vendors** app - Supplier management
**Models:**
- vendors, purchases, purchase_items

**Purpose:** Supplier relationships and procurement

### 6. **customers** app - Customer management
**Models:**
- customers

**Purpose:** Customer data and relationships

### 7. **sales** app - Sales operations
**Models:**
- sales, sale_items
- returns, return_items

**Purpose:** Sales transactions and returns

### 8. **finance** app - Financial management
**Models:**
- cash_drawers, cash_drawer_money
- payments, transactions
- expenses, expense_categories, monthly_payments

**Purpose:** Money management and accounting

### 9. **hr** app - Human Resources
**Models:**
- employees, employee_positions, employee_careers
- members

**Purpose:** Staff and partnership management

## Multi-Tenant Business Process Flows

### 1. Tenant Onboarding Flow
```
1. CREATE tenant record in tenants table
2. CREATE default tenant_settings:
   - base_currency_id = 1 (AED)
   - enable_variants = false
   - enable_expiry_tracking = false
   - enable_multi_location = true
   - tax_rate = 0.05
3. CREATE admin user:
   - username = owner email
   - tenant_id = new tenant id
   - role = 'admin'
4. CREATE default location:
   - name = "Main Store"
   - tenant_id = new tenant id
5. CREATE default cash_drawer:
   - name = "Main Register"
   - location_id = default location
   - tenant_id = new tenant id
6. GRANT all permissions to admin role
7. SEND welcome email with login credentials
```

### 2. Making a Sale (Multi-Tenant + Variants + Batches)
```
1. USER logs in → System identifies tenant_id from user record
2. ALL subsequent queries include WHERE tenant_id = user.tenant_id
3. CREATE sale record:
   - tenant_id = current_tenant_id
   - location_id = user's current location
   - status = 'draft'
4. ADD products to sale:
   - IF variants enabled: User selects specific variant_id
   - IF expiry tracking enabled: System auto-selects batch_id using FEFO logic
   - ELSE: batch_id = NULL
5. CALCULATE totals using variant-specific pricing
6. UPDATE sale (status = 'completed')
7. CREATE stock_movements:
   - tenant_id = current_tenant_id
   - variant_id = selected variant
   - batch_id = selected batch (or NULL)
   - movement_type = 'out'
8. UPDATE inventory:
   - Find record: (tenant_id, variant_id, batch_id, location_id)
   - Reduce quantity_on_hand
9. CREATE payment record with tenant_id
10. CREATE transaction record with tenant_id
11. LOG everything in activity_logs with tenant_id
```

### 3. Receiving Purchase (Multi-Tenant + Variants + Batches)
```
1. CREATE purchase record (tenant_id = current_tenant_id)
2. ADD purchase_items:
   - IF variants enabled: Link to specific variant_id
   - ELSE: Link to default variant of product
3. WHEN goods received:
   - IF expiry tracking enabled:
     a. CREATE product_batches record:
        - tenant_id = current_tenant_id
        - variant_id = purchased variant
        - batch_number = supplier batch number
        - expiry_date = from supplier info
   - ELSE: batch_id = NULL
4. CREATE stock_movements:
   - tenant_id = current_tenant_id
   - variant_id = received variant
   - batch_id = new batch or NULL
   - movement_type = 'in'
5. UPDATE/CREATE inventory record:
   - (tenant_id, variant_id, batch_id, location_id)
   - Increase quantity_on_hand
6. All payment and transaction records include tenant_id
```

### 4. Feature Flag Implementation
```
WHEN user performs action requiring feature check:

1. QUERY tenant_settings:
   WHERE tenant_id = current_tenant_id 
   AND setting_key = 'enable_variants'

2. IF setting_value = 'true':
   - SHOW variant selection UI
   - REQUIRE variant_id in all inventory operations
   
3. IF setting_value = 'false':
   - HIDE variant UI
   - AUTO-SELECT default variant for product
   
4. SAME logic for 'enable_expiry_tracking':
   - TRUE: Show batch fields, implement FEFO
   - FALSE: Set batch_id = NULL everywhere
```

### 5. Multi-Tenant Security Query Pattern
```sql
-- WRONG (Security Risk):
SELECT * FROM products WHERE id = 123;

-- CORRECT (Tenant-Safe):
SELECT * FROM products 
WHERE id = 123 AND tenant_id = current_user_tenant_id;

-- Using Django ORM with automatic tenant filtering:
# In Django middleware or model manager
class TenantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            tenant_id=get_current_tenant_id()
        )

# Usage:
products = Product.objects.all()  # Automatically filtered by tenant
```

### 6. Tenant Billing Flow
```
1. MONTHLY job runs for all active tenants
2. FOR each tenant:
   a. COUNT active users: SELECT COUNT(*) FROM users WHERE tenant_id = X
   b. CALCULATE storage used: SUM(file_sizes) for tenant
   c. CHECK tenant_subscriptions.plan_limits
   d. IF over limits: UPDATE tenant status to 'suspended'
   e. CALCULATE monthly bill based on usage
   f. CREATE invoice record
   g. SEND billing notification
3. PROCESS payments and update subscription status
```

This comprehensive schema provides a robust foundation for a multi-tenant SaaS business management system with flexible feature flags, proper data isolation, and scalable architecture.