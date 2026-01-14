"""
Test suite for Rackbeat Product Mass Delete
Tests the functionality without making real API calls
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import os
from rackbeat_product_mass_delete import RackbeatProductManager


class TestRackbeatProductManager(unittest.TestCase):
    """Test cases for RackbeatProductManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_token = "test_bearer_token_12345"
        self.manager = RackbeatProductManager(self.test_token)
    
    def test_initialization(self):
        """Test that the manager initializes correctly"""
        self.assertEqual(self.manager.bearer_token, self.test_token)
        self.assertEqual(self.manager.base_url, "https://app.rackbeat.com/api")
        self.assertIn("Authorization", self.manager.headers)
        self.assertEqual(self.manager.headers["Authorization"], f"Bearer {self.test_token}")
    
    @patch('rackbeat_product_mass_delete.requests.get')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_fetch_all_product_numbers_single_page(self, mock_sleep, mock_get):
        """Test fetching product numbers with a single page response"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 206
        mock_response.text = "Success"
        mock_response.json.return_value = {
            "products": [
                {"number": "PROD001"},
                {"number": "PROD002"},
                {"number": "PROD003"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Execute
        product_numbers = self.manager.fetch_all_product_numbers()
        
        # Verify
        self.assertEqual(len(product_numbers), 3)
        self.assertIn("PROD001", product_numbers)
        self.assertIn("PROD002", product_numbers)
        self.assertIn("PROD003", product_numbers)
    
    @patch('rackbeat_product_mass_delete.requests.get')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_fetch_all_product_numbers_multiple_pages(self, mock_sleep, mock_get):
        """Test fetching product numbers with pagination"""
        # Mock API responses for multiple pages
        def mock_response_side_effect(*args, **kwargs):
            page = kwargs.get('params', {}).get('page', 1)
            mock_resp = Mock()
            mock_resp.status_code = 206
            mock_resp.text = "Success"
            
            if page == 1:
                # First page with 1000 products (triggers pagination)
                mock_resp.json.return_value = {
                    "products": [{"number": f"PROD{i:04d}"} for i in range(1, 1001)]
                }
            elif page == 2:
                # Second page with less than 1000 products (last page)
                mock_resp.json.return_value = {
                    "products": [{"number": f"PROD{i:04d}"} for i in range(1001, 1501)]
                }
            else:
                mock_resp.json.return_value = {"products": []}
            
            return mock_resp
        
        mock_get.side_effect = mock_response_side_effect
        
        # Execute
        product_numbers = self.manager.fetch_all_product_numbers()
        
        # Verify
        self.assertEqual(len(product_numbers), 1500)
        self.assertIn("PROD0001", product_numbers)
        self.assertIn("PROD1500", product_numbers)
        self.assertEqual(mock_get.call_count, 2)  # Should make 2 API calls
    
    @patch('rackbeat_product_mass_delete.requests.get')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_fetch_all_product_numbers_error_response(self, mock_sleep, mock_get):
        """Test handling of error responses"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 401  # Unauthorized
        mock_response.text = "Invalid token"
        mock_get.return_value = mock_response
        
        # Execute
        product_numbers = self.manager.fetch_all_product_numbers()
        
        # Verify - should return empty list on error
        self.assertEqual(len(product_numbers), 0)
    
    def test_save_product_numbers_to_file(self):
        """Test saving product numbers to a file"""
        test_products = ["PROD001", "PROD002", "PROD003"]
        test_filename = "test_products.txt"
        
        try:
            # Execute
            self.manager.save_product_numbers_to_file(test_products, test_filename)
            
            # Verify file exists
            self.assertTrue(os.path.exists(test_filename))
            
            # Verify file contents
            df = pd.read_csv(test_filename, header=None)
            self.assertEqual(len(df), 3)
            self.assertIn("PROD001", df[0].values)
            self.assertIn("PROD002", df[0].values)
            self.assertIn("PROD003", df[0].values)
        
        finally:
            # Cleanup
            if os.path.exists(test_filename):
                os.remove(test_filename)
    
    @patch('rackbeat_product_mass_delete.requests.post')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_delete_products_in_batches_single_batch(self, mock_sleep, mock_post):
        """Test deleting products in a single batch"""
        # Mock successful delete response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        test_products = [f"PROD{i:03d}" for i in range(1, 101)]  # 100 products
        
        # Execute
        batch_results = self.manager.delete_products_in_batches(test_products, batch_size=2000)
        
        # Verify
        self.assertEqual(len(batch_results), 1)  # Should have 1 batch
        self.assertEqual(batch_results[1], 200)  # Batch 1 should be successful
        self.assertEqual(mock_post.call_count, 1)
    
    @patch('rackbeat_product_mass_delete.requests.post')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_delete_products_in_batches_multiple_batches(self, mock_sleep, mock_post):
        """Test deleting products in multiple batches"""
        # Mock successful delete response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        test_products = [f"PROD{i:04d}" for i in range(1, 4001)]  # 4000 products
        
        # Execute with batch size of 2000
        batch_results = self.manager.delete_products_in_batches(test_products, batch_size=2000)
        
        # Verify
        self.assertEqual(len(batch_results), 2)  # Should have 2 batches
        self.assertEqual(batch_results[1], 200)
        self.assertEqual(batch_results[2], 200)
        self.assertEqual(mock_post.call_count, 2)
    
    @patch('rackbeat_product_mass_delete.requests.post')
    @patch('rackbeat_product_mass_delete.time.sleep')
    def test_delete_products_in_batches_with_errors(self, mock_sleep, mock_post):
        """Test handling of deletion errors"""
        # Mock responses with some failures
        def mock_delete_side_effect(*args, **kwargs):
            # Simulate different responses for different batches
            mock_resp = Mock()
            if hasattr(mock_delete_side_effect, 'call_count'):
                mock_delete_side_effect.call_count += 1
            else:
                mock_delete_side_effect.call_count = 1
            
            # First batch succeeds, second fails
            if mock_delete_side_effect.call_count == 1:
                mock_resp.status_code = 200
            else:
                mock_resp.status_code = 500
                mock_resp.text = "Server error"
            
            return mock_resp
        
        mock_post.side_effect = mock_delete_side_effect
        
        test_products = [f"PROD{i:04d}" for i in range(1, 4001)]  # 4000 products
        
        # Execute
        batch_results = self.manager.delete_products_in_batches(test_products, batch_size=2000)
        
        # Verify
        self.assertEqual(len(batch_results), 2)
        self.assertEqual(batch_results[1], 200)  # First batch success
        self.assertEqual(batch_results[2], 500)  # Second batch failure
    
    @patch('builtins.print')
    def test_print_batch_summary(self, mock_print):
        """Test batch summary printing"""
        batch_results = {
            1: 200,
            2: 200,
            3: 500,
            4: 200
        }
        
        # Execute
        self.manager.print_batch_summary(batch_results)
        
        # Verify print was called (basic check)
        self.assertTrue(mock_print.called)
        
        # Check that summary information was included in prints
        print_calls = [str(call) for call in mock_print.call_args_list]
        summary_text = ' '.join(print_calls)
        self.assertIn('SUMMARY', summary_text)


class TestIntegration(unittest.TestCase):
    """Integration tests (with mocked network calls)"""
    
    @patch('rackbeat_product_mass_delete.time.sleep')
    @patch('rackbeat_product_mass_delete.requests.post')
    @patch('rackbeat_product_mass_delete.requests.get')
    def test_full_workflow(self, mock_get, mock_post, mock_sleep):
        """Test the complete workflow: fetch, save, and delete"""
        # Setup mocks
        mock_get_response = Mock()
        mock_get_response.status_code = 206
        mock_get_response.text = "Success"
        mock_get_response.json.return_value = {
            "products": [{"number": f"PROD{i:03d}"} for i in range(1, 11)]
        }
        mock_get.return_value = mock_get_response
        
        mock_delete_response = Mock()
        mock_delete_response.status_code = 200
        mock_post.return_value = mock_delete_response
        
        # Initialize manager
        manager = RackbeatProductManager("test_token")
        
        # Step 1: Fetch products
        products = manager.fetch_all_product_numbers()
        self.assertEqual(len(products), 10)
        
        # Step 2: Save to file
        test_filename = "test_integration.txt"
        try:
            manager.save_product_numbers_to_file(products, test_filename)
            self.assertTrue(os.path.exists(test_filename))
            
            # Step 3: Delete products
            batch_results = manager.delete_products_in_batches(products, batch_size=2000)
            self.assertEqual(len(batch_results), 1)
            self.assertEqual(batch_results[1], 200)
        
        finally:
            if os.path.exists(test_filename):
                os.remove(test_filename)


def run_tests():
    """Run all tests and print results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRackbeatProductManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
