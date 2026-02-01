<details>
  <summary>
    <strong>Click to expand the full list of permissions</strong>
  <summary>
  <ul data-sourcepos="148:3-211:0">
  <li data-sourcepos="148:3-155:0">
  <p data-sourcepos="148:5-148:47"><strong>System &amp; User Management (accounts)</strong></p>
  <ul data-sourcepos="150:7-155:0">
  <li data-sourcepos="150:7-150:74"><code>accounts.manage_users</code>: Create, update, and delete user accounts.</li>
  <li data-sourcepos="151:7-151:77"><code>accounts.manage_roles</code>: Create roles and assign permissions to them.</li>
  <li data-sourcepos="152:7-152:55"><code>accounts.assign_roles</code>: Assign roles to users.</li>
  <li data-sourcepos="153:7-153:72"><code>accounts.view_activity_log</code>: View the system-wide activity log.</li>
  <li data-sourcepos="154:7-155:0"><code>accounts.change_system_settings</code>: Modify entries in the <code>system_settings</code> table.</li>
  </ul>
  </li>
  <li data-sourcepos="156:3-164:0">
  <p data-sourcepos="156:5-156:33"><strong>Product Catalog (catalog)</strong></p>
  <ul data-sourcepos="158:7-164:0">
  <li data-sourcepos="158:7-158:62"><code>catalog.view_product</code>: View product list and details.</li>
  <li data-sourcepos="159:7-159:64"><code>catalog.add_product</code>: Add a new product to the catalog.</li>
  <li data-sourcepos="160:7-160:69"><code>catalog.change_product</code>: Edit an existing product's details.</li>
  <li data-sourcepos="161:7-161:51"><code>catalog.delete_product</code>: Delete a product.</li>
  <li data-sourcepos="162:7-162:83"><code>catalog.change_product_price</code>: Modify the cost/selling price of a product.</li>
  <li data-sourcepos="163:7-164:0"><code>catalog.manage_categories</code>: Add, edit, or delete categories and departments.</li>
  </ul>
  </li>
  <li data-sourcepos="165:3-175:0">
  <p data-sourcepos="165:5-165:40"><strong>Inventory Management (inventory)</strong></p>
  <ul data-sourcepos="167:7-175:0">
  <li data-sourcepos="167:7-167:78"><code>inventory.view_stock_levels</code>: View quantity on hand at all locations.</li>
  <li data-sourcepos="168:7-168:82"><code>inventory.view_stock_movements</code>: View the detailed stock movement ledger.</li>
  <li data-sourcepos="169:7-169:81"><code>inventory.manage_locations</code>: Add, edit, or delete warehouses and stores.</li>
  <li data-sourcepos="170:7-170:87"><code>inventory.create_stock_transfer</code>: Initiate a stock transfer between locations.</li>
  <li data-sourcepos="171:7-171:77"><code>inventory.approve_stock_transfer</code>: Approve a pending stock transfer.</li>
  <li data-sourcepos="172:7-172:97"><code>inventory.create_inventory_adjustment</code>: Manually adjust stock levels (e.g., for damage).</li>
  <li data-sourcepos="173:7-173:93"><code>inventory.approve_inventory_adjustment</code>: Approve a stock adjustment (manager-level).</li>
  <li data-sourcepos="174:7-175:0"><code>inventory.perform_inventory_count</code>: Initiate and perform a physical stock count.</li>
  </ul>
  </li>
  <li data-sourcepos="176:3-185:0">
  <p data-sourcepos="176:5-176:35"><strong>Sales &amp; Returns (sales)</strong></p>
  <ul data-sourcepos="178:7-185:0">
  <li data-sourcepos="178:7-178:75"><code>sales.create_sale</code>: Create a new sale transaction (cashier-level).</li>
  <li data-sourcepos="179:7-179:57"><code>sales.apply_discount</code>: Apply discounts to sales.</li>
  <li data-sourcepos="180:7-180:62"><code>sales.cancel_sale</code>: Cancel a draft or completed sale.</li>
  <li data-sourcepos="181:7-181:61"><code>sales.view_sales_history</code>: View a list of all sales.</li>
  <li data-sourcepos="182:7-182:68"><code>sales.view_sales_reports</code>: Access aggregated sales reports.</li>
  <li data-sourcepos="183:7-183:69"><code>sales.process_return</code>: Create and process a customer return.</li>
  <li data-sourcepos="184:7-185:0"><code>sales.override_sale_price</code>: Allow selling an item for a price different from the list price.</li>
  </ul>
  </li>
  <li data-sourcepos="186:3-194:0">
  <p data-sourcepos="186:5-186:42"><strong>Purchasing &amp; Vendors (vendors)</strong></p>
  <ul data-sourcepos="188:7-194:0">
  <li data-sourcepos="188:7-188:70"><code>vendors.view_vendor</code>: View list of vendors and their details.</li>
  <li data-sourcepos="189:7-189:63"><code>vendors.manage_vendors</code>: Add, edit, or delete vendors.</li>
  <li data-sourcepos="190:7-190:69"><code>vendors.create_purchase_order</code>: Create a new purchase order.</li>
  <li data-sourcepos="191:7-191:73"><code>vendors.approve_purchase_order</code>: Approve a PO before it is sent.</li>
  <li data-sourcepos="192:7-192:84"><code>vendors.receive_purchase_order</code>: Mark a PO as received, updating inventory.</li>
  <li data-sourcepos="193:7-194:0"><code>vendors.view_purchase_history</code>: View all purchase orders.</li>
  </ul>
  </li>
  <li data-sourcepos="195:3-204:0">
  <p data-sourcepos="195:5-195:38"><strong>Financial Management (finance)</strong></p>
  <ul data-sourcepos="197:7-204:0">
  <li data-sourcepos="197:7-197:79"><code>finance.view_transactions</code>: View the master financial transaction log.</li>
  <li data-sourcepos="198:7-198:78"><code>finance.manage_payments</code>: Record, view, and manage customer payments.</li>
  <li data-sourcepos="199:7-199:82"><code>finance.manage_expenses</code>: Create, edit, and categorize business expenses.</li>
  <li data-sourcepos="200:7-200:71"><code>finance.approve_expenses</code>: Approve expense claims for payment.</li>
  <li data-sourcepos="201:7-201:79"><code>finance.manage_cash_drawers</code>: Open, close, and reconcile cash drawers.</li>
  <li data-sourcepos="202:7-202:88"><code>finance.view_financial_reports</code>: Access profit &amp; loss, balance sheets, etc.</li>
  <li data-sourcepos="203:7-204:0"><code>finance.manage_currencies</code>: Add new currencies and update exchange rates.</li>
  </ul>
  </li>
  <li data-sourcepos="205:3-211:0">
  <p data-sourcepos="205:5-205:28"><strong>Human Resources (hr)</strong></p>
  <ul data-sourcepos="207:7-211:0">
  <li data-sourcepos="207:7-207:82"><code>hr.view_employee_list</code>: See a list of all employees and their basic info.</li>
  <li data-sourcepos="208:7-208:95"><code>hr.view_employee_sensitive_data</code>: View private employee data (salary, career history).</li>
  <li data-sourcepos="209:7-209:73"><code>hr.manage_employees</code>: Add, edit, and terminate employee records.</li>
  <li data-sourcepos="210:7-211:0"><code>hr.manage_salaries</code>: Change an employee's salary and position.</li>
  </ul>
  </li>
  </ul>
</details>
