# Complete Updated Business Management Database Design

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
id                    -- Primary key
name                 -- Department name
description          -- Optional description
is_active            -- Whether department is currently in use
created_by_user_id   -- Who created this department
created_at           -- When department was created
updated_at           -- Last modification
deleted_at           -- Soft delete
```
**Example**: id=1, name="Electronics", description="All electronic items"

### 3. categories
**Purpose**: Sub-categories within departments (Phones under Electronics)
```sql
id                    -- Primary key
department_id         -- Links to departments table
name                 -- Category name
description          -- Optional description
is_active            -- Active status
created_by_user_id   -- Who created this category
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
cost_currency_id     -- Currency for cost price
selling_price        -- Default selling price
selling_currency_id  -- Currency for selling price
reorder_level        -- Minimum stock before reordering
image                -- Product image path/URL
is_active            -- Whether product is still sold
created_by_user_id   -- Who added this product
created_at
updated_at
deleted_at
```
**Example**: iPhone 15, barcode="123456789", cost_price=800, cost_currency_id=2(CNY), selling_price=3000, selling_currency_id=1(AED)

### 5. product_prices
**Purpose**: Historical pricing - tracks price changes over time. The is_current flag makes finding the active price trivial and allows for database-level integrity constraints.
```sql
id                   -- Primary key
product_id          -- Which product
cost_price          -- Purchase cost at this time
cost_currency_id    -- Cost price currency
selling_price       -- Selling price at this time
selling_currency_id -- Selling price currency
effective_date      -- When this price started
end_date           -- When this price ended (NULL for current if is_current is true)
is_current         -- (boolean) Is this the currently active price for this product?
created_by_user_id  -- Who changed the price
created_at
```
**Why**: Lets you see "iPhone cost was ¥5600 in January, ¥5800 in March; sold for AED3000 then AED3200"

## Location & Inventory Tables

### 6. addresses
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

### 7. locations
**Purpose**: Physical places where inventory is stored
```sql
id                 -- Primary key
name              -- Location name
address_id        -- Links to addresses table
location_type     -- ENUM: 'warehouse', 'store', 'supplier'
is_active         -- Whether location is operational
manager_id        -- Employee who manages this location
created_by_user_id -- Who created this location
created_at
updated_at
deleted_at
```
**Example**: "Main Store", "Downtown Warehouse", "Supplier ABC"

### 8. inventory
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

### 9. stock_movements
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

### 10. currencies
**Purpose**: All currencies used in the business
```sql
id                 -- Primary key
name              -- Currency name
code              -- ISO code (USD, EUR, CNY, AED, etc.)
symbol            -- Currency symbol ($, €, ¥, د.إ, etc.)
decimal_places    -- How many decimal places (USD=2, BTC=8, JPY=0)
is_active         -- Still in use?
created_at
updated_at
```
**Examples**:
- USD: decimal_places=2 ($10.50)
- Bitcoin: decimal_places=8 (0.00000001 BTC)
- Japanese Yen: decimal_places=0 (¥1000)

### 11. currency_rates
**Purpose**: Exchange rates from each currency to base currency
```sql
id                 -- Primary key
currency_id        -- Which currency this rate is for
rate              -- Exchange rate to base currency (1 CNY = 0.52 AED if AED is base)
effective_date    -- Date this rate applies from
created_at
```
**System**: Base currency defined in system_settings. All rates convert TO base currency.
**Example**: If AED is base currency:
- 1 USD = 3.67 AED (rate=3.67)
- 1 CNY = 0.52 AED (rate=0.52)

## Supplier & Purchase Management

### 12. vendors
**Purpose**: Companies/people we buy products from
```sql
id                 -- Primary key  
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
```

### 13. purchases
**Purpose**: Purchase orders/invoices from vendors
```sql
id                    -- Primary key
purchase_number      -- Our internal PO number
vendor_id           -- Who we're buying from
location_id         -- Which location will receive the goods
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

### 14. purchase_items
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
**Example**: Purchase #123 includes 50 iPhones at ¥5600 each = ¥280,000

## Customer Management

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
balance             -- Current amount they owe us (auto-calculated)
date_joined         -- When they became customer
status              -- ENUM: 'active', 'inactive', 'blocked'
notes              -- Additional information
photo_url           -- Customer photo path
created_by_user_id  -- Who added this customer
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
location_id          -- Which store/location made this sale
sale_date           -- When sale happened
subtotal            -- Total before discount/tax
discount_amount     -- Total discount given
tax_amount          -- Tax charged (0 if no tax system)
total_amount        -- Final amount customer pays
currency_id         -- Sale currency
payment_status      -- ENUM: 'paid', 'partial', 'pending'
status              -- ENUM: 'draft', 'completed', 'cancelled', 'refunded'
notes              -- Special instructions
created_by_user_id  -- Which employee made the sale
created_at
updated_at
```
**Status explanation**:
- 'draft': Sale being prepared, can be modified
- 'completed': Sale finalized, inventory updated
- 'cancelled': Sale cancelled before completion
- 'refunded': Sale was completed but later refunded

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
**Example**: Sale #789 includes 2 iPhones at AED3000 each, with AED100 discount

### 18. returns
**Purpose**: When customers return products
```sql
id                    -- Primary key
return_number        -- Unique return ID
original_sale_id     -- Which sale is being returned (contains location info)
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
**Note**: Location comes from original_sale_id.location_id

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
created_by_user_id -- Who set up this register
created_at
updated_at
```

### 21. cash_drawer_money
**Purpose**: How much cash is in each drawer, by currency
```sql
id                 -- Primary key
cash_drawer_id    -- Which drawer
currency_id       -- Which currency
amount            -- Current amount (calculated from transactions)
last_counted_date -- When last physically counted
created_at
updated_at
```
**Example**: Main Register has AED1500 and $200
**Important**: Amount should equal SUM of all transactions for this drawer+currency

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
transaction_type    -- ENUM: 'sale_payment', 'purchase_payment', 'expense', 'withdrawal', 'deposit'
reference_type      -- Source document: 'sale', 'purchase', 'payment', 'expense'
reference_id        -- ID of the source document
cash_drawer_id      -- Affected cash drawer (NULL if not cash)
created_by_user_id  -- Who created this transaction
created_at
```
**Key Design**: Cash drawer amounts = SUM of transactions where cash_drawer_id = drawer_id
**Example**: Customer pays AED100 cash for sale → Transaction: +AED100, cash_drawer_id=1, reference_type='sale', reference_id=sale_id

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
balance          -- Money owed to/by employee (auto-calculated)
created_by_user_id -- Who added this employee record
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
created_by_user_id  -- Who recorded this job change
created_at
updated_at
```
**Example**: John was "Cashier" from Jan-June (AED2000), then "Supervisor" from July-present (AED2500)

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
balance            -- Current account balance (auto-calculated)
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

### 34. users (Django User Model Extension)
**Purpose**: System login accounts - extends Django's AbstractUser
```sql
# Django provides: id, username, email, password, first_name, last_name, etc.
employee_id       -- Links to employee record (NULL for non-employees)
is_active         -- Can they log in? (Django built-in)
last_login_date   -- When they last accessed system (Django built-in as last_login)
created_at        -- Django built-in as date_joined
updated_at        -- Custom field
deleted_at        -- Soft delete
```

### 35. user_roles
**Purpose**: What each user is allowed to do
```sql
id                 -- Primary key
user_id           -- Which user
role_name         -- ENUM: 'admin', 'manager', 'cashier', 'inventory_clerk'
-- 'permissions' JSON field is REMOVED
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
**Example**: User John (id=5) updated product id=123, changed price from AED100 to AED120

### 37. permissions
**Purpose**: Defines a master list of every individual action that can be controlled within the system. This provides a single source of truth for all possible permissions.
```sql
id                 -- Primary key
name               -- Unique permission identifier (e.g., 'catalog.add_product')
description        -- User-friendly explanation of what this permission allows
created_at
```

### 38. role_permissions
**Purpose**: A many-to-many join table that links roles to permissions. This is where you grant specific permissions to a role.
```sql
id                 -- Primary key
role_id            -- FK to the user_roles table
permission_id      -- FK to the permissions table
-- UNIQUE constraint on (role_id, permission_id) to prevent duplicates
```

### 39. user_product_preferences
**Purpose**: Tracks individual user preferences for products, such as marking them as a "favorite" for quick access. This replaces the global flags on the products table.
```sql
user_id            -- Composite primary key part 1, FK to users table
product_id         -- Composite primary key part 2, FK to products table
is_favorite        -- (boolean) User has marked this as a favorite
is_loved           -- (boolean) Another user-specific flag (e.g., for a wishlist)
is_checked         -- (boolean) Another user-specific flag
created_at         -- When this preference was first set
-- PRIMARY KEY (user_id, product_id)
```

### 40. system_settings
**Purpose**: System-wide configuration options
```sql
id                 -- Primary key
setting_key       -- What setting (e.g., 'base_currency_id', 'tax_rate')
setting_value     -- The value
setting_type      -- ENUM: 'string', 'number', 'boolean', 'json'
description       -- What this setting does
category          -- Group settings ('general', 'inventory', 'sales')
updated_by_user_id -- Who last changed this
updated_at
created_at
```
**Examples**:
- setting_key='base_currency_id', setting_value='1' (AED)
- setting_key='tax_rate', setting_value='0.05' (5%)
- setting_key='low_stock_alert', setting_value='true'


## Key Relationships Summary

**Product Flow**: departments → categories → products → inventory → sales/purchases
**Money Flow**: currencies → currency_rates → all financial transactions → cash_drawers
**User Actions**: users → user_roles → activity_logs (everything tracked)
**Address System**: addresses table serves customers, vendors, locations (polymorphic)
**Audit Trail**: stock_movements + transactions + activity_logs = complete business history
**Currency System**: All currencies convert to base_currency (defined in system_settings)

## Business Process Flows

### 1. Making a Sale (Complete Flow):
```
1. CREATE sale record (status='draft', location_id=current_location)
2. ADD products to sale_items table
3. CALCULATE totals (subtotal, discount, tax, total)
4. UPDATE sale (status='completed')
5. CREATE stock_movements (products going 'out')
6. UPDATE inventory (reduce quantity_on_hand, reduce reserved_quantity)
7. WHEN customer pays:
   a. CREATE payment record
   b. CREATE transaction record (type='sale_payment', +amount)
   c. IF cash payment: UPDATE cash_drawer_money (+amount)
   d. UPDATE customer balance (if credit sale)
8. ALL actions logged in activity_logs
```

### 2. Receiving Purchase (Complete Flow):
```
1. CREATE purchase record (status='pending')
2. ADD products to purchase_items
3. WHEN goods arrive:
   a. UPDATE purchase (status='received', delivery_date=today)
   b. CREATE stock_movements (products coming 'in')
   c. UPDATE inventory (increase quantity_on_hand)
4. WHEN paying vendor:
   a. CREATE transaction record (type='purchase_payment', -amount)
   b. IF cash payment: UPDATE cash_drawer_money (-amount)
   c. UPDATE vendor balance
5. ALL actions logged in activity_logs
```

### 3. Processing a Return:
```
1. CREATE return record (status='pending')
2. ADD items to return_items
3. WHEN approved:
   a. UPDATE return (status='approved')
   b. IF restocked=true: CREATE stock_movements (+quantity)
   c. UPDATE inventory (increase quantity_on_hand)
4. WHEN refunding customer:
   a. CREATE transaction record (type='refund', -amount)
   b. IF cash refund: UPDATE cash_drawer_money (-amount)
   c. UPDATE customer balance
5. UPDATE return (status='completed')
```

### 4. Currency Conversion Flow:
```
1. ALL prices stored in original currency
2. WHEN displaying: convert using currency_rates to base_currency or user preferred currency
3. FORMULA: original_amount × currency_rate = base_currency_amount
4. EXAMPLE: Product costs ¥1000, rate=0.52 → AED520 equivalent
```

### 5. Cash Drawer Reconciliation:
```
1. PHYSICAL count cash in drawer
2. SYSTEM calculation: SUM(transactions WHERE cash_drawer_id=X)
3. COMPARE physical vs system
4. IF difference: CREATE inventory_adjustment for cash
5. UPDATE cash_drawer_money (last_counted_date=today)
```

### 6. Balance Synchronization (Automatic):
```
Vendor Balance = SUM(purchases.total_amount) - SUM(payments WHERE vendor_id=X)
Customer Balance = SUM(sales.total_amount) - SUM(payments WHERE customer_id=X)
Employee Balance = SUM(salary_payments) - SUM(advances WHERE employee_id=X)
Cash Drawer Amount = SUM(transactions WHERE cash_drawer_id=X AND currency_id=Y)
```

## Django Apps Structure

### 1. **core** app - Base/shared models
- units, currencies, currency_rates, system_settings, addresses

### 2. **catalog** app - Product catalog  
- departments, categories, products, product_prices

### 3. **inventory** app - Stock management
- locations, inventory, stock_movements, inventory_adjustments, inventory_counts, inventory_count_items

### 4. **vendors** app - Supplier management
- vendors, purchases, purchase_items

### 5. **customers** app - Customer management  
- customers

### 6. **sales** app - Sales operations
- sales, sale_items, returns, return_items

### 7. **finance** app - Financial management
- cash_drawers, cash_drawer_money, payments, transactions, expenses, expense_categories, monthly_payments

### 8. **hr** app - Human Resources
- employees, employee_positions, employee_careers, members

### 9. **accounts** app - User management
- users (Django extension), user_roles, activity_logs,user_product_preferences, permissions, role_permissions

## Implementation Notes

### Balance Fields Strategy:
- Keep balance fields for fast queries
- Update balances in same transaction when creating related records
- Use Django signals or model save() methods to maintain sync
- Provide management commands to recalculate all balances if needed

### Currency Handling:
- Store all amounts in original currency
- Convert for display using current exchange rates
- Base currency defined in system_settings (key=base_currency_id)
- Support for different decimal places per currency

### Transaction Design:
- Every financial movement creates a transaction record
- Complete audit trail maintained
- Reference fields link back to source documents (sales, purchases, etc.)

This design provides complete business management with full audit trails, multi-currency support, multi-location inventory, and proper financial tracking.