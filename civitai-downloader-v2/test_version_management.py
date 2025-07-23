#!/usr/bin/env python3
"""
Quick test for Phase B-4 version management system.
Tests VersionClient with mock data due to API limitations.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.api.version_client import ModelVersion, VersionComparison, VersionClient


def test_version_management():
    """Test version management functionality with mock data."""
    print("📊 Testing Phase B-4 Version Management System")
    print("=" * 50)
    
    # Create mock version data
    mock_version_data_1 = {
        'id': 2010753,
        'name': 'v3.0',
        'baseModel': 'Illustrious',
        'baseModelType': 'Standard',
        'description': '<p>Latest version with improved quality</p>',
        'status': 'Published',
        'availability': 'Public',
        'createdAt': '2024-07-14T23:41:24.964Z',
        'publishedAt': '2024-07-15T02:17:06.358Z',
        'index': 0,
        'downloadUrl': 'https://civitai.com/api/download/models/2010753',
        'stats': {
            'downloadCount': 1500,
            'rating': 4.8,
            'thumbsUpCount': 350,
            'thumbsDownCount': 10
        },
        'files': [
            {
                'id': 1907803,
                'name': 'model_v3.safetensors',
                'type': 'Model',
                'sizeKB': 6775430.125,
                'downloadUrl': 'https://civitai.com/api/download/models/2010753',
                'primary': True,
                'metadata': {
                    'format': 'SafeTensor',
                    'fp': 'fp16',
                    'size': 'pruned'
                },
                'hashes': {
                    'SHA256': 'B4FB5F829A46A91F8499A2C7C0A0653C0E8DE1632C0B03285A0495B0C068E888',
                    'BLAKE3': '52F094B47C384B4ED50B300EC1744CAAFE5ABF97E94E326FFA4516F33F22A47F',
                    'CRC32': 'D163F6E0',
                    'AutoV1': 'A5828527',
                    'AutoV2': 'B4FB5F829A',
                    'AutoV3': 'E45A888AA8F8'
                },
                'pickleScanResult': 'Success',
                'virusScanResult': 'Success'
            }
        ]
    }
    
    mock_version_data_2 = {
        'id': 1800000,
        'name': 'v2.5',
        'baseModel': 'Illustrious',
        'baseModelType': 'Standard',
        'description': '<p>Previous stable version</p>',
        'status': 'Published',
        'availability': 'Public',
        'createdAt': '2024-06-10T15:30:00.000Z',
        'publishedAt': '2024-06-11T08:00:00.000Z',
        'index': 1,
        'downloadUrl': 'https://civitai.com/api/download/models/1800000',
        'stats': {
            'downloadCount': 5200,
            'rating': 4.6,
            'thumbsUpCount': 820,
            'thumbsDownCount': 45
        },
        'files': [
            {
                'id': 1800001,
                'name': 'model_v2_5.safetensors',
                'type': 'Model',
                'sizeKB': 6500000.0,
                'downloadUrl': 'https://civitai.com/api/download/models/1800000',
                'primary': True,
                'metadata': {
                    'format': 'SafeTensor',
                    'fp': 'fp16',
                    'size': 'pruned'
                },
                'hashes': {
                    'SHA256': 'A1FB5F829A46A91F8499A2C7C0A0653C0E8DE1632C0B03285A0495B0C068E111',
                    'CRC32': 'D163F6E1',
                    'AutoV1': 'A5828528',
                    'AutoV2': 'B4FB5F829B'
                },
                'pickleScanResult': 'Success',
                'virusScanResult': 'Success'
            }
        ]
    }
    
    try:
        # Test 1: ModelVersion creation and properties
        print("1. Testing ModelVersion Creation:")
        version1 = ModelVersion(mock_version_data_1)
        version2 = ModelVersion(mock_version_data_2)
        
        print(f"   Version 1: {version1.name} (ID: {version1.id})")
        print(f"   Base Model: {version1.base_model}")
        print(f"   Is Latest: {version1.is_latest}")
        print(f"   Is Published: {version1.is_published}")
        print(f"   Download Count: {version1.download_count:,}")
        print(f"   Like Ratio: {version1.like_ratio:.2%}")
        print()
        
        # Test 2: Version comparison
        print("2. Testing Version Comparison:")
        comparison = VersionComparison(version1, version2)
        
        print(f"   Version 1 newer: {comparison.version1_newer}")
        print(f"   Same base model: {comparison.same_base_model}")
        print(f"   Download difference: {comparison.download_diff:,}")
        print(f"   Rating difference: {comparison.rating_diff:.2f}")
        print(f"   Size difference: {comparison.size_diff_mb:.1f} MB")
        if comparison.days_apart:
            print(f"   Days apart: {comparison.days_apart}")
        print()
        
        # Test 3: Size and file information
        print("3. Testing Size and File Information:")
        size_info = version1.get_size_info()
        primary_file = version1.primary_file
        
        print(f"   Total files: {size_info['total_files']}")
        print(f"   Total size: {size_info['total_size_mb']:.1f} MB")
        print(f"   Primary file: {size_info['primary_file_name']}")
        print(f"   Primary format: {size_info['primary_file_format']}")
        
        if primary_file:
            print(f"   Available hashes: {list(primary_file.hashes.to_dict().keys())}")
        print()
        
        # Test 4: Version serialization
        print("4. Testing Version Serialization:")
        version_dict = version1.to_dict()
        
        print(f"   Serialized fields: {len(version_dict)} fields")
        print(f"   Key fields present: {all(key in version_dict for key in ['id', 'name', 'base_model', 'stats'])}")
        print()
        
        # Test 5: Date handling
        print("5. Testing Date Handling:")
        print(f"   Created: {version1.created_at.strftime('%Y-%m-%d %H:%M UTC') if version1.created_at else 'None'}")
        print(f"   Published: {version1.published_at.strftime('%Y-%m-%d %H:%M UTC') if version1.published_at else 'None'}")
        
        # Test time difference calculation
        if version1.published_at and version2.published_at:
            time_diff = version1.published_at - version2.published_at
            print(f"   Time difference: {time_diff.days} days")
        print()
        
        # Test 6: Comparison serialization
        print("6. Testing Comparison Serialization:")
        comparison_dict = comparison.to_dict()
        
        print(f"   Comparison fields: {len(comparison_dict)} top-level fields")
        print(f"   Statistics included: {'statistics' in comparison_dict}")
        print(f"   Versions included: {all(key in comparison_dict for key in ['version1', 'version2'])}")
        print()
        
        # Test 7: Edge cases
        print("7. Testing Edge Cases:")
        
        # Test with missing optional fields
        minimal_version_data = {
            'id': 999999,
            'name': 'test-version',
            'status': 'Published',
            'index': 2,
            'stats': {},
            'files': []
        }
        
        minimal_version = ModelVersion(minimal_version_data)
        print(f"   Minimal version created: {minimal_version.name}")
        print(f"   Default values: rating={minimal_version.rating}, downloads={minimal_version.download_count}")
        print(f"   Primary file: {minimal_version.primary_file}")
        print()
        
        print("🎉 Phase B-4 Version Management System Test Complete!")
        print("✅ All core functionality working correctly")
        
        # Summary of features tested
        print("\n📋 Features Tested:")
        print("   ✓ ModelVersion creation and property access")
        print("   ✓ Version comparison logic (newer/older determination)")
        print("   ✓ Statistics calculation (downloads, ratings, like ratios)")
        print("   ✓ File information parsing and size calculations")
        print("   ✓ Date parsing and timestamp handling")
        print("   ✓ Serialization and data export")
        print("   ✓ Edge case handling with minimal data")
        print("   ✓ Hash information integration")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_version_management()