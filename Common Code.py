
##############################################
# READ ME
################################################
region_warehouses = {
    "IRE": [19],                # Warehouses for Ireland
    "UK": [1, 8, 10, 20],      # Warehouses for the UK
    "GER": [21]                # Warehouses for Germany
}


# Define companies and their required regions
company_region_mapping = {
    #"Stock Feed IRE": ["IRE"],
    "Stock Feed TC": ["UK"]
    #"Stock Feed OSM": ["GER"]
}

def get_product_by_sku(sku, PRODUCTS_ENDPOINT, ACCESS_TOKEN, FIXED_LOCATION_GLOBAL_ID):
    headers = {
        'X-Shopify-Access-Token': ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }

    query = """
    {
        productVariants(first: 1, query: "sku:%s") {
            edges {
                node {
                    id
                    title
                    sku
                    inventoryItem {
                        id
                        inventoryLevel(locationId: "%s") {
                            available
                        }
                    }
                    product {
                        id
                        title
                    }
                }
            }
        }
    }
    """ % (sku, FIXED_LOCATION_GLOBAL_ID)

    graphql_response = requests.post(PRODUCTS_ENDPOINT, headers=headers, json={'query': query})
    
    if graphql_response.status_code != 200:
        return None, f"Error fetching product for SKU {sku}: {graphql_response.status_code} {graphql_response.text}", query, graphql_response.text, ""

    data = graphql_response.json()
    
    if 'data' not in data or 'productVariants' not in data['data']:
        return None, f"Invalid response structure: {data}", query, graphql_response.text, ""

    variants = data['data']['productVariants']['edges']
    if not variants:
        return None, "No data found", query, graphql_response.text, ""

    variant = variants[0]['node']
    inventory_item_id_full = variant['inventoryItem']['id']
    inventory_item_id = inventory_item_id_full.split('/')[-1]
    inventory_item_global_id = base64.b64encode(f"gid://shopify/InventoryItem/{inventory_item_id}".encode()).decode()
    product_id = variant['product']['id'].split('/')[-1]
    product_title = variant['product']['title']
    variant_id = variant['id'].split('/')[-1]
    variant_title = variant['title']
    sku = variant['sku']

    # Location-specific stock level
    inventory_level = variant['inventoryItem'].get('inventoryLevel')
    current_stock = inventory_level['available'] if inventory_level else None

    return {
        'product_id': product_id,
        'product_title': product_title,
        'variant_id': variant_id,
        'sku': sku,
        'inventory_item_id': inventory_item_id,
        'inventory_item_global_id': inventory_item_global_id,
        'current_stock': current_stock,
    }, "Success", query, graphql_response.text, ""




def update_inventory_level_bulk(operations,PRODUCTS_ENDPOINT,ACCESS_TOKEN,FIXED_LOCATION_GLOBAL_ID):
    headers = {
        'X-Shopify-Access-Token': ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    mutation = """
    mutation {
        inventoryBulkAdjustQuantityAtLocation(locationId: "%s", inventoryItemAdjustments: [%s]) {
            inventoryLevels {
                available
            }
            userErrors {
                field
                message
            }
        }
    }
    """ % (FIXED_LOCATION_GLOBAL_ID, ','.join(operations))

    response = requests.post(PRODUCTS_ENDPOINT, headers=headers, json={'query': mutation})
    
    if response.status_code != 200:
        return False, f"Error updating inventory levels: {response.status_code} {response.text}"
    
    response_data = response.json()
    if 'data' not in response_data:
        return False, f"Invalid response structure: {response_data}"

    if 'errors' in response_data or response_data.get('data', {}).get('inventoryBulkAdjustQuantityAtLocation', {}).get('userErrors', []):
        return False, f"Error updating inventory levels: {response_data.get('errors', response_data['data']['inventoryBulkAdjustQuantityAtLocation']['userErrors'])}"
    
    return True, "Successfully updated stock"



