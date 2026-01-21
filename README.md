# Rackbeat Product Mass Delete

A Python application to fetch and bulk delete products from the Rackbeat API.

## Features

- 🔍 **Fetch Products**: Retrieve all products from your Rackbeat account with automatic pagination
- � **CSV Import**: Import product numbers from semicolon-separated CSV files
- 💾 **Save to File**: Backup product lists before deletion
- 🗑️ **Bulk Delete**: Delete products in configurable batches (default: 2000 per batch)
- 🔄 **Retry Logic**: Automatically handles 403 errors by identifying and skipping products that cannot be deleted
- 🛡️ **Smart Error Handling**: Detects products used on lines and continues with other products
- ✅ **Comprehensive Testing**: Full test suite with mocked API calls
- ⚡ **Rate Limiting**: Built-in delays to respect API limits

## Available Scripts

### 1. `rackbeat_product_mass_delete.py`
Original version that fetches ALL products from your Rackbeat account and deletes them.

### 2. `rackbeat_product_mass_delete_from_csv.py` (Recommended)
Reads product numbers from a semicolon-separated CSV file and deletes only those products. Features:
- Automatic header detection and filtering
- Ignores "Produktnavn" (product name) columns
- Retry logic for handling 403 errors
- Individual product testing when batch fails
- Detailed success/failure reporting

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

### Using the CSV Import Version (Recommended)

This version allows you to specify which products to delete via a CSV file:

```bash
python rackbeat_product_mass_delete_from_csv.py
```

The application will:
1. Prompt for your Rackbeat API bearer token
2. Ask for the path to your CSV file (semicolon-separated)
3. Read and validate product numbers from the CSV
4. Display a preview of products to be deleted
5. Ask for confirmation before deletion
6. Delete products with automatic retry on 403 errors
7. Show detailed summary of successful and failed deletions

**CSV File Format:**
- Semicolon-separated values (`;`)
- Can include headers (automatically detected)
- Header "Produktnr." or similar will be recognized
- "Produktnavn" columns are automatically ignored
- Can have multiple columns; only product number columns are read

Example CSV:
```
Produktnr.;Produktnavn
10ABC;Product Name 1
120000;Product Name 2
120002;Product Name 3
```

### Using the Main Application (Delete All Products)

Run the main application interactively to delete ALL products:

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
from rackbeat_product_mass_delete_from_csv import RackbeatProductManager

# Initialize with your bearer token
manager = RackbeatProductManager("your_bearer_token_here")

# Option 1: Read from CSV file with retry logic
product_numbers = manager.read_product_numbers_from_csv("products.csv")
results = manager.delete_products_in_batches_with_retry(product_numbers)
manager.print_deletion_summary_with_retry(results)

# Option 2: Fetch all products
product_numbers = manager.fetch_all_product_numbers()

# Save to file (backup)
manager.save_product_numbers_to_file(product_numbers, "backup.txt")

# Delete in batches (without retry)
batch_results = manager.delete_products_in_batches(product_numbers)

# Print summary
manager.print_batch_summary(batch_results)
```

## Error Handling

### 403 Forbidden Errors

When a product cannot be deleted (typically because it's used on invoice lines or other documents), the API returns a 403 error with a message like:
```
"The product #10ABC is used on lines, and cannot be deleted."
```

The CSV import version automatically handles this by:
1. Attempting batch deletion first
2. If 403 is received, testing each product individually
3. Successfully deleting products that can be deleted
4. Tracking products that cannot be deleted
5. Providing a summary of both successful and failed deletions

Example output:
```
Processing batch 1 (attempt 1): 5 products
Batch 1: FAILED (HTTP 403) - Some products cannot be deleted
Identifying problematic products...
  ✗ 10ABC: Cannot be deleted (used on lines)
  ✓ 120000: Deleted successfully
  ✓ 120002: Deleted successfully

Total products attempted: 5
Successfully deleted: 2
Failed to delete: 3
```

## Configuration

### Batch Size

You can customize the batch size when deleting products:

```python
# Delete in batches of 500
results = manager.delete_products_in_batches_with_retry(product_numbers, batch_size=500)
```

Default batch size is 2000 products per batch.

### API Delay

The default delay between batches is 1 second. This is configured in the code to respect API rate limits.

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
- `DELETE /api/products/{product_number}` - Delete individual product (used for retry logic)

## Important Notes

⚠️ **WARNING**: This application permanently deletes products. Always:
- Backup your product data before running
- Test with a small number of products first
- Verify the product list before confirming deletion
- Keep the generated backup files
- Use the CSV import version to have precise control over which products are deleted
- Products used on invoice lines or other documents cannot be deleted and will be skipped

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
