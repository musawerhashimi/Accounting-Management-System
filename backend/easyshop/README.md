<blockquote data-sourcepos="63:1-91:117">
<h4 data-sourcepos="63:3-63:48"><strong>Technical Note: Cached Balance Fields</strong></h4>
<p data-sourcepos="65:3-65:25"><strong>Date:</strong> June 19, 2025</p>
<p data-sourcepos="67:3-67:313"><strong>Decision:</strong> The <code>balance</code> fields on the <code>customers</code>, <code>vendors</code>, <code>employees</code>, and <code>members</code> tables, as well as the <code>amount</code> in <code>cash_drawer_money</code>, are intentionally denormalized (cached) for performance reasons. This avoids costly real-time aggregations on large transaction tables during frequent operations.</p>
<p data-sourcepos="69:3-69:30"><strong>Implementation Strategy:</strong></p>
<ol data-sourcepos="71:3-78:1">
<li data-sourcepos="71:3-71:261"><strong>Atomic Updates:</strong> All balance updates <strong>must</strong> occur within the same database transaction as the event that triggers them. For example, when a <code>payment</code> is successfully created, the update to the <code>customers.balance</code> must be part of the same transaction.</li>
<li data-sourcepos="72:3-72:243"><strong>Use Django Signals/Model Methods:</strong> The update logic should be encapsulated within the <code>save()</code> method or triggered by <code>post_save</code> and <code>post_delete</code> signals of the source models (<code>payments</code>, <code>sales</code>, <code>purchases</code>, <code>transactions</code>, etc.).</li>
<li data-sourcepos="73:3-78:1"><strong>Example Flow (Customer Payment):</strong>
<ul data-sourcepos="74:9-78:1">
<li data-sourcepos="74:9-74:30"><code>START TRANSACTION;</code></li>
<li data-sourcepos="75:9-75:58"><code>INSERT</code> a new record into the <code>payments</code> table.</li>
<li data-sourcepos="76:9-76:99"><code>UPDATE customers SET balance = balance - payment.amount WHERE id = payment.customer_id;</code></li>
<li data-sourcepos="77:9-78:1"><code>COMMIT;</code></li>
</ul>
</li>
</ol>
<p data-sourcepos="79:3-79:22"><strong>Associated Risk:</strong></p>
<ul data-sourcepos="81:5-82:1">
<li data-sourcepos="81:5-82:1"><strong>Data Desynchronization:</strong> There is a risk that the cached balance can become out of sync with the sum of its source transactions if an update fails, a signal is missed, or a manual database change is made.</li>
</ul>
<p data-sourcepos="83:3-83:22"><strong>Mitigation Plan:</strong></p>
<ul data-sourcepos="85:5-91:117">
<li data-sourcepos="85:5-85:79">A Django management command, <code>recalculate_balances</code>, <strong>must be created</strong>.</li>
<li data-sourcepos="86:5-91:117"><strong>Functionality of <code>recalculate_balances</code>:</strong>
<ul data-sourcepos="87:9-91:117">
<li data-sourcepos="87:9-87:100">It will accept arguments to target specific models (e.g., <code>--model=customers</code> or <code>--all</code>).</li>
<li data-sourcepos="88:9-88:68">It will iterate through each record (e.g., each customer).</li>
<li data-sourcepos="89:9-89:126">For each record, it will perform a full calculation from the source of truth (the <code>transactions</code> or related tables).</li>
<li data-sourcepos="90:9-90:146">It will compare the calculated balance with the cached balance. If they differ, it will log the discrepancy and update the cached value.</li>
<li data-sourcepos="91:9-91:117">This command should be run periodically as a maintenance task and used to fix any reported inconsistencies.</li>
</ul>
</li>
</ul>
</blockquote>

Manage the indexes of the database

Improve Permissions Performance

Implement Subdomain Tenants

Ensure Tenants ar fully isolated

Add base currency to add purchase form



Connect Product Details to backend

Barcode Input/ Barcode Generator
Delete of Sales
