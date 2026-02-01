📦 1. Model: core.models.Tenant
------------------------------------------------------------
🔹 id: BigAutoField
🔹 name: CharField
🔹 domain: CharField
🔹 contact_email: CharField
🔹 contact_phone: CharField
🔹 business_type: CharField
🔹 status: CharField
🔹 trial_ends_at: DateTimeField
🔹 subscription_plan: CharField
🔹 max_users: PositiveIntegerField
🔹 max_locations: PositiveIntegerField
🔹 max_storage_mb: PositiveIntegerField

📦 2. Model: core.models.TenantSettings
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 setting_key: CharField
🔹 setting_value: TextField
🔹 setting_image: FileField
🔹 setting_type: CharField
🔹 description: TextField
🔹 category: CharField

📦 3. Model: core.models.Currency
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 code: CharField
🔹 symbol: CharField
🔹 decimal_places: PositiveSmallIntegerField
🔹 is_base_currency: BooleanField
🔹 is_active: BooleanField

📦 4. Model: core.models.CurrencyRate
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 currency: ForeignKey → Currency
🔹 rate: DecimalField
🔹 effective_date: DateTimeField

📦 5. Model: core.models.TenantSubscription
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 plan_name: CharField
🔹 price: DecimalField
🔹 currency: ForeignKey → Currency
🔹 billing_cycle: CharField
🔹 current_period_start: DateTimeField
🔹 current_period_end: DateTimeField
🔹 status: CharField
🔹 payment_method: CharField
🔹 next_billing_date: DateTimeField

📦 6. Model: core.models.Unit
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 abbreviation: CharField
🔹 unit_type: CharField
🔹 base_unit: ForeignKey → Unit
🔹 conversion_factor: DecimalField
🔹 is_base_unit: BooleanField

📦 7. Model: core.models.Address
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 addressable_type: ForeignKey → ContentType
🔹 addressable_id: PositiveIntegerField
🔹 address_type: CharField
🔹 address_line_1: CharField
🔹 address_line_2: CharField
🔹 city: CharField
🔹 state: CharField
🔹 postal_code: CharField
🔹 country: CharField
🔹 is_default: BooleanField
🔹 created_by_user: ForeignKey → User

📦 8. Model: core.models.Permission
------------------------------------------------------------
🔹 id: BigAutoField
🔹 action: CharField
🔹 description: TextField
🔹 module: CharField

📦 9. Model: core.models.ActivityLog
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 user: ForeignKey → User
🔹 action: CharField
🔹 table_name: CharField
🔹 record_id: PositiveIntegerField
🔹 old_values: JSONField
🔹 new_values: JSONField
🔹 ip_address: GenericIPAddressField
🔹 user_agent: TextField
🔹 session_id: CharField
🔹 timestamp: DateTimeField

📦 10. Model: accounts.models.Employee
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 phone: CharField
🔹 email: CharField
🔹 hire_date: DateField
🔹 status: CharField
🔹 balance: DecimalField
🔹 created_by_user: ForeignKey → User

📦 11. Model: accounts.models.User
------------------------------------------------------------
🔹 id: BigAutoField
🔹 password: CharField
🔹 last_login: DateTimeField
🔹 is_superuser: BooleanField
🔹 username: CharField
🔹 first_name: CharField
🔹 last_name: CharField
🔹 email: CharField
🔹 is_staff: BooleanField
🔹 is_active: BooleanField
🔹 date_joined: DateTimeField
🔹 tenant: ForeignKey → Tenant
🔹 photo: FileField
🔹 phone: CharField
🔹 employee: ForeignKey → Employee
🔹 role_name: CharField
🔹 last_login_date: DateTimeField
🔹 preferred_currency: ForeignKey → Currency
🔹 location: ForeignKey → Location
🔹 language_preference: CharField
🔹 timezone: CharField
🔹 theme: CharField

📦 12. Model: accounts.models.UserPermission
------------------------------------------------------------
🔹 id: BigAutoField
🔹 user: ForeignKey → User
🔹 permission: ForeignKey → Permission
🔹 allow: BooleanField

📦 13. Model: accounts.models.RolePermission
------------------------------------------------------------
🔹 id: BigAutoField
🔹 role_name: CharField
🔹 permission: ForeignKey → Permission

📦 14. Model: accounts.models.UserProductPreference
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 user: ForeignKey → User
🔹 variant: ForeignKey → ProductVariant
🔹 is_favorite: BooleanField
🔹 is_bookmarked: BooleanField
🔹 is_loved: BooleanField

📦 15. Model: catalog.models.Department
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 description: TextField
🔹 is_active: BooleanField
🔹 created_by_user: ForeignKey → User

📦 16. Model: catalog.models.Category
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 department: ForeignKey → Department
🔹 name: CharField
🔹 description: TextField
🔹 is_active: BooleanField
🔹 created_by_user: ForeignKey → User

📦 17. Model: catalog.models.Product
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 category: ForeignKey → Category
🔹 base_unit: ForeignKey → Unit
🔹 description: TextField
🔹 reorder_level: IntegerField
🔹 has_variants: BooleanField
🔹 is_active: BooleanField
🔹 created_by_user: ForeignKey → User

📦 18. Model: catalog.models.ProductVariant
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 product: ForeignKey → Product
🔹 sku: CharField
🔹 variant_name: CharField
🔹 image: FileField
🔹 barcode: CharField
🔹 is_default: BooleanField
🔹 is_active: BooleanField
🔹 created_by_user: ForeignKey → User

📦 19. Model: catalog.models.ProductPrice
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 variant: ForeignKey → ProductVariant
🔹 product: ForeignKey → Product
🔹 cost_price: DecimalField
🔹 cost_currency: ForeignKey → Currency
🔹 selling_price: DecimalField
🔹 selling_currency: ForeignKey → Currency
🔹 effective_date: DateTimeField
🔹 end_date: DateTimeField
🔹 is_current: BooleanField
🔹 created_by_user: ForeignKey → User

📦 20. Model: inventory.models.Location
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 address: CharField
🔹 location_type: CharField
🔹 is_active: BooleanField
🔹 manager: ForeignKey → Employee
🔹 created_by_user: ForeignKey → User

📦 21. Model: inventory.models.ProductBatch
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 variant: ForeignKey → ProductVariant
🔹 batch_number: CharField
🔹 manufacture_date: DateField
🔹 expiry_date: DateField
🔹 supplier_batch_ref: CharField
🔹 notes: TextField
🔹 is_active: BooleanField

📦 22. Model: inventory.models.Inventory
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 location: ForeignKey → Location
🔹 quantity_on_hand: DecimalField
🔹 reserved_quantity: DecimalField
🔹 reorder_level: DecimalField
🔹 last_counted_date: DateTimeField

📦 23. Model: inventory.models.StockMovement
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 location: ForeignKey → Location
🔹 movement_type: CharField
🔹 quantity: DecimalField
🔹 reference_type: CharField
🔹 reference_id: PositiveIntegerField
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 24. Model: inventory.models.InventoryAdjustment
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 adjustment_number: CharField
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 location: ForeignKey → Location
🔹 adjustment_quantity: DecimalField
🔹 reason: CharField
🔹 cost_impact: DecimalField
🔹 currency: ForeignKey → Currency
🔹 notes: TextField
🔹 approved_by_user: ForeignKey → User
🔹 created_by_user: ForeignKey → User
🔹 adjustment_date: DateTimeField

📦 25. Model: inventory.models.InventoryCount
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 count_number: CharField
🔹 location: ForeignKey → Location
🔹 count_date: DateTimeField
🔹 status: CharField
🔹 total_items_counted: PositiveIntegerField
🔹 variances_found: PositiveIntegerField
🔹 created_by_user: ForeignKey → User
🔹 completed_by_user: ForeignKey → User

📦 26. Model: inventory.models.InventoryCountItem
------------------------------------------------------------
🔹 id: BigAutoField
🔹 count: ForeignKey → InventoryCount
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 system_quantity: DecimalField
🔹 counted_quantity: DecimalField
🔹 variance: DecimalField
🔹 notes: TextField
🔹 counted_by_user: ForeignKey → User

📦 27. Model: vendors.models.Vendor
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 photo: FileField
🔹 phone: CharField
🔹 email: CharField
🔹 tax_id: CharField
🔹 balance: DecimalField
🔹 status: CharField
🔹 created_by_user: ForeignKey → User

📦 28. Model: vendors.models.Purchase
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 purchase_number: CharField
🔹 vendor: ForeignKey → Vendor
🔹 location: ForeignKey → Location
🔹 purchase_date: DateTimeField
🔹 delivery_date: DateTimeField
🔹 subtotal: DecimalField
🔹 tax_amount: DecimalField
🔹 total_amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 status: CharField
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 29. Model: vendors.models.PurchaseItem
------------------------------------------------------------
🔹 id: BigAutoField
🔹 purchase: ForeignKey → Purchase
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 quantity: DecimalField
🔹 unit_cost: DecimalField
🔹 line_total: DecimalField
🔹 received_quantity: DecimalField

📦 30. Model: finance.models.CashDrawer
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 location: ForeignKey → Location
🔹 description: CharField
🔹 is_active: BooleanField
🔹 created_by_user: ForeignKey → User

📦 31. Model: finance.models.CashDrawerMoney
------------------------------------------------------------
🔹 id: BigAutoField
🔹 cash_drawer: ForeignKey → CashDrawer
🔹 currency: ForeignKey → Currency
🔹 amount: DecimalField
🔹 last_counted_date: DateTimeField

📦 32. Model: finance.models.Payment
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 payment_number: CharField
🔹 amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 payment_method: CharField
🔹 payment_date: DateTimeField
🔹 reference_type: CharField
🔹 reference_id: PositiveIntegerField
🔹 cash_drawer: ForeignKey → CashDrawer
🔹 card_transaction_id: CharField
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 33. Model: finance.models.Transaction
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 transaction_date: DateTimeField
🔹 amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 description: CharField
🔹 party_type: CharField
🔹 party_id: PositiveIntegerField
🔹 transaction_type: CharField
🔹 reference_type: CharField
🔹 reference_id: PositiveIntegerField
🔹 cash_drawer: ForeignKey → CashDrawer
🔹 created_by_user: ForeignKey → User
🔹 is_direct: BooleanField

📦 34. Model: finance.models.ExpenseCategory
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 description: TextField
🔹 parent_category: ForeignKey → ExpenseCategory
🔹 is_active: BooleanField

📦 35. Model: finance.models.Expense
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 expense_number: CharField
🔹 expense_category: ForeignKey → ExpenseCategory
🔹 amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 expense_date: DateTimeField
🔹 cash_drawer: ForeignKey → CashDrawer
🔹 description: TextField
🔹 payment_method: CharField
🔹 created_by_user: ForeignKey → User

📦 36. Model: finance.models.MonthlyPayment
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 payment_method: CharField
🔹 start_date: DateField
🔹 end_date: DateField
🔹 payment_day: PositiveIntegerField
🔹 reference_type: CharField
🔹 reference_id: PositiveIntegerField
🔹 is_active: BooleanField
🔹 description: TextField

📦 37. Model: customers.models.Customer
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 customer_number: CharField
🔹 name: CharField
🔹 gender: CharField
🔹 birth_date: DateField
🔹 email: CharField
🔹 phone: CharField
🔹 customer_type: CharField
🔹 discount_percentage: FloatField
🔹 tax_exempt: BooleanField
🔹 balance: DecimalField
🔹 date_joined: DateField
🔹 status: CharField
🔹 notes: TextField
🔹 photo: FileField
🔹 created_by_user: ForeignKey → User
🔹 preferred_currency: ForeignKey → Currency
🔹 address: CharField
🔹 city: CharField

📦 38. Model: customers.models.CustomerStatement
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 customer: ForeignKey → Customer
🔹 amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 statement_type: CharField
🔹 statement_date: DateTimeField
🔹 sale: ForeignKey → Sales
🔹 cash_drawer: ForeignKey → CashDrawer
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 39. Model: sales.models.Sales
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 sale_number: CharField
🔹 receipt_id: CharField
🔹 customer: ForeignKey → Customer
🔹 sale_date: DateTimeField
🔹 subtotal: DecimalField
🔹 discount_amount: DecimalField
🔹 tax_amount: DecimalField
🔹 total_amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 payment_status: CharField
🔹 status: CharField
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 40. Model: sales.models.SaleItem
------------------------------------------------------------
🔹 id: BigAutoField
🔹 sale: ForeignKey → Sales
🔹 inventory: ForeignKey → Inventory
🔹 quantity: DecimalField
🔹 unit_price: DecimalField
🔹 line_total: DecimalField
🔹 discount_amount: DecimalField

📦 41. Model: sales.models.Returns
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 return_number: CharField
🔹 original_sale: ForeignKey → Sales
🔹 customer: ForeignKey → Customer
🔹 return_date: DateTimeField
🔹 reason: CharField
🔹 total_refund_amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 status: CharField
🔹 processed_by_user: ForeignKey → User

📦 42. Model: sales.models.ReturnItem
------------------------------------------------------------
🔹 id: BigAutoField
🔹 return_order: ForeignKey → Returns
🔹 sale_item: ForeignKey → SaleItem
🔹 variant: ForeignKey → ProductVariant
🔹 batch: ForeignKey → ProductBatch
🔹 quantity_returned: DecimalField
🔹 condition: CharField
🔹 refund_amount: DecimalField
🔹 restocked: BooleanField

📦 43. Model: hr.models.EmployeePosition
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 position_name: CharField
🔹 base_salary: DecimalField
🔹 currency: ForeignKey → Currency
🔹 description: TextField
🔹 is_active: BooleanField

📦 44. Model: hr.models.EmployeeCareer
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 employee: ForeignKey → Employee
🔹 position: ForeignKey → EmployeePosition
🔹 start_date: DateField
🔹 end_date: DateField
🔹 salary: DecimalField
🔹 currency: ForeignKey → Currency
🔹 status: CharField
🔹 notes: TextField
🔹 created_by_user: ForeignKey → User

📦 45. Model: hr.models.Member
------------------------------------------------------------
🔹 id: BigAutoField
🔹 tenant: ForeignKey → Tenant
🔹 name: CharField
🔹 ownership_percentage: DecimalField
🔹 investment_amount: DecimalField
🔹 currency: ForeignKey → Currency
🔹 start_date: DateField
🔹 end_date: DateField
🔹 balance: DecimalField
🔹 status: CharField
