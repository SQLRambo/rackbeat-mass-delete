"""
Rackbeat Product Manager
A Python application to fetch and delete products from Rackbeat API
"""

import requests
import pandas as pd
import sys
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
    
    def delete_products_in_batches(self, product_numbers: List[str], batch_size: int = 1000) -> Dict[int, int]:
        """
        Delete products in batches using the bulk delete API
        
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


def main():
    """
    Main function to run the Rackbeat Product Manager
    """
    print("Rackbeat Product Manager")
    print("="*30)
    
    # Get bearer token from user input
    bearer_token = input("Please enter your bearer token: ").strip()
    
    if not bearer_token:
        print("Error: Bearer token is required!")
        sys.exit(1)
    
    # Initialize the product manager
    manager = RackbeatProductManager(bearer_token)
    
    # Step 1: Fetch all product numbers
    product_numbers = manager.fetch_all_product_numbers()
    
    if not product_numbers:
        print("No product numbers found or failed to fetch products.")
        sys.exit(1)
    
    # Step 2: Save product numbers to file
    manager.save_product_numbers_to_file(product_numbers)
    
    # Step 3: Ask user confirmation before deletion
    print(f"\nFound {len(product_numbers)} products to delete.")
    confirm = input("Are you sure you want to delete ALL these products? (yes/no): ").lower().strip()
    
    if confirm != 'yes':
        print("Deletion cancelled by user.")
        sys.exit(0)
    
    # Step 4: Delete products in batches
    batch_results = manager.delete_products_in_batches(product_numbers, batch_size=2000)
    
    # Step 5: Print summary
    manager.print_batch_summary(batch_results)


if __name__ == "__main__":
    main()