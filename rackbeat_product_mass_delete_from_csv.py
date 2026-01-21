"""
Rackbeat Product Manager - CSV Import Version
A Python application to delete products from Rackbeat API using a CSV file with product numbers
"""

import requests
import pandas as pd
import sys
import os
from typing import List, Dict, Any
import time


class RackbeatProductManager:
    def __init__(self, bearer_token: str):
        """
        Initialize the Rackbeat Product Manager
        
        Args:
            bearer_token (str): Bearer token for API authentication
        """
        self.bearer_token = bearer_token
        self.base_url = "https://app.rackbeat.com/api"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def read_product_numbers_from_csv(self, csv_file_path: str) -> List[str]:
        """
        Read product numbers from a semicolon-separated CSV file
        
        Args:
            csv_file_path (str): Path to the CSV file
            
        Returns:
            List[str]: List of product numbers from the CSV file
        """
        try:
            if not os.path.exists(csv_file_path):
                print(f"Error: File not found: {csv_file_path}")
                return []
            
            print(f"Reading product numbers from: {csv_file_path}")
            
            # First, read the first row to check for headers
            df_peek = pd.read_csv(csv_file_path, sep=';', nrows=1, dtype=str)
            first_row_values = df_peek.iloc[0].tolist()
            
            # Check if first row contains header-like values
            has_header = any(str(val).lower() in ['produktnr.', 'produktnr', 'produktnavn', 
                                                    'product number', 'product_number'] 
                            for val in first_row_values if pd.notna(val))
            
            # Read CSV with or without header
            if has_header:
                df = pd.read_csv(csv_file_path, sep=';', dtype=str)
                # Find product number column(s)
                product_number_headers = ['produktnr.', 'produktnr', 'product number', 'product_number', 
                                         'productnumber', 'number', 'nr', 'varenr', 'varenummer']
                cols_to_read = [col for col in df.columns 
                               if str(col).lower().strip() in product_number_headers]
                
                # If no explicit product number column found, use the first column
                if not cols_to_read:
                    cols_to_read = [df.columns[0]]
                
                df = df[cols_to_read]
            else:
                # No header - only read the first column
                df = pd.read_csv(csv_file_path, sep=';', header=None, dtype=str)
                df = df[[0]]  # Only keep first column
            
            # Flatten all columns into a single list and remove any NaN values
            product_numbers = []
            for col in df.columns:
                values = df[col].dropna().astype(str).tolist()
                product_numbers.extend(values)
            
            # Remove any whitespace and empty strings
            product_numbers = [pn.strip() for pn in product_numbers if pn.strip()]
            
            # Remove common header values that might still be present
            common_headers = ['produktnr.', 'produktnr', 'product number', 'product_number', 
                            'productnumber', 'number', 'nr', 'varenr', 'varenummer']
            product_numbers = [pn for pn in product_numbers 
                             if pn.lower() not in common_headers]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_product_numbers = []
            for pn in product_numbers:
                if pn not in seen:
                    seen.add(pn)
                    unique_product_numbers.append(pn)
            
            print(f"Found {len(unique_product_numbers)} unique product numbers in CSV file")
            
            return unique_product_numbers
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return []
    
    def fetch_all_product_numbers(self) -> List[str]:
        """
        Fetch all product numbers from the API with pagination
        
        Returns:
            List[str]: List of all product numbers
        """
        product_numbers = []
        page = 1
        
        print("Fetching product numbers from Rackbeat API...")
        
        while True:
            # API parameters
            params = {
                "fields": "number",
                "limit": 1000,
                "page": page
            }
            
            try:
                print(f"Fetching page {page}...")
                response = requests.get(
                    f"{self.base_url}/products",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code != 206:
                    print(f"Error fetching page {page}: HTTP {response.status_code}")
                    print(f"Response: {response.text}")
                    break
                
                data = response.json()
                
                # Extract product numbers from the response
                if "products" in data and isinstance(data["products"], list):
                    page_products = [product.get("number") for product in data["products"] 
                                   if product.get("number")]
                    product_numbers.extend(page_products)
                    
                    print(f"Page {page}: Found {len(page_products)} products")
                    
                    # Check if we've reached the last page
                    if len(page_products) < 1000:
                        print("Reached last page")
                        break
                else:
                    print("No more products found or unexpected response format")
                    break
                
                page += 1
                
                # Add a small delay to be respectful to the API
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"Request error on page {page}: {e}")
                break
            except Exception as e:
                print(f"Unexpected error on page {page}: {e}")
                break
        
        print(f"Total product numbers fetched: {len(product_numbers)}")
        return product_numbers
    
    def save_product_numbers_to_file(self, product_numbers: List[str], filename: str = "product_numbers.txt"):
        """
        Save product numbers to a text file using pandas
        
        Args:
            product_numbers (List[str]): List of product numbers
            filename (str): Output filename
        """
        try:
            # Create a pandas DataFrame
            df = pd.DataFrame(product_numbers, columns=['product_number'])
            
            # Save to text file
            df.to_csv(filename, index=False, header=False)
            print(f"Product numbers saved to {filename}")
            
        except Exception as e:
            print(f"Error saving product numbers: {e}")
    
    def delete_products_in_batches_with_retry(self, product_numbers: List[str], batch_size: int = 1000) -> Dict[str, Any]:
        """
        Delete products in batches using the bulk delete API with retry logic.
        If a batch fails, identify failed products and retry without them.
        
        Args:
            product_numbers (List[str]): List of product numbers to delete
            batch_size (int): Number of products to delete per batch
            
        Returns:
            Dict[str, Any]: Results containing successful deletions, failed products, and batch results
        """
        total_products = len(product_numbers)
        failed_products = []
        successful_deletions = []
        batch_results = {}
        
        print(f"Starting bulk deletion with retry of {total_products} products in batches of {batch_size}...")
        
        # Process products in batches
        for i in range(0, total_products, batch_size):
            batch_num = i // batch_size + 1
            batch = product_numbers[i:i + batch_size]
            remaining_batch = batch.copy()
            retry_count = 0
            max_retries = 10  # Prevent infinite loops
            
            while remaining_batch and retry_count < max_retries:
                print(f"\nProcessing batch {batch_num} (attempt {retry_count + 1}): {len(remaining_batch)} products")
                
                # Prepare the payload for bulk delete
                payload = {
                    "ids": remaining_batch
                }
                
                try:
                    response = requests.post(
                        f"{self.base_url}/products/bulk/delete",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        print(f"Batch {batch_num}: SUCCESS - {len(remaining_batch)} products deleted")
                        successful_deletions.extend(remaining_batch)
                        batch_results[f"{batch_num}.{retry_count + 1}"] = response.status_code
                        break  # Success, move to next batch
                    
                    elif response.status_code == 403:
                        print(f"Batch {batch_num}: FAILED (HTTP 403) - Some products cannot be deleted")
                        print(f"Identifying problematic products...")
                        
                        # Test each product individually to find which ones fail
                        batch_failed = []
                        batch_successful = []
                        
                        for product_num in remaining_batch:
                            try:
                                test_response = requests.delete(
                                    f"{self.base_url}/products/{product_num}",
                                    headers=self.headers
                                )
                                
                                if test_response.status_code in [200, 204]:
                                    batch_successful.append(product_num)
                                    print(f"  ✓ {product_num}: Deleted successfully")
                                elif test_response.status_code == 403:
                                    batch_failed.append(product_num)
                                    print(f"  ✗ {product_num}: Cannot be deleted (used on lines)")
                                elif test_response.status_code == 404:
                                    batch_successful.append(product_num)
                                    print(f"  ✓ {product_num}: Already deleted")
                                else:
                                    batch_failed.append(product_num)
                                    print(f"  ✗ {product_num}: Failed (HTTP {test_response.status_code})")
                                
                                time.sleep(0.1)  # Small delay between tests
                                
                            except Exception as e:
                                batch_failed.append(product_num)
                                print(f"  ✗ {product_num}: Error - {e}")
                        
                        # Update tracking lists
                        successful_deletions.extend(batch_successful)
                        failed_products.extend(batch_failed)
                        
                        print(f"\nBatch {batch_num} summary: {len(batch_successful)} deleted, {len(batch_failed)} failed")
                        batch_results[f"{batch_num}.{retry_count + 1}"] = response.status_code
                        break  # All products processed individually
                    
                    else:
                        print(f"Batch {batch_num}: FAILED (HTTP {response.status_code})")
                        print(f"Response: {response.text}")
                        batch_results[f"{batch_num}.{retry_count + 1}"] = response.status_code
                        failed_products.extend(remaining_batch)
                        break
                    
                except requests.exceptions.RequestException as e:
                    print(f"Batch {batch_num}: Request error - {e}")
                    batch_results[f"{batch_num}.{retry_count + 1}"] = -1
                    failed_products.extend(remaining_batch)
                    break
                except Exception as e:
                    print(f"Batch {batch_num}: Unexpected error - {e}")
                    batch_results[f"{batch_num}.{retry_count + 1}"] = -2
                    failed_products.extend(remaining_batch)
                    break
                
                retry_count += 1
            
            # Add delay between batches to avoid overwhelming the API
            time.sleep(1)
        
        return {
            "batch_results": batch_results,
            "successful_deletions": successful_deletions,
            "failed_products": failed_products,
            "total_attempted": total_products,
            "total_successful": len(successful_deletions),
            "total_failed": len(failed_products)
        }
    
    def delete_products_in_batches(self, product_numbers: List[str], batch_size: int = 1000) -> Dict[int, int]:
        """
        Delete products in batches using the bulk delete API (without retry)
        
        Args:
            product_numbers (List[str]): List of product numbers to delete
            batch_size (int): Number of products to delete per batch
            
        Returns:
            Dict[int, int]: Dictionary mapping batch number to HTTP response code
        """
        batch_results = {}
        total_products = len(product_numbers)
        
        print(f"Starting bulk deletion of {total_products} products in batches of {batch_size}...")
        
        # Process products in batches
        for i in range(0, total_products, batch_size):
            batch_num = i // batch_size + 1
            batch = product_numbers[i:i + batch_size]
            
            print(f"Processing batch {batch_num}: {len(batch)} products")
            
            # Prepare the payload for bulk delete
            payload = {
                "ids": batch
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/products/bulk/delete",
                    headers=self.headers,
                    json=payload
                )
                
                batch_results[batch_num] = response.status_code
                
                if response.status_code == 200:
                    print(f"Batch {batch_num}: SUCCESS (HTTP {response.status_code})")
                elif response.status_code == 403:
                    print(f"Batch {batch_num}: FAILED (HTTP {response.status_code})")
                    print(f"Some products in this batch are used on lines and cannot be deleted")
                    print(f"Response: {response.text}")
                else:
                    print(f"Batch {batch_num}: FAILED (HTTP {response.status_code})")
                    print(f"Response: {response.text}")
                
                # Add delay between batches to avoid overwhelming the API
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print(f"Batch {batch_num}: Request error - {e}")
                batch_results[batch_num] = -1
            except Exception as e:
                print(f"Batch {batch_num}: Unexpected error - {e}")
                batch_results[batch_num] = -2
        
        return batch_results
    
    def delete_products_individually(self, product_numbers: List[str], delay: float = 0.1) -> Dict[str, int]:
        """
        Delete products one by one using individual DELETE requests
        
        Args:
            product_numbers (List[str]): List of product numbers to delete
            delay (float): Delay in seconds between each delete request
            
        Returns:
            Dict[str, int]: Dictionary mapping product number to HTTP response code
        """
        results = {}
        total_products = len(product_numbers)
        
        print(f"Starting individual deletion of {total_products} products...")
        print()
        
        for idx, product_number in enumerate(product_numbers, 1):
            try:
                response = requests.delete(
                    f"{self.base_url}/products/{product_number}",
                    headers=self.headers
                )
                
                results[product_number] = response.status_code
                
                if response.status_code in [200, 204]:
                    if idx % 10 == 0 or idx == total_products:
                        print(f"Progress: {idx}/{total_products} - {product_number}: SUCCESS")
                elif response.status_code == 404:
                    print(f"Progress: {idx}/{total_products} - {product_number}: NOT FOUND (already deleted?)")
                elif response.status_code == 403:
                    print(f"Progress: {idx}/{total_products} - The product {product_number} is used on lines, and cannot be deleted")
                else:
                    print(f"Progress: {idx}/{total_products} - {product_number}: FAILED (HTTP {response.status_code})")
                
                # Add delay to avoid overwhelming the API
                time.sleep(delay)
                
            except requests.exceptions.RequestException as e:
                print(f"Progress: {idx}/{total_products} - {product_number}: Request error - {e}")
                results[product_number] = -1
            except Exception as e:
                print(f"Progress: {idx}/{total_products} - {product_number}: Unexpected error - {e}")
                results[product_number] = -2
        
        return results
    
    def print_batch_summary(self, batch_results: Dict[int, int]):
        """
        Print a summary of batch deletion results
        
        Args:
            batch_results (Dict[int, int]): Batch results from deletion
        """
        print("\n" + "="*50)
        print("BATCH DELETION SUMMARY")
        print("="*50)
        
        successful_batches = 0
        failed_batches = 0
        
        for batch_num, status_code in batch_results.items():
            status = "SUCCESS" if status_code == 200 else "FAILED"
            print(f"Batch {batch_num}: HTTP {status_code} - {status}")
            
            if status_code == 200:
                successful_batches += 1
            else:
                failed_batches += 1
        
        print("-"*50)
        print(f"Total batches: {len(batch_results)}")
        print(f"Successful batches: {successful_batches}")
        print(f"Failed batches: {failed_batches}")
        print("="*50)
    
    def print_deletion_summary_with_retry(self, results: Dict[str, Any]):
        """
        Print a summary of deletion results with retry information
        
        Args:
            results (Dict[str, Any]): Results from delete_products_in_batches_with_retry
        """
        print("\n" + "="*60)
        print("DELETION SUMMARY WITH RETRY")
        print("="*60)
        
        print(f"\nTotal products attempted: {results['total_attempted']}")
        print(f"Successfully deleted: {results['total_successful']}")
        print(f"Failed to delete: {results['total_failed']}")
        
        if results['failed_products']:
            print(f"\nFailed products ({len(results['failed_products'])}):")
            for product in results['failed_products']:
                print(f"  - {product}")
        
        print("\n" + "="*60)


def main():
    """
    Main function to run the Rackbeat Product Manager with CSV import
    """
    print("Rackbeat Product Manager - CSV Import Version")
    print("="*50)
    
    # Get bearer token from user input
    bearer_token = input("Please enter your bearer token: ").strip()
    
    if not bearer_token:
        print("Error: Bearer token is required!")
        sys.exit(1)
    
    # Get CSV file path from user input
    csv_file_path = input("Please enter the path to your CSV file (semicolon-separated): ").strip()
    
    # Remove quotes if the user copied the path with quotes
    csv_file_path = csv_file_path.strip('"').strip("'")
    
    if not csv_file_path:
        print("Error: CSV file path is required!")
        sys.exit(1)
    
    # Initialize the product manager
    manager = RackbeatProductManager(bearer_token)
    
    # Step 1: Read product numbers from CSV file
    product_numbers = manager.read_product_numbers_from_csv(csv_file_path)
    
    if not product_numbers:
        print("No product numbers found in the CSV file or failed to read the file.")
        sys.exit(1)
    
    # Display first few product numbers as a preview
    print(f"\nFirst 5 product numbers: {product_numbers[:5]}")
    
    # Step 2: Ask user confirmation before deletion
    print(f"\nFound {len(product_numbers)} products to delete.")
    confirm = input("Are you sure you want to delete these products? (yes/no): ").lower().strip()
    
    if confirm != 'yes':
        print("Deletion cancelled by user.")
        sys.exit(0)
    
    # Step 3: Delete products in batches with retry
    results = manager.delete_products_in_batches_with_retry(product_numbers, batch_size=2000)
    
    # Step 4: Print summary
    manager.print_deletion_summary_with_retry(results)


if __name__ == "__main__":
    main()
