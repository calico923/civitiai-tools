# Problematic Tests

This directory contains tests that have been identified as having issues and need improvement.

## Issues Identified

### Category 1: Over-mocking Business Logic (❌ BAD)

#### API Client Tests (`test_api_client_problematic.py`)
- **`test_search_models_problematic`**: Mocks `_make_request` bypassing URL construction, parameter handling
- **`test_get_model_details_problematic`**: Same over-mocking issue
- **`test_get_model_version_problematic`**: Same over-mocking issue  
- **`test_context_manager_problematic`**: Tests implementation details (session.closed) not behavior

#### Search Engine Tests (`test_search_additional_problematic.py`)
- **`test_basic_search_problematic`**: Only tests that mocked data comes back unchanged
- **`test_search_with_query_problematic`**: Mock filtering too simple
- **`test_search_by_type_problematic`**: Mock filtering trivial
- **`test_filter_by_base_model_problematic`**: Mock always returns same result
- **`test_cached_search_problematic`**: Only tests call counting, not cache correctness

#### Unit Tests (`test_unit_problematic.py`)
- **`test_search_models_basic_problematic`**: Hardcoded mock doesn't test parameter construction
- **`test_init_with_api_key_problematic`**: Too shallow, basic property testing
- **`test_search_models_with_filters_problematic`**: Simplified mock doesn't test real behavior
- **`test_search_basic_problematic`**: Trivial assertions, no business logic testing
- **`test_search_with_multiple_tags_problematic`**: Oversimplified mock logic

### Category 2: Already Fixed Tests (`test_search_problematic.py`)
- **`test_search_similar_problematic`**: Fixed in main test suite
- **`test_get_by_creator_problematic`**: Fixed in main test suite  
- **`test_pagination_problematic`**: Fixed in main test suite

## Anti-Patterns Identified

1. **Over-mocking**: Mocking business logic instead of dependencies
2. **Trivial assertions**: Testing that mock data comes back unchanged
3. **Bypassing logic**: Mocking so high-level that core logic is never tested
4. **Unrealistic scenarios**: Mocks that don't represent real-world complexity
5. **Testing mocks**: Assertions about mock behavior rather than business logic

## Improvement Guidelines

Tests should:
1. **Mock at infrastructure boundaries**: HTTP requests, file systems, not business logic
2. **Test realistic scenarios**: Use complex data that exercises real code paths
3. **Validate transformations**: Test how inputs are transformed to outputs
4. **Test error conditions**: Include negative test cases and edge conditions
5. **Verify behavior**: Test what the code does, not how it's implemented

## Status

- **Moved**: 2025-07-18
- **Total moved**: 18 problematic tests
- **Reason**: Over-mocking, trivial assertions, unrealistic scenarios
- **Action**: Removed from main test suite to improve overall test quality