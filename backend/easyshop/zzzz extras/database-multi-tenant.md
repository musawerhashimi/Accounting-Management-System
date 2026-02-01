# Complete Multi-Tenant Business Management Database Schema

## Multi-Tenant Architecture Overview

This system uses **Shared Database, Shared Schema** approach where:
- All tenants share the same database and tables
- Data isolation achieved through `tenant_id` column in every table
- Features controlled through tenant-specific settings
- **CRITICAL**: Every query MUST include `WHERE tenant_id = ?` clause for security

## Tenant Management Tables

### 1. tenants
**Purpose**: Core tenant/business account information
```sql
id                    -- Primary key
name                 -- Business display name
company_name         -- Legal company name
domain               -- Custom domain (optional)
subdomain            -- Subdomain (e.g., "acme" for acme.yoursaas.com)
contact_email        -- Primary contact email
contact_phone        -- Primary contact phone
address              -- Business address
city                 -- Business city
country              -- Business country
subscription_plan    -- ENUM: 'free', 'basic', 'premium', 'enterprise'
billing_cycle        -- ENUM: 'monthly', 'yearly'
subscription_start   -- When subscription started
subscription_end     -- When subscription expires
last_payment_date    -- Last successful payment
next_billing_date    -- Next payment due date
status               -- ENUM: 'active', 'suspended', 'cancelled', 'trial'
max_users            -- Maximum users allowed
max_products         -- Maximum products allowed
max_locations        -- Maximum locations allowed
storage_limit_mb     -- Storage limit in megabytes
timezone             -- Business timezone (e.g., "Asia/Dubai")
base_currency_id     -- Default currency for this tenant
date_format          -- ENUM: 'DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'
time_format          -- ENUM: '12h', '24h'
language             -- ENUM: 'en', 'ar', 'fr', etc.
logo_url             -- Business logo path
primary_color        -- Brand primary color (hex)
secondary_color      -- Brand secondary color (hex)
created_at           -- When tenant was created
updated_at           -- Last modification
deleted_at           -- Soft delete
```
**Example**: 
- name="Acme Electronics", subscription_plan="premium", max_users=25, base_currency_id=1(AED)

### 2. tenant_settings
**Purpose**: Feature flags and configuration per tenant
```sql
id                   -- Primary key
tenant_id           -- FK to tenants
setting_key         -- Setting identifier
setting_value       -- Setting value (stored as string, cast in app)
setting_type        -- ENUM: 'boolean', 'string', 'number', 'json'
category            -- ENUM: 'features', 'ui', 'business', 'integration'
description         -- What this setting controls
is_user_configurable -- Can tenant admin change this?
created_at
updated_at
```
**Key Settings Examples**:
- `enable_variants: true` - Show product variants feature
- `enable_expiry_tracking: false` - Hide batch/expiry features
- `enable_multi_location: true` - Multi-location inventory
- `enable_advanced_pricing: false` - Tier pricing, bulk discounts
- `tax_calculation: automatic` - Tax handling method
- `inventory_method: fifo` - Inventory costing method

## Core Product & Inventory Tables

### 3. units
**Purpose**: Measurement units (pieces, kg, liters, etc.)
```sql
id                  -- Primary key
tenant_id          -- FK to tenants
name               -- Unit name (e.g., "Piece", "Kilogram", "Liter")
abbreviation       -- Short form (e.g., "pcs", "kg", "L")
unit_type          -- ENUM: 'weight', 'volume', 'length', 'count', 'area'
base_unit_id       -- Links to base unit for conversions (NULL if this IS the base)
conversion_factor  -- How many base units = 1 of this unit
is_base_unit       -- Is this the primary unit for its type?
is_active          -- Still in use?
created_at
updated_at
deleted_at
```
**Examples**:
- Tenant 1: Kilogram (base), Gram (conversion_factor=0.001), Ton (conversion_factor=1000)
- Tenant 2: Piece (base), Box (conversion_factor=12), Case (conversion_factor=144)

### 4. departments
**Purpose**: Main business categories (Electronics, Clothing, Food)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Department name
description          -- Optional description
sort_order           -- Display order
is_active            -- Whether department is currently in use
created_by_user_id   -- Who created this department
created_at
updated_at
deleted_at
```

### 5. categories
**Purpose**: Sub-categories within departments
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
department_id         -- FK to departments
name                 -- Category name
description          -- Optional description
sort_order           -- Display order within department
is_active            -- Active status
created_by_user_id   -- Who created this category
created_at
updated_at
deleted_at
```

### 6. attributes
**Purpose**: Product variation attributes (Color, Size, Brand, etc.)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Attribute name (e.g., "Color", "Size")
display_name         -- User-friendly name
attribute_type       -- ENUM: 'text', 'number', 'color', 'image', 'boolean'
is_required          -- Must have value for variants?
is_filterable        -- Can customers filter by this?
is_searchable        -- Include in search?
sort_order           -- Display order
validation_rules     -- JSON: min/max length, regex, etc.
default_value        -- Default value for new variants
help_text           -- Instructions for users
is_active           -- Still in use?
created_at
updated_at
deleted_at
```
**Examples**:
- name="Color", attribute_type="color", is_required=true
- name="Size", attribute_type="text", validation_rules='{"values":["S","M","L","XL"]}'
- name="Material", attribute_type="text", is_filterable=true

### 7. attribute_values
**Purpose**: Possible values for each attribute
```sql
id                   -- Primary key
attribute_id         -- FK to attributes
value               -- The actual value ("Red", "Large", "Cotton")
display_value       -- User-friendly display name
color_code          -- Hex color (if attribute_type='color')
image_url           -- Image for this value (optional)
sort_order          -- Display order within attribute
is_active           -- Still available?
created_at
updated_at
```
**Examples**:
- attribute_id=1(Color): value="red", display_value="Red", color_code="#FF0000"
- attribute_id=2(Size): value="L", display_value="Large", sort_order=3

### 8. products
**Purpose**: Master product templates (iPhone 15, Nike Air Max)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Product name (e.g., "iPhone 15", "Nike Air Max 90")
description          -- Product details
category_id          -- FK to categories
unit_id              -- Default measurement unit
brand               -- Product brand
model               -- Product model
base_cost_price     -- Template cost price (variants can override)
base_cost_currency_id -- Cost currency
base_selling_price   -- Template selling price (variants can override)  
base_selling_currency_id -- Selling currency
reorder_level        -- Default minimum stock
weight              -- Product weight
dimensions          -- Product dimensions (JSON: length, width, height)
image_url           -- Main product image
gallery_images      -- JSON array of additional images
tags                -- JSON array of searchable tags
meta_title          -- SEO title
meta_description    -- SEO description
has_variants        -- Does this product have variants?
track_inventory     -- Should we track stock for this product?
is_active           -- Whether product is still sold
created_by_user_id  -- Who added this product
created_at
updated_at
deleted_at
```
**Example**: name="iPhone 15", has_variants=true, base_selling_price=3000, base_selling_currency_id=1

### 9. product_variants
**Purpose**: Individual SKUs (iPhone 15 Pro 256GB Space Black)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
product_id           -- FK to products (parent template)
sku                  -- Unique SKU for this variant
barcode              -- Scannable barcode
variant_name         -- Generated name (e.g., "Red / Large")
cost_price           -- Variant-specific cost (NULL = use product base_cost_price)
cost_currency_id     -- Cost currency (NULL = use product currency)
selling_price        -- Variant-specific price (NULL = use product base_selling_price)
selling_currency_id  -- Selling currency (NULL = use product currency)
price_adjustment     -- Price modifier: +50, -10, +5% (applied to base price)
adjustment_type      -- ENUM: 'fixed', 'percentage'
weight              -- Variant-specific weight (NULL = use product weight)
dimensions          -- Variant-specific dimensions (JSON)
image_url           -- Variant-specific image
reorder_level       -- Variant-specific reorder level
is_default          -- Is this the default variant for the product?
is_active           -- Is this variant still available?
stock_tracking_enabled -- Track inventory for this variant?
created_at
updated_at
deleted_at
```
**Example**: 
- product_id=1(iPhone 15), sku="IP15-256-SB", variant_name="256GB / Space Black"
- price_adjustment="+200", adjustment_type="fixed" (costs AED200 more than base)

### 10. product_variant_attributes
**Purpose**: Links variants to their attribute values (M:M relationship)
```sql
id                   -- Primary key
variant_id          -- FK to product_variants
attribute_id        -- FK to attributes  
attribute_value_id  -- FK to attribute_values
created_at
```
**Example**: variant_id=1 + attribute_id=1(Color) + attribute_value_id=5(Space Black)

### 11. product_batches
**Purpose**: Batch/lot tracking for expiry dates
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
variant_id           -- FK to product_variants
batch_number         -- Internal batch identifier
lot_number           -- Supplier lot number
expiry_date          -- When this batch expires
manufacture_date     -- When this batch was made
purchase_date        -- When we bought this batch
received_date        -- When we received this batch
supplier_batch_ref   -- Supplier's batch reference
notes               -- Additional batch information
status              -- ENUM: 'active', 'expired', 'recalled', 'sold_out'
created_at
updated_at
```
**Example**: batch_number="MILK-240601", expiry_date="2024-06-15", status="active"

### 12. product_prices
**Purpose**: Historical pricing for products/variants
```sql
id                   -- Primary key
tenant_id           -- FK to tenants
product_id          -- FK to products (NULL if variant-specific)
variant_id          -- FK to product_variants (NULL if product-level)
cost_price          -- Purchase cost
cost_currency_id    -- Cost currency
selling_price       -- Selling price
selling_currency_id -- Selling currency
customer_type       -- ENUM: 'all', 'retail', 'wholesale', 'vip'
min_quantity        -- Minimum quantity for this price
effective_date      -- When this price started
end_date           -- When this price ended (NULL for current)
is_current         -- Is this the active price?
created_by_user_id  -- Who set this price
created_at
```

## Location & Inventory Tables

### 13. addresses
**Purpose**: Flexible address storage
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
latitude            -- GPS latitude (optional)
longitude           -- GPS longitude (optional)
is_default          -- Is this the main address?
created_at
updated_at
deleted_at
```

### 14. locations
**Purpose**: Physical places where inventory is stored
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Location name
location_code     -- Short code (MAIN, WH01, etc.)
location_type     -- ENUM: 'warehouse', 'store', 'supplier', 'virtual'
address_id        -- FK to addresses
is_active         -- Whether location is operational
is_default        -- Is this the default location?
manager_id        -- FK to employees
capacity_info     -- JSON: max_items, max_weight, etc.
operating_hours   -- JSON: opening/closing times
contact_phone     -- Location phone
contact_email     -- Location email
created_by_user_id -- Who created this location
created_at
updated_at
deleted_at
```

### 15. inventory
**Purpose**: Current stock levels (supports both simple products and batches)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
product_id           -- FK to products (for non-variant products)
variant_id           -- FK to product_variants (for variant products)
batch_id             -- FK to product_batches (NULL if no batch tracking)
location_id          -- FK to locations
quantity_on_hand     -- Current stock count
reserved_quantity    -- Stock reserved for pending orders
allocated_quantity   -- Stock allocated to specific orders
available_quantity   -- on_hand - reserved - allocated (calculated)
average_cost         -- Weighted average cost per unit
last_cost           -- Cost from last purchase
reorder_level        -- Location-specific minimum stock
max_stock_level     -- Location-specific maximum stock
last_counted_date    -- When physical count was last done
last_movement_date   -- When stock last changed
created_at
updated_at
```
**Key Logic**: 
- For simple products: product_id filled, variant_id=NULL, batch_id=NULL
- For variants: variant_id filled, product_id=NULL, batch_id=NULL
- For batches: variant_id + batch_id filled, product_id=NULL

### 16. stock_movements
**Purpose**: Complete audit trail of inventory changes
```sql
id                   -- Primary key
tenant_id           -- FK to tenants
product_id          -- FK to products (NULL for variants)
variant_id          -- FK to product_variants (NULL for simple products)
batch_id            -- FK to product_batches (NULL if no batch tracking)
location_id         -- FK to locations
movement_type       -- ENUM: 'in', 'out', 'transfer', 'adjustment'
quantity            -- Quantity moved (positive or negative)
unit_cost           -- Cost per unit for this movement
total_cost          -- quantity × unit_cost
reference_type      -- What caused movement: 'purchase', 'sale', 'transfer', 'adjustment'
reference_id        -- ID of the source document
reference_number    -- Human-readable reference (PO-001, SALE-123)
notes              -- Optional explanation
movement_date       -- When movement occurred
created_by_user_id -- Who recorded this movement
created_at
```

## Currency Management

### 17. currencies
**Purpose**: All currencies used in the business
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Currency name
code              -- ISO code (USD, EUR, CNY, AED, etc.)
symbol            -- Currency symbol ($, €, ¥, د.إ, etc.)
decimal_places    -- How many decimal places
is_base_currency  -- Is this the tenant's base currency?
is_active         -- Still in use?
created_at
updated_at
```

### 18. currency_rates
**Purpose**: Exchange rates between currencies
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
from_currency_id  -- FK to currencies (source currency)
to_currency_id    -- FK to currencies (target currency)
rate              -- Exchange rate (1 from_currency = rate * to_currency)
effective_date    -- Date this rate applies from
source            -- Where rate came from: 'manual', 'api', 'bank'
created_at
```

## Supplier & Purchase Management

### 19. vendors
**Purpose**: Companies/people we buy products from
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
vendor_number     -- Unique vendor code (V001, V002)
name              -- Vendor company name
contact_person    -- Main contact name
phone             -- Phone number
email             -- Email address
website           -- Vendor website
tax_id            -- Their tax identification
credit_terms      -- Payment terms (Net 30, Net 60, etc.)
credit_limit      -- Maximum we can owe them
payment_method    -- Default payment method
discount_terms    -- Early payment discount (2/10 Net 30)
currency_id       -- Preferred transaction currency
balance           -- Current amount we owe (auto-calculated)
rating           -- ENUM: 'excellent', 'good', 'fair', 'poor'
status           -- ENUM: 'active', 'inactive', 'blocked'
notes            -- Additional vendor information
created_by_user_id -- Who added this vendor
created_at
updated_at
deleted_at
```

### 20. purchases
**Purpose**: Purchase orders/invoices from vendors
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
purchase_number      -- Our internal PO number
vendor_id           -- FK to vendors
location_id         -- FK to locations (where goods received)
purchase_date       -- When we ordered
expected_date       -- When we expect delivery
delivery_date       -- When we actually received
subtotal           -- Cost before taxes/shipping
tax_amount         -- Tax/duties amount
shipping_cost      -- Shipping charges
total_amount       -- Final total amount
currency_id        -- Purchase currency
exchange_rate      -- Rate used if different from system rate
status             -- ENUM: 'draft', 'sent', 'received', 'cancelled'
payment_status     -- ENUM: 'pending', 'partial', 'paid'
payment_terms      -- Terms for this specific purchase
vendor_invoice_number -- Vendor's invoice number
tracking_number    -- Shipping tracking number
notes              -- Additional information
created_by_user_id -- Who created this purchase
approved_by_user_id -- Who approved this purchase
created_at
updated_at
```

### 21. purchase_items
**Purpose**: Individual products/variants within each purchase
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
purchase_id       -- FK to purchases
product_id        -- FK to products (for simple products)
variant_id        -- FK to product_variants (for variant products)
batch_id          -- FK to product_batches (if batch tracking enabled)
description       -- Item description (for reference)
quantity_ordered  -- How many we ordered
quantity_received -- How many actually arrived
unit_cost         -- Price per unit
line_total        -- quantity_ordered × unit_cost
expiry_date      -- Expiry date for this batch (if applicable)
notes            -- Notes for this line item
created_at
```

## Customer Management

### 22. customers
**Purpose**: People/companies who buy from us
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
customer_number      -- Unique customer ID (C001, C002, etc.)
name                -- Customer name
company_name        -- Company name (if business customer)
gender              -- ENUM: 'male', 'female', 'other', 'not_specified'
date_of_birth       -- Customer birthday (for marketing)
email               -- Email address
phone               -- Primary phone number
secondary_phone     -- Secondary phone number
customer_type       -- ENUM: 'individual', 'business', 'vip', 'wholesale'
price_level         -- ENUM: 'retail', 'wholesale', 'vip' (determines pricing)
credit_limit        -- Maximum they can owe us
credit_terms        -- Payment terms (Net 30, etc.)
discount_percentage -- Default discount they get
tax_exempt          -- Do they pay tax? (true/false)
tax_id              -- Their tax ID (if business)
balance             -- Current amount they owe (auto-calculated)
loyalty_points      -- Reward points balance
preferred_currency_id -- Preferred transaction currency
date_joined         -- When they became customer
last_purchase_date  -- When they last bought something
total_purchases     -- Lifetime purchase amount
purchase_count      -- Number of purchases made
status              -- ENUM: 'active', 'inactive', 'blocked'
source              -- How they found us: 'referral', 'advertising', 'walk_in'
notes              -- Additional information
photo_url           -- Customer photo
created_by_user_id  -- Who added this customer
created_at
updated_at
deleted_at
```

## Sales Management

### 23. sales
**Purpose**: Individual sales transactions
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
sale_number          -- Receipt/invoice number
customer_id          -- FK to customers (NULL for walk-in)
location_id          -- FK to locations (which store made sale)
sale_date           -- When sale happened
due_date            -- Payment due date (for credit sales)
subtotal            -- Total before discount/tax
discount_amount     -- Total discount given
discount_percentage -- Discount percentage applied
tax_amount          -- Tax charged
shipping_amount     -- Shipping charges
total_amount        -- Final amount customer pays
currency_id         -- Sale currency
exchange_rate       -- Exchange rate used
payment_status      -- ENUM: 'paid', 'partial', 'pending', 'overdue'
status              -- ENUM: 'draft', 'completed', 'cancelled', 'refunded'
sale_type           -- ENUM: 'pos', 'online', 'phone', 'quote'
channel             -- ENUM: 'in_store', 'website', 'mobile_app', 'marketplace'
source_document_id  -- If converted from quote/order
shipping_address_id -- FK to addresses (for delivery)
billing_address_id  -- FK to addresses (for billing)
notes              -- Special instructions
internal_notes     -- Staff-only notes
terms_conditions   -- Sale terms
created_by_user_id  -- Which employee made the sale
approved_by_user_id -- Who approved the sale (if required)
created_at
updated_at
```

### 24. sale_items
**Purpose**: Products/variants sold in each sale
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
sale_id           -- FK to sales
product_id        -- FK to products (for simple products)
variant_id        -- FK to product_variants (for variant products)
batch_id          -- FK to product_batches (if batch tracking)
description       -- Item description at time of sale
quantity          -- How many sold
unit_price        -- Price per unit (at time of sale)
original_price    -- Original price before discounts
line_total        -- quantity × unit_price
discount_amount   -- Discount on this line item
discount_percentage -- Discount percentage for this line
tax_amount        -- Tax on this line item
cost_price        -- Our cost for this item (for profit calculation)
profit_amount     -- line_total - (cost_price × quantity)
notes            -- Notes for this line item
created_at
```

### 25. returns
**Purpose**: When customers return products
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
return_number        -- Unique return ID
original_sale_id     -- FK to sales (which sale is being returned)
customer_id          -- FK to customers
location_id          -- FK to locations (derived from original sale)
return_date         -- When return happened
reason_code         -- ENUM: 'defective', 'wrong_item', 'unwanted', 'damaged'
reason_description  -- Detailed reason
subtotal           -- Return amount before adjustments
restocking_fee     -- Fee charged for return
refund_amount      -- Net amount refunded
currency_id        -- Refund currency
refund_method      -- How refunded: 'cash', 'card', 'store_credit'
status             -- ENUM: 'pending', 'approved', 'completed', 'rejected'
requires_approval  -- Does this return need manager approval?
processed_by_user_id -- Who handled the return
approved_by_user_id -- Who approved the return
created_at
updated_at
```

### 26. return_items
**Purpose**: Specific products being returned
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
return_id            -- FK to returns
sale_item_id         -- FK to sale_items (original item being returned)
product_id           -- FK to products
variant_id           -- FK to product_variants
batch_id            -- FK to product_batches
quantity_returned    -- How many being returned
unit_price          -- Original selling price
line_total          -- quantity_returned × unit_price
restocking_fee      -- Fee for this line
net_refund_amount   -- Amount refunded for this line
condition           -- ENUM: 'new', 'used', 'damaged', 'defective'
disposition         -- ENUM: 'restock', 'repair', 'dispose', 'return_to_vendor'
restocked           -- Was item put back in inventory?
notes              -- Notes about this return item
created_at
```

## Financial Management

### 27. cash_drawers
**Purpose**: Physical cash registers/tills
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
name              -- Drawer name ("Main Register", "Counter 2")
location_id       -- FK to locations
drawer_code       -- Short code (REG01, TILL1)
is_active         -- Currently in use?
current_shift_id  -- FK to cash_drawer_shifts (current shift)
opening_balance   -- Starting balance for current shift
created_by_user_id -- Who set up this register
created_at
updated_at
```

### 28. cash_drawer_shifts
**Purpose**: Track cash drawer opening/closing sessions
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
cash_drawer_id    -- FK to cash_drawers
opened_by_user_id -- Who opened the drawer
closed_by_user_id -- Who closed the drawer (NULL if still open)
shift_start       -- When shift started
shift_end         -- When shift ended (NULL if still open)
opening_balance   -- Cash at start of shift
closing_balance   -- Cash at end of shift
expected_balance  -- What balance should be (calculated)
variance          -- Difference between expected and actual
total_sales       -- Total sales during this shift
total_returns     -- Total returns during this shift
status            -- ENUM: 'open', 'closed', 'balanced'
notes            -- Notes about this shift
created_at
updated_at
```

### 29. cash_drawer_money
**Purpose**: Current cash in each drawer by currency
```sql
id                 -- Primary key
tenant_id         -- FK to tenants
cash_drawer_id    -- FK to cash_drawers
currency_id       -- FK to currencies
amount            -- Current amount (auto-calculated)
last_counted_date -- When last physically counted
counted_amount    -- Last physical count amount
variance          -- Difference from system amount
created_at
updated_at
```

### 30. payments
**Purpose**: All money received from customers and paid to vendors
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
payment_number       -- Unique payment reference
amount              -- Payment amount
currency_id         -- Payment currency
exchange_rate       -- Exchange rate used
payment_method      -- ENUM: 'cash', 'card', 'bank_transfer', 'check', 'store_credit'
payment_date        -- When payment received/made
reference_type      -- What was paid: 'sale', 'return', 'customer_account', 'vendor_bill'
reference_id        -- ID of sale/return/customer/vendor
customer_id         -- FK to customers (for customer payments)
vendor_id           -- FK to vendors (for vendor payments)
cash_drawer_id      -- FK to cash_drawers (if cash payment)
bank_account_id     -- FK to bank accounts (if bank payment)
card_transaction_id -- External transaction reference
check_number        -- Check number (if check payment)
payment_gateway     -- ENUM: 'stripe', 'paypal', 'square' (if online)
gateway_transaction_id -- Gateway transaction reference
status             -- ENUM: 'pending', 'completed', 'failed', 'cancelled'
notes              -- Additional details
processed_by_user_id -- Who processed payment
created_at
updated_at
```

### 31. transactions
**Purpose**: Complete financial audit trail
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
transaction_number   -- Unique transaction reference
transaction_date     -- When transaction occurred
amount              -- Transaction amount (positive or negative)
currency_id         -- Transaction currency
description         -- What happened
account_type        -- ENUM: 'cash', 'bank', 'receivable', 'payable', 'expense', 'revenue'
party_type          -- Who: 'customer', 'vendor', 'employee', 'bank'
party_id            -- ID of the customer/vendor/employee
transaction_type    -- ENUM: 'sale', 'purchase', 'payment', 'expense', 'transfer', 'adjustment'
reference_type      -- Source document: 'sale', 'purchase', 'payment', 'expense'
reference_id        -- ID of the source document
cash_drawer_id      -- FK to cash_drawers (if cash transaction)
bank_account_id     -- FK to bank accounts (if bank transaction)
is_cleared          -- Has transaction been cleared/reconciled?
created_by_user_id  -- Who created this transaction
created_at
```

## Expense Management

### 32. expense_categories
**Purpose**: Organize business expenses
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Category name
description          -- What expenses go here
parent_category_id   -- FK to expense_categories (for subcategories)
category_code        -- Short code (RENT, UTIL, MARK)
is_active           -- Still using this category?
budget_amount       -- Monthly budget for this category
budget_currency_id  -- Budget currency
created_at
updated_at
deleted_at
```

### 33. expenses
**Purpose**: All business expenses and costs
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
expense_number       -- Unique expense reference
expense_category_id  -- FK to expense_categories
vendor_id           -- FK to vendors (if vendor expense)
employee_id         -- FK to employees (if employee expense)
amount              -- Expense amount
currency_id         -- Expense currency
expense_date        -- When expense occurred
due_date            -- When payment is due
description         -- What was purchased/paid for
receipt_number      -- Receipt number or reference
receipt_image_url   -- Photo of receipt
payment_method      -- How it was/will be paid
payment_status      -- ENUM: 'pending', 'paid', 'overdue'
status              -- ENUM: 'draft', 'submitted', 'approved', 'rejected', 'paid'
is_recurring        -- Is this a recurring expense?
recurring_frequency -- ENUM: 'monthly', 'quarterly', 'yearly'
tags               -- JSON array of tags for categorization
tax_deductible     -- Is this tax deductible?
project_id         -- FK to projects (if expense tracking by project)
approved_by_user_id -- Who approved this expense
created_by_user_id  -- Who recorded this expense
created_at
updated_at
```

### 34. recurring_expenses
**Purpose**: Template for recurring expenses (rent, subscriptions)
```sql
id                    -- Primary key
tenant_id            -- FK to tenants
name                 -- Expense name ("Office Rent", "Internet Bill")
expense_category