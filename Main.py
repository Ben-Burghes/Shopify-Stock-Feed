all_results = []

# Iterate over companies and regions
for company, regions in company_region_mapping.items():
    # Build a query that fetches data for the required regions
    query = f"""
    WITH cte_regions AS (
        SELECT
            * 
        FROM (VALUES 
            (1, 'UK'),
            (8, 'UK'),
            (10, 'UK'),
            (20, 'UK'),
            (19, 'IRE'),
            (21, 'GER')
        ) AS data(warehouse_id, region)
    )
    ,cte_products AS (
        SELECT DISTINCT
            stock_availability_dirty_shopify.product_id,
            cte_regions.region,
            stock_availability_dirty_shopify.date_added
        FROM
            stock_availability_dirty_shopify
            INNER JOIN cte_regions ON stock_availability_dirty_shopify.warehouse_id = cte_regions.warehouse_id
    )
    SELECT 
        cte_products.product_id,
        SUM(stock_availability.potential_qty) AS potential_qty,
        COALESCE(product_partner_alias.name, product_product.default_code) AS default_code,
        cte_regions.region,
        cte_products.date_added,
        product_product.colour
    FROM
        cte_products
        LEFT JOIN cte_regions ON cte_products.region = cte_regions.region
        LEFT JOIN stock_availability
            ON stock_availability.product_id = cte_products.product_id
            AND stock_availability.warehouse_id = cte_regions.warehouse_id
        LEFT JOIN product_product ON product_product.id = cte_products.product_id
        LEFT JOIN (
            SELECT * FROM product_partner_alias WHERE partner_id IN (SELECT id FROM res_partner WHERE ref = 'SHOPIFY')
        ) product_partner_alias ON stock_availability.product_id = product_partner_alias.product_id
    WHERE 
        product_product.shopify_product = TRUE
        AND potential_qty IS NOT NULL
        AND cte_regions.region IN ({', '.join(f"'{region}'" for region in regions)})
    GROUP BY 
        cte_products.product_id, 
        product_partner_alias.name,
        product_product.default_code,
        cte_regions.region,
        cte_products.date_added, 
        product_product.colour 
    ORDER BY 
        cte_products.date_added ASC
    LIMIT 1000
    """

    # Execute the query and fetch results
    env.cr.execute(query)
    company_results = env.cr.fetchall()

    # Process results for the company
    if company_results:
        all_results.extend(company_results)

        # Write results into EDI message
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow([
            "product_id", 
            "potential_qty", 
            "default_code", 
            "region", 
            "date_added", 
            "colour"
        ])

        # Write the data rows
        for row in company_results:
            writer.writerow(row)

        # Create the EDI message
        msg = env['edi.message'].create({ 
            'direction': 'in', 
            'backend_id': backend.id, 
            'body': output.getvalue(),
            'type': 'STOCK', 
            'metadata': {}, 
            'message_route_id': env['edi.route'].search(
                [
                    ('name', '=', company),
                    ('backend_id', '=', backend.id)
                ], limit=1).id, 
            'external_id': backend.message_sequence._next(), 
        })
        msg.action_pending()

        # Collect product IDs and regions for deletion

        delete_product_wh = ["%s-%s" % (row[0], warehouse_id)
                              for row in company_results
                              for warehouse_id in region_warehouses.get(row[3], [])]

        if delete_product_wh:
            delete_query = f"""
             DELETE FROM stock_availability_dirty_shopify
            WHERE concat(product_id, '-', warehouse_id) = ANY(ARRAY[{', '.join(f"'{x}'" for x in delete_product_wh)}])
            """
           # Execute the query
            env.cr.execute(delete_query)
