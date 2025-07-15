#!/usr/bin/env python3
"""
Backend API Testing Suite for Food Health Tracking Application
Tests OpenFoodFacts integration, health scoring, and all API endpoints
"""

import asyncio
import httpx
import json
import sys
import time
from typing import Dict, List, Any
from datetime import datetime

# Backend URL from frontend environment
BACKEND_URL = "https://c7246f44-97cb-4bb1-a402-26de582e1933.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        self.test_user_id = "test_user_12345"
        
    async def close(self):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, message: str, response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
    
    async def test_api_health(self):
        """Test basic API health"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Health Check", True, f"API is responding: {data.get('message', 'OK')}")
                return True
            else:
                self.log_test("API Health Check", False, f"API returned status {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"API connection failed: {str(e)}")
            return False
    
    async def test_food_search_real_products(self):
        """Test food search with real product queries"""
        test_queries = ["coca cola", "apple", "bread", "banana", "milk"]
        
        for query in test_queries:
            try:
                payload = {"query": query, "limit": 5}
                response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
                
                if response.status_code == 200:
                    products = response.json()
                    if isinstance(products, list) and len(products) > 0:
                        # Check first product structure
                        product = products[0]
                        required_fields = ["id", "product_name", "health_score", "health_rating"]
                        missing_fields = [field for field in required_fields if field not in product]
                        
                        if not missing_fields:
                            self.log_test(f"Food Search - {query}", True, 
                                        f"Found {len(products)} products, first: {product['product_name']}")
                        else:
                            self.log_test(f"Food Search - {query}", False, 
                                        f"Missing required fields: {missing_fields}", product)
                    else:
                        self.log_test(f"Food Search - {query}", False, "No products returned", products)
                else:
                    self.log_test(f"Food Search - {query}", False, 
                                f"Search failed with status {response.status_code}", response.text)
            except Exception as e:
                self.log_test(f"Food Search - {query}", False, f"Search error: {str(e)}")
    
    async def test_health_scoring_algorithm(self):
        """Test health scoring algorithm with known products"""
        try:
            # Test with Coca Cola (should have poor health score)
            payload = {"query": "coca cola", "limit": 1}
            response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    product = products[0]
                    health_score = product.get("health_score")
                    health_rating = product.get("health_rating")
                    
                    if health_score is not None and health_rating:
                        # Coca Cola should have low health score
                        if health_score < 50:
                            self.log_test("Health Scoring - Coca Cola", True, 
                                        f"Correct low score: {health_score} ({health_rating})")
                        else:
                            self.log_test("Health Scoring - Coca Cola", False, 
                                        f"Score too high for sugary drink: {health_score} ({health_rating})")
                    else:
                        self.log_test("Health Scoring - Coca Cola", False, 
                                    "Missing health score or rating", product)
                else:
                    self.log_test("Health Scoring - Coca Cola", False, "No products found for scoring test")
            
            # Test with Apple (should have good health score)
            payload = {"query": "apple fresh", "limit": 1}
            response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    product = products[0]
                    health_score = product.get("health_score")
                    health_rating = product.get("health_rating")
                    
                    if health_score is not None and health_rating:
                        # Apple should have higher health score
                        if health_score > 60:
                            self.log_test("Health Scoring - Apple", True, 
                                        f"Correct high score: {health_score} ({health_rating})")
                        else:
                            self.log_test("Health Scoring - Apple", False, 
                                        f"Score too low for healthy fruit: {health_score} ({health_rating})")
                    else:
                        self.log_test("Health Scoring - Apple", False, 
                                    "Missing health score or rating", product)
                        
        except Exception as e:
            self.log_test("Health Scoring Algorithm", False, f"Scoring test error: {str(e)}")
    
    async def test_barcode_lookup(self):
        """Test barcode lookup functionality"""
        # Common product barcodes to test
        test_barcodes = [
            "3017620422003",  # Nutella
            "8901030835029",  # Common Indian product
            "4902777000015",  # Japanese product
            "0012000161155"   # US product
        ]
        
        successful_lookups = 0
        
        for barcode in test_barcodes:
            try:
                response = await self.client.get(f"{BACKEND_URL}/food/barcode/{barcode}")
                
                if response.status_code == 200:
                    product = response.json()
                    if product.get("product_name"):
                        successful_lookups += 1
                        self.log_test(f"Barcode Lookup - {barcode}", True, 
                                    f"Found: {product['product_name']}")
                    else:
                        self.log_test(f"Barcode Lookup - {barcode}", False, 
                                    "Product found but missing name", product)
                elif response.status_code == 404:
                    self.log_test(f"Barcode Lookup - {barcode}", True, 
                                "Product not found (expected for some barcodes)")
                else:
                    self.log_test(f"Barcode Lookup - {barcode}", False, 
                                f"Unexpected status {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test(f"Barcode Lookup - {barcode}", False, f"Lookup error: {str(e)}")
        
        # Overall barcode functionality test
        if successful_lookups > 0:
            self.log_test("Barcode Lookup Functionality", True, 
                        f"Successfully looked up {successful_lookups} products")
        else:
            self.log_test("Barcode Lookup Functionality", False, 
                        "No successful barcode lookups")
    
    async def test_food_tracking(self):
        """Test food tracking functionality"""
        try:
            # First, get a product to track
            search_payload = {"query": "banana", "limit": 1}
            search_response = await self.client.post(f"{BACKEND_URL}/food/search", json=search_payload)
            
            if search_response.status_code != 200:
                self.log_test("Food Tracking Setup", False, "Could not get product for tracking test")
                return
            
            products = search_response.json()
            if not products:
                self.log_test("Food Tracking Setup", False, "No products found for tracking test")
                return
            
            test_product = products[0]
            
            # Test tracking food
            track_payload = {
                "user_id": self.test_user_id,
                "food_product": test_product,
                "quantity": 150.0
            }
            
            track_response = await self.client.post(f"{BACKEND_URL}/food/track", json=track_payload)
            
            if track_response.status_code == 200:
                tracking_entry = track_response.json()
                entry_id = tracking_entry.get("id")
                
                if entry_id:
                    self.log_test("Food Tracking - Add Entry", True, 
                                f"Successfully tracked {test_product['product_name']}")
                    
                    # Test retrieving tracking history
                    history_response = await self.client.get(f"{BACKEND_URL}/food/track/{self.test_user_id}")
                    
                    if history_response.status_code == 200:
                        history = history_response.json()
                        if isinstance(history, list) and len(history) > 0:
                            self.log_test("Food Tracking - Get History", True, 
                                        f"Retrieved {len(history)} tracking entries")
                            
                            # Test deleting tracking entry
                            delete_response = await self.client.delete(f"{BACKEND_URL}/food/track/{entry_id}")
                            
                            if delete_response.status_code == 200:
                                self.log_test("Food Tracking - Delete Entry", True, 
                                            "Successfully deleted tracking entry")
                            else:
                                self.log_test("Food Tracking - Delete Entry", False, 
                                            f"Delete failed with status {delete_response.status_code}")
                        else:
                            self.log_test("Food Tracking - Get History", False, 
                                        "No tracking history returned", history)
                    else:
                        self.log_test("Food Tracking - Get History", False, 
                                    f"History retrieval failed with status {history_response.status_code}")
                else:
                    self.log_test("Food Tracking - Add Entry", False, 
                                "Tracking entry missing ID", tracking_entry)
            else:
                self.log_test("Food Tracking - Add Entry", False, 
                            f"Tracking failed with status {track_response.status_code}", track_response.text)
                
        except Exception as e:
            self.log_test("Food Tracking", False, f"Tracking test error: {str(e)}")
    
    async def test_api_response_times(self):
        """Test API response times"""
        endpoints_to_test = [
            ("GET", f"{BACKEND_URL}/", "API Root"),
            ("POST", f"{BACKEND_URL}/food/search", "Food Search", {"query": "apple", "limit": 5})
        ]
        
        for method, url, name, *payload in endpoints_to_test:
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = await self.client.get(url)
                else:
                    response = await self.client.post(url, json=payload[0] if payload else {})
                
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time < 10.0:  # 10 second timeout
                    self.log_test(f"Response Time - {name}", True, 
                                f"Responded in {response_time:.2f}s")
                elif response_time >= 10.0:
                    self.log_test(f"Response Time - {name}", False, 
                                f"Too slow: {response_time:.2f}s")
                else:
                    self.log_test(f"Response Time - {name}", False, 
                                f"Failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Response Time - {name}", False, f"Error: {str(e)}")
    
    async def test_error_handling(self):
        """Test API error handling"""
        try:
            # Test invalid barcode
            response = await self.client.get(f"{BACKEND_URL}/food/barcode/invalid_barcode")
            if response.status_code == 404:
                self.log_test("Error Handling - Invalid Barcode", True, 
                            "Correctly returned 404 for invalid barcode")
            else:
                self.log_test("Error Handling - Invalid Barcode", False, 
                            f"Expected 404, got {response.status_code}")
            
            # Test empty search query
            response = await self.client.post(f"{BACKEND_URL}/food/search", json={"query": "", "limit": 5})
            if response.status_code in [200, 400]:  # Either empty results or validation error is acceptable
                self.log_test("Error Handling - Empty Search", True, 
                            f"Handled empty search appropriately (status {response.status_code})")
            else:
                self.log_test("Error Handling - Empty Search", False, 
                            f"Unexpected status {response.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling", False, f"Error handling test failed: {str(e)}")
    
    async def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests for Food Health Tracking Application")
        print(f"Testing against: {BACKEND_URL}")
        print("=" * 80)
        
        # Test API health first
        if not await self.test_api_health():
            print("❌ API is not responding. Stopping tests.")
            return
        
        # Run all tests
        await self.test_food_search_real_products()
        await self.test_health_scoring_algorithm()
        await self.test_barcode_lookup()
        await self.test_food_tracking()
        await self.test_api_response_times()
        await self.test_error_handling()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 KEY FINDINGS:")
        
        # OpenFoodFacts Integration
        search_tests = [r for r in self.test_results if "Food Search" in r["test"]]
        search_success = sum(1 for r in search_tests if r["success"])
        if search_success > 0:
            print(f"  ✅ OpenFoodFacts API Integration: Working ({search_success}/{len(search_tests)} queries successful)")
        else:
            print(f"  ❌ OpenFoodFacts API Integration: Failed")
        
        # Health Scoring
        scoring_tests = [r for r in self.test_results if "Health Scoring" in r["test"]]
        scoring_success = sum(1 for r in scoring_tests if r["success"])
        if scoring_success == len(scoring_tests) and len(scoring_tests) > 0:
            print(f"  ✅ Health Scoring Algorithm: Working correctly")
        else:
            print(f"  ❌ Health Scoring Algorithm: Issues detected")
        
        # Barcode Lookup
        barcode_tests = [r for r in self.test_results if "Barcode Lookup" in r["test"]]
        barcode_success = sum(1 for r in barcode_tests if r["success"])
        if barcode_success > 0:
            print(f"  ✅ Barcode Lookup: Working ({barcode_success}/{len(barcode_tests)} lookups successful)")
        else:
            print(f"  ❌ Barcode Lookup: Failed")
        
        # Food Tracking
        tracking_tests = [r for r in self.test_results if "Food Tracking" in r["test"]]
        tracking_success = sum(1 for r in tracking_tests if r["success"])
        if tracking_success == len(tracking_tests) and len(tracking_tests) > 0:
            print(f"  ✅ Food Tracking: Working correctly")
        else:
            print(f"  ❌ Food Tracking: Issues detected")
        
        return passed_tests, failed_tests, self.test_results

async def main():
    """Main test runner"""
    tester = BackendTester()
    try:
        passed, failed, results = await tester.run_all_tests()
        
        # Save detailed results
        with open("/app/backend_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": len(results),
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/len(results))*100 if results else 0
                },
                "results": results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if failed == 0 else 1)
        
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())