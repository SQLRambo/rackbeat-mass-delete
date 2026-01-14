# Rackbeat Product Mass Delete

A Python application to fetch and bulk delete products from the Rackbeat API.

## Features

- 🔍 **Fetch Products**: Retrieve all products from your Rackbeat account with automatic pagination
- 💾 **Save to File**: Backup product lists before deletion
- 🗑️ **Bulk Delete**: Delete products in configurable batches (default: 1000 per batch)
- ✅ **Comprehensive Testing**: Full test suite with mocked API calls
- ⚡ **Rate Limiting**: Built-in delays to respect API limits (500ms between batches)

## Requirements

- Python 3.7+
- pandas
- requests

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/rackbeat-product-mass-delete.git
cd rackbeat-product-mass-delete
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install pandas requests
```

## Usage

### Using the Main Application

Run the main application interactively:

```bash
python rackbeat_product_mass_delete.py
```

The application will:
1. Prompt for your Rackbeat API bearer token
2. Fetch all products from your account
3. Save product numbers to a file
4. Ask for confirmation before deletion
5. Delete all products in batches

### Using as a Module

```python
from rackbeat_product_mass_delete import RackbeatProductManager

# Initialize with your bearer token
manager = RackbeatProductManager("your_bearer_token_here")

# Fetch all product numbers
product_numbers = manager.fetch_all_product_numbers()

# Save to file (backup)
manager.save_product_numbers_to_file(product_numbers, "backup.txt")

# Delete in batches (default: 1000 per batch)
batch_results = manager.delete_products_in_batches(product_numbers)

# Print summary
manager.print_batch_summary(batch_results)
```

## Configuration

### Batch Size

You can customize the batch size when deleting products:

```python
# Delete in batches of 500
batch_results = manager.delete_products_in_batches(product_numbers, batch_size=500)
```

### API Delay

The default delay between batches is 500ms. This is configured in the code to respect API rate limits.

## API Authentication

You need a Rackbeat API bearer token to use this application:

1. Log in to your Rackbeat account
2. Go to Settings → API
3. Generate a new bearer token
4. Copy the token and use it when prompted by the application

## Testing

Run the comprehensive test suite:

```bash
python test_rackbeat_product_manager.py
```

All tests use mocked API calls, so they're safe to run without affecting real data.

## API Endpoints Used

- `GET /api/products` - Fetch products with pagination
- `POST /api/products/bulk/delete` - Bulk delete products

## Important Notes

⚠️ **WARNING**: This application permanently deletes products. Always:
- Backup your product data before running
- Test with a small number of products first
- Verify the product list before confirming deletion
- Keep the generated backup files

## Response Format

The API uses the following response structure:

### Fetch Products
```json
{
  "products": [
    {"number": "PROD001"},
    {"number": "PROD002"}
  ],
  "total": 5841,
  "pages": 585,
  "limit": 10,
  "page": 1
}
```

### Bulk Delete
Request:
```json
{
  "ids": ["PROD001", "PROD002"]
}
```

Response:
```json
{
  "message": "Ok"
}
```

## License

MIT License

## Disclaimer

This tool is provided as-is. Always backup your data before performing bulk deletions. The authors are not responsible for any data loss resulting from the use of this application.
