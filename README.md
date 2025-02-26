# Shopify Stock & Pricing Management

## Overview
This project automates stock and pricing synchronization between Odoo and Shopify using FTP-based EDI messages and Shopify's GraphQL API.

## Features
- **Stock Management**: Updates Shopify stock levels based on Odoo inventory.
- **Pricing Synchronization**: Sends Odoo pricing data to Shopify.
- **FTP Integration**: Uses EDI messages for stock feeds.
- **Shopify API Integration**: Utilizes GraphQL to update stock and pricing.

## Files in the Repository
- `Common Code.txt`: Shared functions for Shopify API integration.
- `Main.txt`: Core script that processes stock feeds and sends updates.
- `Send Odoo Pricing.txt`: Handles pricing updates from Odoo to Shopify.
- `Stock Feed OSM.txt`: Updates stock levels for OSM Shopify store.
- `Stock Feed TC.txt`: Updates stock levels for TC Shopify store.

## Setup & Configuration
### Prerequisites
- Node.js & Python installed
- Shopify API credentials
- Odoo EDI setup

### Configuration
Update these variables in scripts:
- **FTP Credentials** (for EDI message handling)
- **Shopify API Keys** (Store URL, Access Token)
- **Odoo Database Access** (for queries)

### Installation
1. Clone the repository
2. Install dependencies:
   ```sh
   npm install axios csv-parser
   ```
3. Configure credentials in the scripts.

### Running the Scripts
Run individual scripts based on the required task:
- **Stock Updates:**
  ```sh
  python Main.txt
  ```
- **Pricing Updates:**
  ```sh
  python Send Odoo Pricing.txt
  ```

## Workflow
1. **Stock Processing:**
   - Extracts stock data from Odoo.
   - Compares with Shopify stock levels.
   - Updates stock on Shopify via GraphQL.
2. **Pricing Synchronization:**
   - Fetches pricing from Odoo.
   - Splits data into chunks.
   - Uploads prices to Shopify metafields.

## Logs & Debugging
- Logs are stored in `/In/Plytix/Logs/` on the FTP server.
- Check console output for errors.
- Verify API access permissions if issues arise.

## Future Enhancements
- Add retry mechanisms for failed API calls.
- Optimize GraphQL batch processing.
- Improve error logging and reporting.

## License
This project is proprietary and should not be shared without permission.

