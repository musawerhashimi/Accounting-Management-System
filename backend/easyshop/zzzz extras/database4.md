# Complete Business Management Database Design

## Core Product & Inventory Tables

### 1. units
**Purpose**: Defines measurement units for products (pieces, kg, liters, etc.)
```sql
id                  -- Primary key
name               -- Unit name (e.g., "Piece", "Kilogram", "Liter")
abbreviation       -- Short form (e.g., "pcs", "kg", "L")
unit_type          -- ENUM: 'weight', 'volume', 'length', 'count', 'area'
base_unit_id       -- Links to base unit for conversions (NULL if this IS the base)
conversion_factor  -- How many base units = 1 of this unit
is_base_unit       -- Is this the primary unit for its type?
created_at         -- When this unit was added
updated_at         -- Last modification time
deleted_at         -- Soft delete timestamp
```
**Examples**: 
- Kilogram: id=1, name="Kilogram", abbreviation="kg", unit_type="weight", base_unit_id=NULL, is_base_unit=true
- Ton: id=2, name="Ton", abbreviation="t", unit_type="weight", base_unit_id=1, conversion_factor=1000, is_base_unit=false
- Gram: id=3, name="Gram", abbreviation="g", unit_type="weight", base_unit_id=1, conversion_factor=0.001, is_base_unit=false

### 2. departments
**Purpose**: Main business categories (like Electronics, Clothing, Food)
```sql
id                 -- Primary key
name              -- Department name
description       -- Optional description
is_active         -- Whether department is currently in use
created_at        -- When department was created
updated_at        -- Last modification
deleted_at        -- Soft delete
```
**Example**: id=1, name="Electronics", description="All electronic items"

### 3. categories
**Purpose**: Sub-categories within departments (Phones under Electronics)
```sql
id                 -- Primary key
department_id      -- Links to departments table
name              -- Category name
description       -- Optional description
is_active         -- Active status
created_at
updated_at
deleted_at
```
**Example**: id=1, department_id=1, name="Mobile Phones"

### 4. products
**Purpose**: Master product catalog with basic info and default pricing
```sql
id                    -- Primary key
name                 -- Product name
barcode              -- Unique product identifier (can be scanned)
sku                  -- Stock Keeping Unit (internal code)
category_id          -- Links to categories
unit_id              -- Default measurement unit
description          -- Product details
cost_price           -- How much we pay to buy this product
selling_price        -- Default selling price
price_currency_id    -- Currency for the prices above
reorder_level        -- Minimum stock before reordering
is_active            -- Whether product is still sold
created_at
updated_at
deleted_at
```
**Example**: iPhone 15, barcode="123456789", cost_price=800, selling_price=1000

### 5. product_prices
**Purpose**: Historical pricing - tracks price changes over time
```sql
id                   -- Primary key
product_id          -- Which product
cost_price          -- Purchase cost at this time
selling_price       -- Selling price at this time
currency_id         -- Price currency
effective_date      -- When this price started
end_date           -- When this price ended (NULL if current)
created_by_user_id  -- Who changed the price
created_at
```
**Why**: Lets you see "iPhone was $900 in January, $950 in March"

## Location & Inventory Tables

### 6. locations
**Purpose**: Physical places where inventory is stored
```sql
id                 -- Primary key
name              -- Location name
address           -- Physical address
location_type     -- ENUM: 'warehouse', 'store', 'supplier'
is_active         -- Whether location is operational
manager_id        -- Employee who manages this location
created_at
updated_at
deleted_at
```
**Example**: "Main Store", "Downtown Warehouse", "Supplier ABC"

### 7. inventory
**Purpose**: Current stock levels at each location
```sql
id                    -- Primary key
product_id           -- Which product
location_id          -- At which location
quantity_on_hand     -- Current stock count
reserved_quantity    -- Stock reserved for pending orders
reorder_level        -- Minimum before reordering (location-specific)
last_counted_date    -- When physical count was last done
created_at
updated_at
```
**Example**: iPhone 15 at Main Store has 25 pieces, 3 reserved

### 8. stock_movements
**Purpose**: Every time inventory changes, record it here (audit trail)
```sql
id                   -- Primary key
product_id          -- Which product moved
location_id         -- At which location
movement_type       -- ENUM: 'in', 'out', 'transfer', 'adjustment'
quantity            -- How many (positive or negative)
reference_type      -- What caused this movement: 'purchase', 'sale', 'adjustment'
reference_id        -- ID of the purchase/sale/adjustment record
notes              -- Optional explanation
created_by_user_id -- Who made this movement
created_at
```
**Example**: +50 iPhones came 'in' from purchase #123, -2 iPhones went 'out' for sale #456

## Currency Management

### 9. currencies
**Purpose**: All currencies used in the business
```sql
id                 -- Primary key
name              -- Currency name
code              -- ISO code (USD, EUR, etc.)
symbol            -- Currency symbol ($, €, etc.)
is_active         -- Still in use?
created_at
updated_at
```

### 10. currency_rates
**Purpose**: Exchange rates between currencies (changes daily)
```sql
id                 -- Primary key
from_currency_id   -- Convert from this currency
to_currency_id     -- Convert to this currency
rate              -- Exchange rate (1 USD = 3.75 AED)
effective_date    -- Date this rate applies from
created_at
```
**Example**: 1 USD = 3.75 AED on 2025-06-12

## Supplier & Purchase Management

### 11. vendors
**Purpose**: Companies/people we buy products from
```sql
id                 -- Primary key  
name              -- Vendor company name
contact_person    -- Main contact name
phone             -- Phone number
email             -- Email address
address           -- Physical address
credit_limit      -- Maximum we can owe them
payment_terms     -- How many days to pay (30, 60, etc.)
tax_id            -- Their tax identification
balance           -- Current amount we owe them
status            -- ENUM: 'active', 'inactive', 'blocked'
created_at
updated_at
deleted_at
```

### 12. purchases
**Purpose**: Purchase orders/invoices from vendors
```sql
id                    -- Primary key
purchase_number      -- Our internal PO number
vendor_id           -- Who we're buying from
purchase_date       -- When we ordered
delivery_date       -- When we received
subtotal           -- Cost before any taxes/duties
tax_amount         -- Any import duties or taxes (0 if none)
total_amount       -- Total purchase cost (subtotal + tax_amount)
currency_id        -- Currency of the purchase
status             -- ENUM: 'pending', 'received', 'cancelled'
notes              -- Additional information
created_by_user_id -- Who created this purchase
created_at
updated_at
```

### 13. purchase_items
**Purpose**: Individual products within each purchase
```sql
id                 -- Primary key
purchase_id       -- Which purchase order
product_id        -- Which product
quantity          -- How many we ordered
unit_cost         -- Price per unit
line_total        -- quantity × unit_cost
received_quantity -- How many actually arrived
created_at
```
**Example**: Purchase #123 includes 50 iPhones at $800 each = $40,000

## Customer Management

### 14. addresses
**Purpose**: Flexible address storage for customers, vendors, locations
```sql
id                    -- Primary key
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
```
**Why flexible**: One customer can have multiple addresses (home, office, billing)

### 15. customers
**Purpose**: People/companies who buy from us
```sql
id                    -- Primary key
customer_number      -- Unique customer ID (C001, C002, etc.)
name                -- Customer name
gender              -- Optional: 'male', 'female', 'other'
email               -- Email address
phone               -- Phone number
customer_type       -- ENUM: 'individual', 'business', 'vip'
credit_limit        -- Maximum they can owe us
discount_percentage -- Default discount they get
tax_exempt          -- Do they pay tax? (true/false) default false
balance             -- Current amount they owe us
date_joined         -- When they became customer
status              -- ENUM: 'active', 'inactive', 'blocked'
notes              -- Additional information
photo_url           -- Customer photo path
created_at
updated_at
deleted_at
```

## Sales Management

### 16. sales
**Purpose**: Individual sales transactions
```sql
id                    -- Primary key
sale_number          -- Receipt/invoice number
customer_id          -- Who bought (NULL for walk-in customers)
sale_date           -- When sale happened
subtotal            -- Total before discount/tax
discount_amount     -- Total discount given
tax_amount          -- Tax charged (0 if no tax system)
total_amount        -- Final amount customer pays
currency_id         -- Sale currency
payment_status      -- ENUM: 'paid', 'partial', 'pending'
notes              -- Special instructions
created_by_user_id  -- Which employee made the sale
created_at
updated_at
```

### 17. sale_items
**Purpose**: Products sold in each sale
```sql
id                 -- Primary key
sale_id           -- Which sale
product_id        -- Which product
quantity          -- How many sold
unit_price        -- Price per unit (at time of sale)
line_total        -- quantity × unit_price
discount_amount   -- Discount on this line item
created_at
```
**Example**: Sale #789 includes 2 iPhones at $1000 each, with $50 discount

### 18. returns
**Purpose**: When customers return products
```sql
id                    -- Primary key
return_number        -- Unique return ID
original_sale_id     -- Which sale is being returned
customer_id          -- Who is returning
return_date         -- When return happened
reason              -- Why returning: 'defective', 'unwanted', etc.
total_refund_amount -- How much money refunded
currency_id         -- Refund currency
status              -- ENUM: 'pending', 'approved', 'completed'
processed_by_user_id -- Who handled the return
created_at
updated_at
```

### 19. return_items
**Purpose**: Specific products being returned
```sql
id                    -- Primary key
return_id            -- Which return
sale_item_id         -- Original sale item being returned
quantity_returned    -- How many being returned
condition           -- ENUM: 'new', 'used', 'damaged'
refund_amount       -- Money refunded for this item
restocked           -- Put back in inventory? (true/false)
created_at
```

## Financial Management

### 20. cash_drawers
**Purpose**: Physical cash registers/tills in stores
```sql
id                 -- Primary key
name              -- Drawer name ("Main Register", "Counter 2")
location_id       -- Which store/location
is_active         -- Currently in use?
created_at
updated_at
```

### 21. cash_drawer_money
**Purpose**: How much cash is in each drawer, by currency
```sql
id                 -- Primary key
cash_drawer_id    -- Which drawer
currency_id       -- Which currency
amount            -- Current amount
last_counted_date -- When last physically counted
created_at
updated_at
```
**Example**: Main Register has $500 USD and 200 AED

### 22. payments
**Purpose**: All money received from customers
```sql
id                    -- Primary key
payment_number       -- Unique payment reference
amount              -- Payment amount
currency_id         -- Payment currency
payment_method      -- ENUM: 'cash', 'card', 'bank_transfer', 'check'
payment_date        -- When payment received
reference_type      -- What was paid: 'sale', 'account_payment'
reference_id        -- ID of sale or customer account
cash_drawer_id      -- Where cash was deposited (if cash payment)
card_transaction_id -- Bank transaction reference (if card)
notes              -- Additional details
processed_by_user_id -- Who processed payment
created_at
```

### 23. transactions
**Purpose**: Complete financial audit trail - every money movement
```sql
id                    -- Primary key
transaction_date     -- When transaction occurred
amount              -- Transaction amount (positive or negative)
currency_id         -- Transaction currency
description         -- What happened
party_type          -- Who: 'customer', 'vendor', 'employee', 'expense'
party_id            -- ID of the customer/vendor/employee
transaction_type    -- ENUM: 'sale', 'purchase', 'payment', 'expense', 'transfer'
reference_type      -- Source document: 'sale', 'purchase', 'payment'
reference_id        -- ID of the source document
cash_drawer_id      -- Affected cash drawer (if applicable)
created_by_user_id  -- Who created this transaction
created_at
```
**Complex Example**: 
- Customer John (party_type='customer', party_id=5) bought $100 worth of goods
- This creates: +$100 transaction (sale income)
- When John pays: creates payment record and links to transaction

## Expense Management

### 24. expense_categories
**Purpose**: Organize business expenses (Rent, Utilities, Marketing, etc.)
```sql
id                    -- Primary key
name                 -- Category name
description          -- What expenses go here
parent_category_id   -- For subcategories (Marketing > Online Ads)
is_active           -- Still using this category?
created_at
updated_at
```
**Example**: "Marketing" parent category, "Online Advertising" subcategory

### 25. expenses
**Purpose**: All business expenses and costs
```sql
id                    -- Primary key
expense_number       -- Unique expense reference
expense_category_id  -- What type of expense
vendor_id           -- Who we paid (if vendor expense)
amount              -- Expense amount
currency_id         -- Expense currency
expense_date        -- When expense occurred
description         -- What was purchased/paid for
receipt_reference   -- Receipt number or reference
payment_method      -- How was it paid
status              -- ENUM: 'pending', 'approved', 'paid'
approved_by_user_id -- Who approved this expense
created_by_user_id  -- Who recorded this expense
created_at
updated_at
```

### 26. monthly_payments
**Purpose**: Recurring expenses (rent, salaries, subscriptions)
```sql
id                    -- Primary key
name                 -- Payment name ("Office Rent", "Internet Bill")
amount              -- Monthly amount
currency_id         -- Payment currency
payment_method      -- How it's paid
start_date          -- When recurring payments started
end_date            -- When they end (NULL if ongoing)
payment_day         -- Which day of month (1-31)
expense_category_id -- What type of expense
vendor_id          -- Who receives payment
is_active          -- Still active?
description        -- Additional details
created_at
updated_at
```

## Human Resources

### 27. employees
**Purpose**: Staff members and their basic information
```sql
id                 -- Primary key
employee_number   -- Unique employee ID (E001, E002)
name             -- Full name
phone            -- Phone number
email            -- Email address
hire_date        -- When they started
status           -- ENUM: 'active', 'inactive', 'terminated'
balance          -- Money owed to/by employee
created_at
updated_at
deleted_at
```

### 28. employee_positions
**Purpose**: Job roles and their details
```sql
id                 -- Primary key
position_name     -- Job title
department_id     -- Which department
base_salary       -- Standard salary for this position
currency_id       -- Salary currency
description       -- Job responsibilities
is_active         -- Still hiring for this position?
created_at
updated_at
```

### 29. employee_careers
**Purpose**: Track employee job history and salary changes
```sql
id                    -- Primary key
employee_id          -- Which employee
position_id          -- Which job position
start_date          -- When they started this role
end_date            -- When role ended (NULL if current)
salary              -- Salary for this role
currency_id         -- Salary currency
status              -- ENUM: 'active', 'ended'
notes              -- Performance notes, reason for change
created_at
updated_at
```
**Example**: John was "Cashier" from Jan-June ($2000), then "Supervisor" from July-present ($2500)

## Business Partnership

### 30. members
**Purpose**: Business partners/investors and their ownership
```sql
id                    -- Primary key
name                 -- Partner name
ownership_percentage -- What % of business they own
investment_amount   -- How much money they invested
currency_id         -- Investment currency
start_date         -- When partnership started
end_date           -- When partnership ended (NULL if active)
balance            -- Current account balance
profit_share       -- Accumulated profits owed to them
asset_share        -- Their share of business assets
status             -- ENUM: 'active', 'inactive', 'withdrawn'
created_at
updated_at
```

## Inventory Management Advanced

### 31. inventory_adjustments
**Purpose**: Manual corrections to inventory (damaged, theft, counting errors)
```sql
id                    -- Primary key
adjustment_number    -- Unique reference
product_id          -- Which product
location_id         -- At which location
adjustment_quantity -- How many added/removed (+ or -)
reason              -- ENUM: 'damaged', 'theft', 'count_correction', 'expired'
cost_impact         -- Financial impact of adjustment
currency_id         -- Cost currency
notes              -- Detailed explanation
approved_by_user_id -- Who approved this adjustment
created_by_user_id  -- Who made the adjustment
adjustment_date     -- When adjustment happened
created_at
```

### 32. inventory_counts
**Purpose**: Physical inventory counting sessions
```sql
id                    -- Primary key
count_number         -- Unique count reference
location_id         -- Which location was counted
count_date          -- When counting happened
status              -- ENUM: 'in_progress', 'completed', 'cancelled'
total_items_counted -- How many different products counted
variances_found     -- How many products had differences
created_by_user_id  -- Who organized the count
completed_by_user_id -- Who finished the count
created_at
updated_at
```

### 33. inventory_count_items
**Purpose**: Individual product counts during physical inventory
```sql
id                    -- Primary key
count_id             -- Which inventory count session
product_id          -- Which product
system_quantity     -- What computer says we have
counted_quantity    -- What was physically counted
variance            -- Difference (counted - system)
notes              -- Explanation for variance
counted_by_user_id  -- Who counted this product
created_at
```
**Example**: System says 100 iPhones, counted 98, variance = -2 (2 missing)

## User Management & Security

### 34. users
**Purpose**: System login accounts
```sql
id                 -- Primary key
username          -- Login username
email             -- Email address
password_hash     -- Encrypted password
employee_id       -- Links to employee record (NULL for non-employees)
is_active         -- Can they log in?
last_login_date   -- When they last accessed system
created_at
updated_at
deleted_at
```

### 35. user_roles
**Purpose**: What each user is allowed to do
```sql
id                 -- Primary key
user_id           -- Which user
role_name         -- ENUM: 'admin', 'manager', 'cashier', 'inventory_clerk'
permissions       -- JSON: specific permissions within role
assigned_by_user_id -- Who gave them this role
assigned_date     -- When role was assigned
is_active         -- Is this role currently active?
created_at
updated_at
```

### 36. activity_logs
**Purpose**: Track all user actions for security and audit
```sql
id                 -- Primary key
user_id           -- Who did the action
action            -- What they did ('create', 'update', 'delete', 'login')
table_name        -- Which database table was affected
record_id         -- Which specific record
old_values        -- Data before change (JSON)
new_values        -- Data after change (JSON)
ip_address        -- Where action came from
user_agent        -- What browser/device
timestamp         -- When action happened
```
**Example**: User John (id=5) updated product id=123, changed price from $100 to $120


**Purpose**: System-wide configuration options
```sql
id                 -- Primary key
setting_key       -- What setting (e.g., 'default_currency', 'tax_rate')
setting_value     -- The value
setting_type      -- ENUM: 'string', 'number', 'boolean', 'json'
description       -- What this setting does
category          -- Group settings ('general', 'inventory', 'sales')
updated_by_user_id -- Who last changed this
updated_at
created_at
```
**Examples**:
- setting_key='default_currency', setting_value='USD'
- setting_key='tax_rate', setting_value='0.05' (5%)
- setting_key='low_stock_alert', setting_value='true'

## Key Relationships Summary

**Product Flow**: departments → categories → products → inventory → sales/purchases
**Money Flow**: currencies → currency_rates → all financial transactions
**User Actions**: users → user_roles → activity_logs (everything tracked)
**Address System**: addresses table serves customers, vendors, locations (polymorphic)
**Audit Trail**: stock_movements + transactions + activity_logs = complete business history

## Business Process Examples

### Making a Sale:
1. Create record in `sales` table
2. Add products to `sale_items` table  
3. Create `stock_movements` (products going 'out')
4. Update `inventory` (reduce quantity_on_hand)
5. Create `payments` record when customer pays
6. Create `transactions` record for financial tracking
7. All actions logged in `activity_logs`

### Receiving Purchase:
1. Create `purchases` record
2. Add products to `purchase_items`
3. Create `stock_movements` (products coming 'in')
4. Update `inventory` (increase quantity_on_hand)
5. Update vendor `balance` (money we owe)
6. Create `transactions` record for expense

This design handles a complete business with full audit trails, multi-currency support, and detailed tracking of all operations.


WORKING WITH DJANGO AND DJANGO RESTFRAMEWORK TO CREATE AN API FROM THIS SYSTEM

DJANGO APPS AND MODELS IN EACH APP:

1. core app
Purpose: Base/shared models and utilities

units
currencies
currency_rates
system_settings
addresses (since it's polymorphic and used everywhere)

2. catalog app
Purpose: Product catalog management

departments
categories
products
product_prices

3. inventory app
Purpose: Stock management and warehouse operations

locations
inventory
stock_movements
inventory_adjustments
inventory_counts
inventory_count_items

4. vendors app
Purpose: Supplier/vendor management

vendors
purchases
purchase_items

5. customers app
Purpose: Customer management

customers

6. sales app
Purpose: Sales operations

sales
sale_items
returns
return_items

7. finance app
Purpose: Financial management

cash_drawers
cash_drawer_money
payments
transactions
expenses
expense_categories
monthly_payments

8. hr app (Human Resources)
Purpose: Employee management

employees
employee_positions
employee_careers
members (business partners)

9. accounts app
Purpose: User management and authentication

users
user_roles
activity_logs