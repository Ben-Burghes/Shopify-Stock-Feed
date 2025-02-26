df = pd.read_csv(io.StringIO(record.body), names=[ 
    'client_order_ref', 
    'account', 
    'product_id', 
    'customer_product_id', 
    'description', 
    'product_uom_qty', 
    'price', 
    'customer_ref', 
    'contact', 
    'company', 
    'street', 
    'street2', 
    'city', 
    'state', 
    'postcode', 
    'country', 
    'phone', 
    'mobile', 
    'commitment_date', 
    'shipping_code', 
    'shipping_title', 
    'shipping_price', 
    'email', 
    'delivery_instructions' 
  ], encoding='latin_1') 
 
df = df.fillna('') 
 
 
# TODO: Make this group by the client_order_ref and then do it for each order 
 
# REPLACE ANY DF MENTIONS BELOW WITH GROUP 
# Check to see if this already exists 
for name, group in df.groupby(['client_order_ref']): 
   
  header = group.iloc[0] 
  partner_id = env['res.partner'].search([('ref', '=', header.account)],limit=1) 
  if not partner_id: 
    raise Exception("Partner not found for ref %s" % header.account) 
  ship_price = header.shipping_price 
   
  if env['sale.order']._count_existing_filtered_client_order_ref(partner_id, header.client_order_ref) < 1: 
     
    # if str(header['delivery_type']) != 'Next Day': 
    #   raise Exception("Unknown delivery type: %s" % str(header['delivery_type'])) 
       
    # try: 
    #   commitment_date = datetime.datetime.strptime(header.commitment_date, "%Y-%m-%d") 
    # except Exception: 
    #   commitment_date = datetime.datetime.now() + datetime.timedelta(days=1) 
     
    commitment_date = datetime.datetime.today() 
    if commitment_date.time() > datetime.time(16,30): 
      commitment_date += datetime.timedelta(days=1) 
 
       
    # default picking policy 
    model_product = env['product.product'].sudo() 
    sale_order_lines = [] 
    warehouse_id = None 
   
    shipping_partner = env['res.partner'].search_create({ 
      	'name' : header.contact, 
      	'zip' : header.postcode, 
      	'city': header.city, 
      	'street' : header.street, 
      	'street2' : header.street2, 
      	'state': header.state, # _find_or_create_partner_from_vals will auto convert this for us 
      	'country': header.country,  # _find_or_create_partner_from_vals will auto convert this for us 
      	'is_customer': True, 
      	'is_supplier': False, 
      	'type': 'delivery', 
      	'phone': header.phone, 
      	'mobile': header.mobile, 
      	'email': header.email, 
      	'third_party_company_name': header.company, 
        'is_direct': True, 
  	}, search_using={"zip": "ilike", "name": "=ilike", "third_party_company_name": "=", "street": "=", "phone": "=", "type": "=", "is_direct": "="}) 
       
    for index, line in group.iterrows(): 
      #raise Exception(line) 
      product = env['product.product'].search([ 
        ('default_code', '=', line.product_id) 
      ], limit=1) 
      #raise Exception(product,line.product_id) 
 
      if not product: 
        raise Exception("Unknown product %s on line %d" % (line.product_id, index)) 
     
      route_id = product.sale_order_line_route_id.id 
      if product.brand_id.name == 'Titan Furniture': 
        route_id = env['stock.location.route'].with_context(prefetch_fields=False).search([('name','=','Ship from TCM')],limit=1).id 
   
      dt_qty = sum(product.availability_ids.filtered(lambda a: a.warehouse_id.id == 1).mapped(lambda a: max(a.potential_qty, 0))) 
      titan_qty = sum(product.availability_ids.filtered(lambda a: a.warehouse_id.id == 18).mapped(lambda a: max(a.potential_qty, 0))) 
      tcm_qty = sum(product.availability_ids.filtered(lambda a: a.warehouse_id.id == 20).mapped(lambda a: max(a.potential_qty, 0))) 
       
      # Get next po date for product if out of stock. (ignoring MTO / Manufactured / Dropship) 
      if (dt_qty + titan_qty + tcm_qty) < int(line.product_uom_qty) and product.availability_classification == 'stocked': 
        record.message_post(body="PO Date: %s!" % (product.get_next_po()['date'])) 
        if product.get_next_po()['date'] != 0: 
          if product.get_next_po()['date'].replace(tzinfo=None) > commitment_date.replace(tzinfo=None): 
              commitment_date = (product.get_next_po()['date']).replace(tzinfo=None) 
        else: 
          record.message_post(body="No PO found for: %s!" % (line.product_id)) 
           
      sale_order_lines.append((0, 0, { 
        'backend_id': backend.id, 
        'product_id': product.id, 
        'product_uom_qty': line.product_uom_qty, 
        'price_unit': line.price, 
        'client_order_line_ref': index, 
        'route_id': route_id, 
      })) 
     
    # Setting this stuff after so if a product is on back order... 
    # the delivery method leadtime gets added to the new commitment date 
    carrier_id = None 
    dayoffset = None 
    if 'Next ' in str(header['shipping_title']): 
      carrier_id = env.ref('wwuk_delivery_type.delivery_carrier_next_day') 
      dayoffset = 1 
    elif 'Delivery & Installation' in str(header['shipping_title']): 
      carrier_id = env.ref('wwuk_delivery_type.delivery_carrier_installation') 
      dayoffset = 11 
    elif 'Economy' in str(header['shipping_title']): 
      carrier_id = env.ref('wwuk_delivery_type.delivery_carrier_five_seven') 
      dayoffset = 7 
    elif 'Highlands and Islands' in str(header['shipping_title']): 
      carrier_id = env.ref('wwuk_delivery_type.delivery_carrier_five_seven') 
      dayoffset = 7 
    else: 
      raise Exception("No delivery_type specified") 
     
    if carrier_id.warehouse_id: 
      warehouse_id = carrier_id.warehouse_id 
     
    if product.brand_id.name == 'Titan Furniture': 
      if product.availability_classification == 'manufactured': 
        dayoffset = 10 
      else: 
        dayoffset = 5 
      #commitment_date = commitment_date + titanLeadTime 
     
    while dayoffset > 0: 
      commitment_date += datetime.timedelta(days=1) 
      weekday = commitment_date.weekday() 
      if weekday >= 5: # sunday = 6 
          continue 
      dayoffset -= 1 
     
    if header.commitment_date: 
      header_date = datetime.datetime.strptime(header.commitment_date, '%Y-%m-%dT%H:%M:%S+00:00') 
      if header_date > commitment_date: 
        commitment_date = header_date 
    # check if commitment_date is on the weekend and if so bump it to monday 
   # if commitment_date.isoweekday() in set((6, 7)): 
    #  commitment_date += datetime.timedelta(days=datetime.datetime.today().isoweekday() % 5) 
     
    vals = { 
      'backend_id': backend.id, 
      'client_order_ref': header.client_order_ref, 
      'partner_id': partner_id.id, 
      'partner_shipping_id': shipping_partner.id, 
      'commitment_date': commitment_date, 
      'original_order_ref': 'Shopify Order', 
      'edi_external_id': header['client_order_ref'], 
      'edi_order_line_ids': sale_order_lines, 
      'edi_message_id': record.id, 
      #'warehouse_id': warehouse_id.id if warehouse_id else None, 
      'delivery_instructions' : header.delivery_instructions 
    } 
     
    sale_id = env['edi.sale.order'].create(vals) 
    record._associate_with(sale_id.odoo_id) 
    #sale_id.action_apply_carrier(carrier_id) 
    sale_id.odoo_id.set_delivery_line(carrier_id, ship_price) 
     
    # policy_hold = env['credit.control.policy'].search([('name','=','Test Order Hold')],limit=1) 
    # sale_id.odoo_id.action_credit_control_hold(policy_hold.rule_ids) 
     
    sale_id.with_context(__raise_on_zero_value=True).action_confirm() 
  else: 
    raise EdiException("Duplicate sale") 
  
