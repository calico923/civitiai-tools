# Pre-Investigation Documentation

This directory contains the comprehensive API investigation results from the initial 4-day research phase (July 13-17, 2025).

## 📋 Investigation Reports

### **Core API Documentation**
- **`civitai_api_comprehensive_specification.md`** ⭐
  - Complete API specification with all endpoints
  - Request/response structures
  - Authentication details
  - Rate limiting information

- **`civitai_api_full_spec.md`**
  - Detailed field-by-field documentation
  - Data types and constraints
  - Example responses

- **`civitai_official_vs_discovered_features.md`** ⭐
  - Side-by-side comparison of documented vs actual features
  - List of all undocumented capabilities
  - Risk assessment for using unofficial features

### **Feature Discovery Reports**
- **`civitai_category_system_investigation.md`** ⭐
  - Discovery of 15 hidden category types
  - How categories work with tags
  - Implementation strategies

- **`civitai_model_types_final_complete.md`**
  - All 13 model types documented
  - Type-specific features and limitations
  - Conversion between types (LyCORIS → LoCon)

- **`civitai_sort_options_investigation.md`**
  - 10 confirmed sort options
  - Advanced sorting with sortBy parameter
  - Performance implications

- **`civitai_period_filter_specification.md`**
  - Time-based filtering options
  - Period filter implementations
  - Date range capabilities

### **Specialized Investigations**
- **`illustrious_version_investigation_report.md`**
  - Deep dive into Illustrious models
  - Version comparison methodology
  - Popular Illustrious variants

- **`api_image_findings.md`**
  - Image API endpoint discovery
  - Image metadata structures
  - Generation parameters access

## 🎯 Key Discoveries

### **API Coverage**
- **Official Documentation**: ~30 fields
- **Actual Available**: 85+ fields
- **Hidden Functionality**: 60% more than documented

### **Major Findings**
1. **License Information**: 4 fields available but undocumented
2. **Security Scans**: Virus/pickle scan results accessible
3. **Categories**: 15 hidden categories for enhanced filtering
4. **Hash Types**: 6 different hash algorithms available
5. **Creator Info**: Verification status and tier information

### **Critical Missing Features in First Implementation**
- ❌ License information (0% captured)
- ❌ Security scan results (0% captured)
- ❌ Multiple hash types (only SHA256 used)
- ❌ Creator verification status
- ❌ Category-based filtering

## 📊 Statistics

| Investigation Area | Time Spent | Findings |
|-------------------|------------|----------|
| API Endpoints | 1 day | 3 main + 4 hidden endpoints |
| Field Mapping | 1 day | 85+ fields discovered |
| Feature Testing | 1 day | 15 categories, 13 types |
| Documentation | 1 day | 10 comprehensive reports |

## 🔧 Using These Findings

### **For API Implementation**
1. Use field mappings from `civitai_api_comprehensive_specification.md`
2. Implement all security fields for user safety
3. Include license information for legal compliance
4. Support all hash types for verification

### **For Search Features**
1. Implement 15-category filtering system
2. Support all 10 sort options
3. Enable hidden search parameters
4. Use cursor pagination for large results

### **Risk Mitigation**
- Features marked "unofficial" may change
- Implement fallbacks for undocumented features
- Monitor API changes regularly
- Cache discovered features locally

## 💡 Lessons Learned

1. **Official docs cover only 40% of functionality**
2. **Categories are passed as tags in API**
3. **Multiple pagination methods available**
4. **Rich metadata exists but isn't documented**
5. **Security information is critical but hidden**

These investigation results represent a significant effort to understand the full capabilities of the CivitAI API and should be the foundation for any implementation.