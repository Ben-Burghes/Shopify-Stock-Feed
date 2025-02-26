
# Shopify API details
FIXED_LOCATION_ID = '*****'
# Batching removed as inventoryAdjustQuantities does not support bulk operations
SHOPIFY_STORE = '****.myshopify.com' 
ACCESS_TOKEN = '*******' 
PRODUCTS_ENDPOINT = f'https://{SHOPIFY_STORE}/admin/api/2024-01/graphql.json' 

# Convert fixed location ID to Shopify global ID format
FIXED_LOCATION_GLOBAL_ID = f"gid://shopify/Location/{FIXED_LOCATION_ID}"

# Function to get product details by SKU

# Read CSV content
reader = csv.DictReader(io.StringIO(record.body))
results = list(reader)

output = io.StringIO()
writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
writer.writerow([
    'Time', 'Shopify Variant ID', 'Shopify Inventory Item ID', 'Current Shopify Stock',
    'Odoo Stock', 'Delta', 'SKU', 'Status', 'Response'
])

inventory_adjustments = []

for result in results:
    sku = result.get("default_code")
    potential_qty = int(float(result.get("potential_qty")))
    
    shopify_info, error_message = get_product_by_sku(sku, PRODUCTS_ENDPOINT, ACCESS_TOKEN, FIXED_LOCATION_GLOBAL_ID)
    
    if shopify_info:
        inventory_item_id = shopify_info["inventory_item_id"]
        current_shopify_quantity = shopify_info["current_stock"]
        delta = potential_qty - current_shopify_quantity
        
        inventory_adjustments.append({
            "inventoryItemId": inventory_item_id,
            "delta": delta,
            "locationId": FIXED_LOCATION_GLOBAL_ID,
        })
        status = "Pending Update"
        response_message = "Pending update"
        writer.writerow([
        datetime.datetime.now(),
        shopify_info["variant_id"],
        shopify_info.get("inventory_item_id", ""),
        current_shopify_quantity,
        potential_qty,
        delta,
        sku,
        status,
        response_message,
        ])
    else:
        status = "FAILED"
        response_message = error_message
        writer.writerow([
        datetime.datetime.now(),
        "#N/A",
        "#N/A",
        "#N/A",
        potential_qty,
        "#N/A",
        sku,
        status,
        response_message,
        ])
    


# Execute updates in batches
BATCH_SIZE = 100
for i in range(0, len(inventory_adjustments), BATCH_SIZE):
    batch = inventory_adjustments[i:i + BATCH_SIZE]
    success, response_message = update_stock_levels(batch, PRODUCTS_ENDPOINT, ACCESS_TOKEN)
    status = "Success" if success else "Fail"
    
    writer.writerow([
          datetime.datetime.now(),
          "BATCH",
          "BATCH",
          "BATCH",
          "BATCH",
          "BATCH",
          "BATCH",
          "BATCH",
          status,
          response_message
    ])

# Create EDI message
route_id = env['edi.route'].search([('name', '=', 'Stock Feed TC')], limit=1)
if not route_id:
    raise ValueError("Route ID not found for 'Stock Feed TC'.")

msg = env['edi.message'].create({
    'direction': 'out',
    'backend_id': backend.id,
    'body': output.getvalue(),
    'type': 'STOCK',
    'metadata': {},
    'message_route_id': route_id.id,
    'external_id': backend.message_sequence._next(),
})

msg.action_pending()
