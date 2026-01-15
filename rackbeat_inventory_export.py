"""
Rackbeat Inventory Export
Fetches inventory data from Rackbeat API and exports to CSV
"""

import requests
import csv
import sys
from typing import List, Dict, Any


def fetch_all_products(bearer_token: str) -> List[Dict[str, Any]]:
    """
    Fetch all products from Rackbeat API with pagination.
    
    Args:
        bearer_token: Bearer token for API authentication
        
    Returns:
        List of all products
    """
    base_url = "https://app.rackbeat.com/api/reports/checking"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json"
    }
    
    params = {
        "show_all_locations": "true",
        "limit": "1000",
        "fields": "number,name,stock_quantity,cost_price,recommended_cost_price,barcode,locations(*)"
    }
    
    all_products = []
    page = 1
    
    print("Fetching products from Rackbeat API...")
    
    while True:
        params["page"] = str(page)
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract products from response (API uses 'items' field)
            if "items" in data:
                products = data["items"]
                if not products:
                    break
                    
                all_products.extend(products)
                print(f"Fetched page {page}: {len(products)} products (Total: {len(all_products)})")
                
                # Check if there are more pages
                total_pages = data.get("pages", 1)
                if page >= total_pages:
                    break
                    
                page += 1
            else:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            sys.exit(1)
    
    print(f"Total products fetched: {len(all_products)}")
    return all_products


def flatten_product(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten product data, especially handling locations array.
    Creates one row per location, or one row if no locations.
    
    Args:
        product: Product dictionary
        
    Returns:
        List of flattened product dictionaries
    """
    base_data = {
        "number": product.get("number", ""),
        "name": product.get("name", ""),
        "stock_quantity": product.get("stock_quantity", ""),
        "cost_price": product.get("cost_price", ""),
        "recommended_cost_price": product.get("recommended_cost_price", ""),
        "barcode": product.get("barcode", "")
    }
    
    locations = product.get("locations", [])
    
    if not locations:
        # No locations, return single row
        return [{
            **base_data,
            "location_number": "",
            "location_name": "",
            "location_stock_quantity": ""
        }]
    
    # Create one row per location
    flattened_rows = []
    for location in locations:
        row = {
            **base_data,
            "location_number": location.get("number", ""),
            "location_name": location.get("name", ""),
            "location_stock_quantity": location.get("stock_quantity", "")
        }
        flattened_rows.append(row)
    
    return flattened_rows


def save_to_csv(products: List[Dict[str, Any]], filename: str = "rackbeat_inventory_export.csv"):
    """
    Save flattened products to semicolon-separated CSV file.
    
    Args:
        products: List of product dictionaries
        filename: Output CSV filename
    """
    if not products:
        print("No products to save.")
        return
    
    # Flatten all products
    flattened_data = []
    for product in products:
        flattened_data.extend(flatten_product(product))
    
    # Get all unique field names
    fieldnames = [
        "number",
        "name",
        "stock_quantity",
        "cost_price",
        "recommended_cost_price",
        "barcode",
        "location_number",
        "location_name",
        "location_stock_quantity"
    ]
    
    # Write to CSV with semicolon delimiter
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(flattened_data)
    
    print(f"Data exported successfully to {filename}")
    print(f"Total rows: {len(flattened_data)}")


def main():
    """Main function to run the export process."""
    print("=" * 60)
    print("Rackbeat Inventory Export")
    print("=" * 60)
    print()
    
    # Get bearer token from user
    bearer_token = input("Enter your Rackbeat API bearer token: ").strip()
    
    if not bearer_token:
        print("Error: Bearer token is required.")
        sys.exit(1)
    
    # Fetch all products
    products = fetch_all_products(bearer_token)
    
    if not products:
        print("No products found.")
        sys.exit(0)
    
    # Save to CSV
    save_to_csv(products)
    
    print()
    print("Export completed successfully!")


if __name__ == "__main__":
    main()
