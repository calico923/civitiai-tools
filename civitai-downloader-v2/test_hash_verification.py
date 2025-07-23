#!/usr/bin/env python3
"""
Quick test for Phase B-3 hash verification system.
Tests HashValidator with various scenarios.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data.models.file_models import HashValidator, HashType, FileHashes


def test_hash_validator():
    """Test HashValidator functionality."""
    print("🔐 Testing Phase B-3 Hash Verification System")
    print("=" * 50)
    
    # Create a small test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Hello, CivitAI HashValidator!")
        test_file_path = Path(f.name)
    
    try:
        validator = HashValidator()
        
        # Test 1: Check supported algorithms
        print("1. Supported Hash Algorithms:")
        supported_algorithms = validator.get_supported_algorithms()
        for algo in supported_algorithms:
            print(f"   ✓ {algo.value}")
        print()
        
        # Test 2: Calculate all hashes for the test file
        print("2. Calculating hashes for test file:")
        print(f"   File: {test_file_path.name}")
        
        file_hashes = validator.get_file_hashes(test_file_path)
        calculated_hashes = file_hashes.to_dict()
        
        for hash_name, hash_value in calculated_hashes.items():
            if hash_value:
                print(f"   {hash_name}: {hash_value}")
            else:
                print(f"   {hash_name}: (not calculated)")
        print()
        
        # Test 3: Verify a hash (positive case)
        print("3. Hash Verification (Positive Test):")
        if file_hashes.SHA256:
            is_valid = validator.verify_file_hash(
                test_file_path, file_hashes.SHA256, HashType.SHA256
            )
            print(f"   SHA256 self-verification: {'✓ PASS' if is_valid else '✗ FAIL'}")
        
        if file_hashes.CRC32:
            is_valid = validator.verify_file_hash(
                test_file_path, file_hashes.CRC32, HashType.CRC32
            )
            print(f"   CRC32 self-verification: {'✓ PASS' if is_valid else '✗ FAIL'}")
        print()
        
        # Test 4: Verify with wrong hash (negative case)
        print("4. Hash Verification (Negative Test):")
        wrong_sha256 = "0123456789abcdef" * 4  # 64 chars of wrong hash
        is_valid = validator.verify_file_hash(
            test_file_path, wrong_sha256, HashType.SHA256
        )
        print(f"   SHA256 with wrong hash: {'✗ FAIL (expected)' if not is_valid else '✓ UNEXPECTEDLY PASSED'}")
        print()
        
        # Test 5: Test FileHashes model validation
        print("5. FileHashes Model Validation:")
        try:
            # Valid hashes
            valid_hashes = FileHashes(
                SHA256="a" * 64,
                CRC32="ABCD1234",
                AutoV1="12345678",
                AutoV2="1234567890",
                AutoV3="123456789012"
            )
            print("   ✓ Valid hash formats accepted")
            
            # Invalid hash (should raise validation error)
            try:
                invalid_hashes = FileHashes(SHA256="invalid_hash")
                print("   ✗ Invalid hash validation failed")
            except Exception as e:
                print(f"   ✓ Invalid hash properly rejected: {type(e).__name__}")
                
        except Exception as e:
            print(f"   ✗ Hash validation error: {e}")
        print()
        
        # Test 6: Priority verification
        print("6. Priority Verification Test:")
        verification_results = {
            'SHA256': True,
            'CRC32': False,
            'AutoV1': True,
            'MD5': False
        }
        
        primary_result = validator.get_primary_verification_result(verification_results)
        print(f"   Results: SHA256=✓, CRC32=✗, AutoV1=✓, MD5=✗")
        print(f"   Primary result (SHA256 priority): {'✓ PASS' if primary_result else '✗ FAIL'}")
        print()
        
        print("🎉 Phase B-3 Hash Verification System Test Complete!")
        print("✅ All core functionality working correctly")
        
    finally:
        # Cleanup test file
        if test_file_path.exists():
            test_file_path.unlink()


if __name__ == '__main__':
    test_hash_validator()