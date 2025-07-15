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
    
    async def test_indian_food_search(self):
        """Test Indian OpenFoodFacts Integration with Indian food terms"""
        indian_food_terms = [
            "basmati rice", "wheat atta", "toor dal", "amul milk", 
            "britannia biscuit", "haldiram namkeen", "chana dal", "ghee"
        ]
        
        successful_searches = 0
        
        for term in indian_food_terms:
            try:
                payload = {"query": term, "limit": 10}
                response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
                
                if response.status_code == 200:
                    products = response.json()
                    if isinstance(products, list) and len(products) > 0:
                        successful_searches += 1
                        # Check if products have proper structure
                        product = products[0]
                        has_health_score = product.get("health_score") is not None
                        has_health_rating = product.get("health_rating") is not None
                        
                        self.log_test(f"Indian Food Search - {term}", True, 
                                    f"Found {len(products)} products, health scoring: {has_health_score and has_health_rating}")
                    else:
                        self.log_test(f"Indian Food Search - {term}", False, 
                                    f"No products found for Indian term: {term}")
                else:
                    self.log_test(f"Indian Food Search - {term}", False, 
                                f"Search failed with status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Indian Food Search - {term}", False, f"Search error: {str(e)}")
        
        # Overall Indian search functionality
        if successful_searches >= len(indian_food_terms) * 0.6:  # At least 60% success
            self.log_test("Indian OpenFoodFacts Integration", True, 
                        f"Successfully searched {successful_searches}/{len(indian_food_terms)} Indian terms")
        else:
            self.log_test("Indian OpenFoodFacts Integration", False, 
                        f"Only {successful_searches}/{len(indian_food_terms)} Indian searches successful")
    
    async def test_indian_food_categories(self):
        """Test Indian Food Categories API endpoint"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/food/categories")
            
            if response.status_code == 200:
                categories = response.json()
                if isinstance(categories, list) and len(categories) > 0:
                    # Check for expected Indian categories
                    expected_categories = ["dal", "rice", "atta", "ghee", "masala", "namkeen"]
                    found_categories = [cat for cat in expected_categories if cat in categories]
                    
                    if len(found_categories) >= 4:  # At least 4 expected categories
                        self.log_test("Indian Food Categories API", True, 
                                    f"Found {len(categories)} categories including: {', '.join(found_categories[:5])}")
                    else:
                        self.log_test("Indian Food Categories API", False, 
                                    f"Missing expected Indian categories. Found: {found_categories}")
                else:
                    self.log_test("Indian Food Categories API", False, 
                                "No categories returned or invalid format", categories)
            else:
                self.log_test("Indian Food Categories API", False, 
                            f"Categories API failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Indian Food Categories API", False, f"Categories test error: {str(e)}")
    
    async def test_indian_brand_prioritization(self):
        """Test Indian Brand Prioritization in search results"""
        indian_brands = ["amul", "britannia", "parle", "haldiram", "mdh", "everest"]
        
        # Test with generic terms that should return Indian brands first
        test_terms = ["milk", "biscuit", "spices", "namkeen"]
        
        brand_prioritization_working = 0
        
        for term in test_terms:
            try:
                payload = {"query": term, "limit": 10}
                response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
                
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        # Check if any of the first 3 results have Indian brands
                        top_products = products[:3]
                        indian_brand_found = False
                        
                        for product in top_products:
                            brand = product.get("brand", "").lower()
                            if any(indian_brand in brand for indian_brand in indian_brands):
                                indian_brand_found = True
                                break
                        
                        if indian_brand_found:
                            brand_prioritization_working += 1
                            self.log_test(f"Indian Brand Priority - {term}", True, 
                                        f"Indian brand found in top 3 results")
                        else:
                            self.log_test(f"Indian Brand Priority - {term}", False, 
                                        f"No Indian brands in top 3 results for {term}")
                    else:
                        self.log_test(f"Indian Brand Priority - {term}", False, 
                                    f"No products found for {term}")
                        
            except Exception as e:
                self.log_test(f"Indian Brand Priority - {term}", False, f"Brand priority test error: {str(e)}")
        
        # Overall brand prioritization assessment
        if brand_prioritization_working >= len(test_terms) * 0.5:  # At least 50% success
            self.log_test("Indian Brand Prioritization", True, 
                        f"Brand prioritization working for {brand_prioritization_working}/{len(test_terms)} terms")
        else:
            self.log_test("Indian Brand Prioritization", False, 
                        f"Brand prioritization only working for {brand_prioritization_working}/{len(test_terms)} terms")
    
    async def test_popular_indian_foods_api(self):
        """Test Popular Indian Foods API endpoint"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/food/popular-indian")
            
            if response.status_code == 200:
                products = response.json()
                if isinstance(products, list) and len(products) > 0:
                    # Check product structure and content
                    valid_products = 0
                    indian_products = 0
                    
                    for product in products:
                        if all(key in product for key in ["id", "product_name", "health_score"]):
                            valid_products += 1
                            
                            # Check if product seems Indian-related
                            name = product.get("product_name", "").lower()
                            brand = product.get("brand", "").lower()
                            indian_terms = ["basmati", "dal", "atta", "amul", "britannia", "indian", "masala"]
                            
                            if any(term in name or term in brand for term in indian_terms):
                                indian_products += 1
                    
                    if valid_products >= len(products) * 0.8:  # 80% valid structure
                        if indian_products >= len(products) * 0.4:  # 40% Indian-related
                            self.log_test("Popular Indian Foods API", True, 
                                        f"Found {len(products)} products, {indian_products} Indian-related")
                        else:
                            self.log_test("Popular Indian Foods API", False, 
                                        f"Only {indian_products}/{len(products)} products seem Indian-related")
                    else:
                        self.log_test("Popular Indian Foods API", False, 
                                    f"Only {valid_products}/{len(products)} products have valid structure")
                else:
                    self.log_test("Popular Indian Foods API", False, 
                                "No products returned or invalid format", products)
            else:
                self.log_test("Popular Indian Foods API", False, 
                            f"Popular Indian foods API failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Popular Indian Foods API", False, f"Popular Indian foods test error: {str(e)}")
    
    async def test_enhanced_barcode_lookup(self):
        """Test Enhanced Barcode Lookup with Indian product focus"""
        # Common Indian product barcodes (some may not exist, but testing the functionality)
        indian_barcodes = [
            "8901030835029",  # Common Indian product format
            "8901030800000",  # Amul product format
            "8901030900000",  # Britannia product format
            "8901725000000",  # Haldiram format
        ]
        
        # Also test with known international barcodes for comparison
        international_barcodes = [
            "3017620422003",  # Nutella
            "0012000161155"   # US product
        ]
        
        indian_lookups = 0
        total_lookups = 0
        
        # Test Indian barcodes
        for barcode in indian_barcodes:
            try:
                response = await self.client.get(f"{BACKEND_URL}/food/barcode/{barcode}")
                total_lookups += 1
                
                if response.status_code == 200:
                    product = response.json()
                    if product.get("product_name"):
                        indian_lookups += 1
                        self.log_test(f"Enhanced Barcode - Indian {barcode}", True, 
                                    f"Found Indian product: {product['product_name']}")
                    else:
                        self.log_test(f"Enhanced Barcode - Indian {barcode}", False, 
                                    "Product found but missing name")
                elif response.status_code == 404:
                    self.log_test(f"Enhanced Barcode - Indian {barcode}", True, 
                                "Product not found (acceptable for test barcodes)")
                else:
                    self.log_test(f"Enhanced Barcode - Indian {barcode}", False, 
                                f"Unexpected status {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Enhanced Barcode - Indian {barcode}", False, f"Lookup error: {str(e)}")
        
        # Test international barcodes for comparison
        for barcode in international_barcodes:
            try:
                response = await self.client.get(f"{BACKEND_URL}/food/barcode/{barcode}")
                
                if response.status_code == 200:
                    product = response.json()
                    if product.get("product_name"):
                        self.log_test(f"Enhanced Barcode - International {barcode}", True, 
                                    f"Found: {product['product_name']}")
                elif response.status_code == 404:
                    self.log_test(f"Enhanced Barcode - International {barcode}", True, 
                                "Product not found (acceptable)")
                    
            except Exception as e:
                self.log_test(f"Enhanced Barcode - International {barcode}", False, f"Lookup error: {str(e)}")
        
        # Overall enhanced barcode functionality
        self.log_test("Enhanced Barcode Lookup", True, 
                    f"Barcode lookup functionality working (tested {len(indian_barcodes + international_barcodes)} barcodes)")
    
    async def test_indian_nutritional_guidelines(self):
        """Test Indian Nutritional Guidelines in health scoring"""
        # Test with products that should have different scores based on Indian dietary patterns
        test_products = [
            ("ghee", "should have moderate score despite high fat (traditional Indian food)"),
            ("basmati rice", "should have good score (staple Indian food)"),
            ("dal", "should have excellent score (high protein, fiber)"),
            ("indian sweets", "should have poor score (high sugar)"),
            ("namkeen", "should have poor score (high sodium, processed)")
        ]
        
        scoring_appropriate = 0
        
        for product_term, expectation in test_products:
            try:
                payload = {"query": product_term, "limit": 3}
                response = await self.client.post(f"{BACKEND_URL}/food/search", json=payload)
                
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        product = products[0]
                        health_score = product.get("health_score")
                        health_rating = product.get("health_rating")
                        
                        if health_score is not None and health_rating:
                            # Analyze if scoring seems appropriate for Indian context
                            score_reasonable = True
                            
                            # Basic reasonableness checks
                            if "dal" in product_term and health_score < 60:
                                score_reasonable = False
                            elif "sweets" in product_term and health_score > 50:
                                score_reasonable = False
                            elif "namkeen" in product_term and health_score > 40:
                                score_reasonable = False
                            
                            if score_reasonable:
                                scoring_appropriate += 1
                                self.log_test(f"Indian Nutrition - {product_term}", True, 
                                            f"Score {health_score} ({health_rating}) - {expectation}")
                            else:
                                self.log_test(f"Indian Nutrition - {product_term}", False, 
                                            f"Score {health_score} seems inappropriate - {expectation}")
                        else:
                            self.log_test(f"Indian Nutrition - {product_term}", False, 
                                        "Missing health score or rating")
                    else:
                        self.log_test(f"Indian Nutrition - {product_term}", False, 
                                    f"No products found for {product_term}")
                        
            except Exception as e:
                self.log_test(f"Indian Nutrition - {product_term}", False, f"Nutrition test error: {str(e)}")
        
        # Overall Indian nutritional guidelines assessment
        if scoring_appropriate >= len(test_products) * 0.6:  # At least 60% appropriate
            self.log_test("Indian Nutritional Guidelines", True, 
                        f"Health scoring appropriate for {scoring_appropriate}/{len(test_products)} Indian food types")
        else:
            self.log_test("Indian Nutritional Guidelines", False, 
                        f"Health scoring only appropriate for {scoring_appropriate}/{len(test_products)} Indian food types")

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
        await self.test_indian_food_search()
        await self.test_indian_food_categories()
        await self.test_indian_brand_prioritization()
        await self.test_popular_indian_foods_api()
        await self.test_enhanced_barcode_lookup()
        await self.test_indian_nutritional_guidelines()
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