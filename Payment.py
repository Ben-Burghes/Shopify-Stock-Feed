df = pd.read_csv(io.StringIO(record.body), names=[
      'id',
      'order_number',
      'account',
      'customer_email',
      'billing_name',
      'billing_address',
      'billing_city',
      'billing_country',
      'billing_zip',
      'line_item_name',
      'sku',
      'quantity',
      'price',
      'total_price',
      'subtotal_price',
      'shipping_price',
      'tax',
      'currency',
      'created_at',
      'confirmed',
      'payment_status'
  ], encoding='latin_1')

df = df.fillna('')

#df[created_at] = pd.to_datetime(df[created_at])
for index, group in df.groupby(['order_number']):
  header = group.iloc[0]
  partner =env['res.partner'].search([('ref', '=', header.account)], limit=1)
  if not partner:
    # Handle case where partner is not found
    continue  # Or create a new partner record

#payment_method = env.ref('account.account_payment_method_electronic_in')  # Example: Electronic payment


 #'payment_date': row['Created At'].date(),
payment_vals = {
      #'create_date': datetime.datetime.today(),
      #'write_date' : datetime.datetime.today(),
      'payment_reference' : header.order_number,
      'partner_id': partner.id,
      'currency_id': env['res.currency'].search([('name', '=', header.currency)], limit=1).id,
      #'partner_bank_id': N ,
      'payment_type': 'inbound',
      'amount' : header.total_price,
      'is_internal_transfer' : False ,
      'destination_account_id' : 91,
      'allocation_state' : 'allocated',
      'ref' : header.order_number,
    }
payment_id = env['account.payment'].create(payment_vals)
#record._associate_with(payment_id.odoo_id)
  
