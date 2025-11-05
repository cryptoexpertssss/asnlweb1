#!/usr/bin/env python3
"""
GoBeauty Backend API Testing Suite
Tests all backend endpoints for the beauty service booking app
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Backend URL from environment
BACKEND_URL = "https://beautyhub-pink.preview.emergentagent.com/api"

class GoBeautyAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_data = {
            "name": "Sarah Johnson",
            "email": "sarah.johnson@example.com", 
            "password": "SecurePass123!",
            "phone": "+1-555-0123"
        }
        self.salon_id = None
        self.service_id = None
        self.booking_id = None
        
    def log_test(self, test_name, success, details=""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if not success:
            print(f"   Error occurred in: {test_name}")
        print()

    def test_seed_data(self):
        """Test seeding sample data"""
        try:
            response = self.session.post(f"{self.base_url}/seed-data")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Message: {data.get('message', 'No message')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Seed Data", success, details)
            return success
        except Exception as e:
            self.log_test("Seed Data", False, f"Exception: {str(e)}")
            return False

    def test_user_registration(self):
        """Test user registration endpoint"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=self.test_user_data
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.auth_token = data.get('token')
                user_info = data.get('user', {})
                details = f"Status: {response.status_code}, User ID: {user_info.get('id')}, Token received: {'Yes' if self.auth_token else 'No'}"
            else:
                # Check if user already exists
                if response.status_code == 400 and "already registered" in response.text:
                    details = f"Status: {response.status_code}, User already exists (expected for repeated tests)"
                    success = True  # This is acceptable for testing
                else:
                    details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                    
            self.log_test("User Registration", success, details)
            return success
        except Exception as e:
            self.log_test("User Registration", False, f"Exception: {str(e)}")
            return False

    def test_user_login(self):
        """Test user login endpoint"""
        try:
            login_data = {
                "email": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.auth_token = data.get('token')
                user_info = data.get('user', {})
                details = f"Status: {response.status_code}, User: {user_info.get('name')}, Token: {'Received' if self.auth_token else 'Missing'}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("User Login", success, details)
            return success
        except Exception as e:
            self.log_test("User Login", False, f"Exception: {str(e)}")
            return False

    def test_get_current_user(self):
        """Test get current user endpoint (requires authentication)"""
        try:
            if not self.auth_token:
                self.log_test("Get Current User", False, "No auth token available")
                return False
                
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/auth/me",
                headers=headers
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, User: {data.get('name')}, Email: {data.get('email')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Current User", success, details)
            return success
        except Exception as e:
            self.log_test("Get Current User", False, f"Exception: {str(e)}")
            return False

    def test_get_categories(self):
        """Test get categories endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/categories")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                categories_count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Categories found: {categories_count}"
                if categories_count > 0:
                    sample_category = data[0]
                    details += f", Sample: {sample_category.get('name', 'Unknown')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Categories", success, details)
            return success
        except Exception as e:
            self.log_test("Get Categories", False, f"Exception: {str(e)}")
            return False

    def test_get_salons(self):
        """Test get salons endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/salons")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                salons_count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Salons found: {salons_count}"
                
                if salons_count > 0:
                    # Store first salon ID for later tests
                    self.salon_id = data[0].get('id')
                    sample_salon = data[0]
                    details += f", Sample: {sample_salon.get('name', 'Unknown')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Salons", success, details)
            return success
        except Exception as e:
            self.log_test("Get Salons", False, f"Exception: {str(e)}")
            return False

    def test_get_specific_salon(self):
        """Test get specific salon endpoint"""
        try:
            if not self.salon_id:
                self.log_test("Get Specific Salon", False, "No salon ID available from previous test")
                return False
                
            response = self.session.get(f"{self.base_url}/salons/{self.salon_id}")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Salon: {data.get('name', 'Unknown')}, Rating: {data.get('rating', 'N/A')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Specific Salon", success, details)
            return success
        except Exception as e:
            self.log_test("Get Specific Salon", False, f"Exception: {str(e)}")
            return False

    def test_get_services(self):
        """Test get services endpoint with salon_id filter"""
        try:
            if not self.salon_id:
                self.log_test("Get Services", False, "No salon ID available from previous test")
                return False
                
            response = self.session.get(f"{self.base_url}/services?salon_id={self.salon_id}")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                services_count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Services found: {services_count}"
                
                if services_count > 0:
                    # Store first service ID for booking test
                    self.service_id = data[0].get('id')
                    sample_service = data[0]
                    details += f", Sample: {sample_service.get('name', 'Unknown')} - ${sample_service.get('price', 0)}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get Services", success, details)
            return success
        except Exception as e:
            self.log_test("Get Services", False, f"Exception: {str(e)}")
            return False

    def test_create_booking(self):
        """Test create booking endpoint (requires authentication)"""
        try:
            if not self.auth_token:
                self.log_test("Create Booking", False, "No auth token available")
                return False
                
            if not self.service_id or not self.salon_id:
                self.log_test("Create Booking", False, "Missing service_id or salon_id from previous tests")
                return False
                
            # Create booking for tomorrow
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            booking_data = {
                "service_id": self.service_id,
                "salon_id": self.salon_id,
                "booking_date": tomorrow,
                "booking_time": "14:30",
                "notes": "First time customer, please call before appointment"
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.post(
                f"{self.base_url}/bookings",
                json=booking_data,
                headers=headers
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.booking_id = data.get('id')
                details = f"Status: {response.status_code}, Booking ID: {self.booking_id}, Service: {data.get('service_name', 'Unknown')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Create Booking", success, details)
            return success
        except Exception as e:
            self.log_test("Create Booking", False, f"Exception: {str(e)}")
            return False

    def test_get_user_bookings(self):
        """Test get user bookings endpoint (requires authentication)"""
        try:
            if not self.auth_token:
                self.log_test("Get User Bookings", False, "No auth token available")
                return False
                
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/bookings",
                headers=headers
            )
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                bookings_count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Bookings found: {bookings_count}"
                
                if bookings_count > 0:
                    latest_booking = data[0]
                    details += f", Latest: {latest_booking.get('service_name', 'Unknown')} on {latest_booking.get('booking_date', 'Unknown')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
                
            self.log_test("Get User Bookings", success, details)
            return success
        except Exception as e:
            self.log_test("Get User Bookings", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("=" * 60)
        print("GoBeauty Backend API Testing Suite")
        print("=" * 60)
        print(f"Testing backend at: {self.base_url}")
        print()
        
        test_results = []
        
        # Test sequence
        tests = [
            ("Seed Data", self.test_seed_data),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Get Current User", self.test_get_current_user),
            ("Get Categories", self.test_get_categories),
            ("Get Salons", self.test_get_salons),
            ("Get Specific Salon", self.test_get_specific_salon),
            ("Get Services", self.test_get_services),
            ("Create Booking", self.test_create_booking),
            ("Get User Bookings", self.test_get_user_bookings)
        ]
        
        for test_name, test_func in tests:
            result = test_func()
            test_results.append((test_name, result))
        
        # Summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print()
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend API is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the details above.")
            return False

if __name__ == "__main__":
    tester = GoBeautyAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)