# Shopify API details
SHOPIFY_STORE = '***.myshopify.com'
ACCESS_TOKEN = '******'
PRODUCTS_ENDPOINT = f'https://{SHOPIFY_STORE}/admin/api/2024-01/graphql.json'
FIXED_LOCATION_ID = '******'
BATCH_SIZE = 100  # Number of items to update per API call
COMPANY_REF = '***'
route_id = env['edi.route'].search([('name', '=', 'Stock Feed OSM')], limit=1)


# Convert fixed location ID to Shopify global ID format
FIXED_LOCATION_GLOBAL_ID = base64.b64encode(f"gid://shopify/Location/{FIXED_LOCATION_ID}".encode()).decode()

# Read the content of the file
reader = csv.DictReader(io.StringIO(record.body))

original_results = list(reader)

output = io.StringIO()
writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

# Write the header row
writer.writerow([
    'Time',
    'Title',
    'Shopify Template ID',
    'Shopify Variant ID',
    'Shopify Inventory Item ID',
    'Shopify Current Stock',
    'Shopify Sku',
    'Odoo Sku',
    'Odoo Stock',
    'Success?',
    'Error Message',
    'GraphQL Query',
    'GraphQL Response',
    'Inventory Request URL',
    'Inventory Response',
])

query = """
select
    product_product.default_code as sku
from
    (select distinct product_id, pricelist_id from product_pricelist_cache) product_pricelist_cache
    join product_product on product_pricelist_cache.product_id = product_product.id
    join product_template on product_template.id = product_product.product_tmpl_id
where
    product_pricelist_cache.pricelist_id = %s
    and product_product.default_code is not null
    and product_product.default_code not in ('', 'NULL')
    and product_template.type = 'product'
    and product_product.active
    and product_template.active
group by
    product_product.default_code
"""

partner_id = env['res.partner'].search([('ref', '=', COMPANY_REF)], limit=1)

env.cr.execute(query, (partner_id.property_product_pricelist.id,))
pricelist_results = env.cr.fetchall()

# Convert pricelist SKUs to a set for quick lookup
pricelist_skus = {row[0] for row in pricelist_results}

# Filter original_results to only include rows with SKUs in pricelist_skus
results = [
    row for row in original_results if row.get("default_code") in pricelist_skus
]

 

# Collecting the bulk operations
bulk_operations = []
for result in results:
    product_id = result.get("product_id")
    if result.get("potential_qty", "") == "":
      potential_qty = 0
    else:
      potential_qty = int(float(result.get("potential_qty")))

    sku = result.get("default_code")
    warehouse_id = result.get("warehouse_id")
    date_added = result.get("date_added")
    colour = result.get("colour")

    shopify_info, error_message, graphql_query, graphql_response, inventory_response_text = get_product_by_sku(
        sku, PRODUCTS_ENDPOINT, ACCESS_TOKEN, FIXED_LOCATION_GLOBAL_ID
    )

    if shopify_info:
        inventory_id = shopify_info["inventory_item_id"]
        inventory_item_global_id = shopify_info["inventory_item_global_id"]
        current_shopify_stock = int(float(shopify_info["current_stock"]))

        if current_shopify_stock != potential_qty:
            if colour == "Unlimited":
                potential_qty = 0

            # Perform the subtraction after ensuring both are integers
            bulk_operations.append(f'{{inventoryItemId: "{inventory_item_global_id}", availableDelta: {potential_qty - current_shopify_stock}}}')
            status = "Pending Update"
            response_message = "Pending update"
        else:
            status = "No Change"
            response_message = "No update needed"

        writer.writerow([
            datetime.datetime.now(),
            shopify_info["product_title"],
            shopify_info["product_id"],
            shopify_info["variant_id"],
            shopify_info["inventory_item_id"],
            shopify_info["current_stock"],
            shopify_info["sku"],
            sku,
            potential_qty,
            status,
            response_message,
            graphql_query,
            graphql_response,
            inventory_response_text,
            "",
        ])
    else:
        writer.writerow([
            datetime.datetime.now(),
            "",
            "",
            "",
            "",
            "",
            "",
            sku,
            potential_qty,
            "FAILED",
            error_message,
            graphql_query,
            graphql_response,
            inventory_response_text,
            "",
        ])



# Executing the bulk update in batches and writing batch status to CSV
for i in range(0, len(bulk_operations), BATCH_SIZE):
    batch = bulk_operations[i:i + BATCH_SIZE]
    success, response_message = update_inventory_level_bulk(batch, PRODUCTS_ENDPOINT, ACCESS_TOKEN, FIXED_LOCATION_GLOBAL_ID)
    batch_status = "Success" if success else "Fail"
    writer.writerow([
        datetime.datetime.now(),
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
        batch_status,
        response_message,
        "BATCH",
        "BATCH",
        "BATCH",
        "BATCH",
    ])




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
