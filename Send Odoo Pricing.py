SHOPIFY_STORE = '****.myshopify.com'
ACCESS_TOKEN = ''
SHOPIFY_GRAPHQL_URL = f'https://{SHOPIFY_STORE}/admin/api/2024-01/graphql.json'

headers = {
    'X-Shopify-Access-Token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

customer_ref = record.external_id

partner = env['res.partner'].search([('ref','=',customer_ref)],limit=1)
if not partner:
    raise Exception("No partner found for %s" % customer_ref)

pricelist = partner.property_product_pricelist
if not pricelist:
    raise Exception("No pricelist for %s" % customer_ref)

## Get Company

query = """
query getCompanyByExternalId($externalId: String!) {
    companies(first: 1, query: $externalId) {
        edges {
            node {
                id
                externalId
                name
            }
        }
    }
}
"""

variables = {
    "externalId": customer_ref
}

response = requests.post(SHOPIFY_GRAPHQL_URL, json={ "query": query, "variables": variables}, headers=headers)

if response.status_code != 200:
    raise Exception(f"Error fetching product for company {customer_ref}: {response.status_code} {response.text}")

response_data = response.json()

if response_data.get("data") and response_data["data"]["companies"]["edges"]:
    company_gid = response_data["data"]["companies"]["edges"][0]["node"]["id"]
else:
    raise Exception("Company not found or invalid Company ID")

## GET PRICELIST DATA

shopify_pricelist_name = "2024 H2 Shopify Dealer Band 1 Header"
shopify_pricelist = env['product.pricelist'].search([('name','=',shopify_pricelist_name)],limit=1)
if not shopify_pricelist:
    raise Exception("Shopify pricelist not found with name %s" % shopify_pricelist_name)
shopify_products = list(set([p[3] for p in pricelist._get_products_tuple()]))

pricelist_cache_lines = env['product.pricelist.cache'].search([
    ('pricelist_id','=',pricelist.id),
    ('product_id','in',shopify_products)
])

if any(line.fixed_price == None for line in pricelist_cache_lines):
    raise Exception("Cache incomplete for pricelist %s, customer %s" % (pricelist.name, customer_ref))
if not pricelist_cache_lines:
    raise Exception("No cache for pricelist %s, customer %s" % (pricelist.name, customer_ref))

pricing_data = {}

for line in pricelist_cache_lines:
    sku = line.product_id.default_code
    if not line.carrier_id.ref:
        raise Exception("Internal Reference not set on carrier %s" % line.carrier_id.name)
    delivery_method = line.carrier_id.ref
    if sku not in pricing_data:
        pricing_data[sku] = {}
    if delivery_method not in pricing_data[sku]:
        pricing_data[sku][delivery_method] = line.fixed_price

## Split the pricing_data into multiple dicts

pricing_data_splits = []
pricing_data_master = {
  "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
  "delivery_methods": [carrier.ref for carrier in partner.carrier_ids],
  "currency" : {
      "code": pricelist.currency_id.name,
      "symbol": pricelist.currency_id.symbol
  },
  "data": {}
}

pricing_data_keys = sorted(pricing_data.keys())
counter = 0

limit = 400 # 2024 10 24 reduced to 400 from 500
for i in range(0, len(pricing_data_keys), limit):

    batch_keys = pricing_data_keys[i:i+limit]
    batch_dict = {sku: pricing_data[sku] for sku in batch_keys}
    first_product = batch_keys[0]
    last_product = batch_keys[-1]
    pricing_data_splits.append(batch_dict)
    pricing_data_master["data"][counter] = {
    'first': first_product,
    'last': last_product
    }
    counter += 1

output = ""

## Send all the pricing data

for index, pricing_data_split in enumerate(pricing_data_splits):
    mutation = f"""
    mutation {{
    metafieldsSet(
        metafields: [{{
        ownerId: "{company_gid}"
        namespace: "custom"
        key: "odoo_pricing_{index}"
        type: "json"
        value: {json.dumps(json.dumps(pricing_data_split))}
        }}]
    ) {{
        metafields {{
        id
        namespace
        key
        value
        }}
        userErrors {{
        field
        message
        }}
    }}
    }}
    """
    
    response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={'query': mutation})
    try:
      response_data = response.json()
    except:
      raise Exception(f"Error in response: {response}")

    if "errors" in response_data:
        raise Exception(f"Error: {response_data['errors']}")
    elif response_data["data"]["metafieldsSet"]["userErrors"]:
        raise Exception(f"User Errors: {response_data['data']['metafieldsSet']['userErrors']}")
    else:
        metafield = response_data["data"]["metafieldsSet"]["metafields"][0]
        output += f"Metafield updated successfully: {metafield}\n"

## Send the pricing data master record

mutation = f"""
mutation {{
metafieldsSet(
    metafields: [{{
    ownerId: "{company_gid}"
    namespace: "custom"
    key: "odoo_pricing_master"
    type: "json"
    value: {json.dumps(json.dumps(pricing_data_master))}
    }}]
) {{
    metafields {{
    id
    namespace
    key
    value
    }}
    userErrors {{
    field
    message
    }}
}}
}}
"""

response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={'query': mutation})
response_data = response.json()

if "errors" in response_data:
    raise Exception(f"Error: {response_data['errors']}")
elif response_data["data"]["metafieldsSet"]["userErrors"]:
    raise Exception(f"User Errors: {response_data['data']['metafieldsSet']['userErrors']}")
else:
    metafield = response_data["data"]["metafieldsSet"]["metafields"][0]
    output += f"Metafield updated successfully: {metafield}\n"



