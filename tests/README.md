# Test Suite for FASER Alignment Scripts

This directory contains tests for validating the HTCondor DAGman-based alignment workflow.

## Test Files

### Unit Tests

- **`test_config.py`**: Tests for configuration management
  - Configuration file loading and validation
  - Path configuration
  - Error handling for invalid configurations

- **`test_dag_generation.py`**: Tests for DAG generation
  - DAG file creation
  - Submit file generation
  - Job dependency management
  - Directory structure creation

- **`test_mermaid_diagrams.py`**: Tests for Mermaid diagram validation
  - Extracts Mermaid diagrams from markdown files
  - Validates syntax (balanced brackets, braces, parentheses)
  - Checks for common syntax errors
  - Optional CLI validation if mermaid-cli is installed

### Integration Tests

- **`test_integration.sh`**: End-to-end integration test
  - Full workflow validation
  - Configuration management
  - DAG generation (dry run)
  - Submit file validation
  - Directory structure verification

## Running Tests

### Prerequisites

Before running tests, ensure you have:
- Python 3.6 or newer installed
- Access to the repository root directory
- Write permissions to create temporary test files

**Verify Python version:**
```bash
python3 --version
# Should show Python 3.6 or newer
```

### Run All Tests

**Quick test run (all tests):**
```bash
# From repository root
cd /path/to/faser-alignment-script

# Run all unit tests with verbose output
python3 tests/test_config.py -v
python3 tests/test_dag_generation.py -v

# Run Mermaid diagram validation
python3 tests/test_mermaid_diagrams.py

# Run integration test
bash tests/test_integration.sh
```

**Expected output:**
- All tests should PASS
- No errors or failures should be reported
- Integration test should show "All tests passed!"

### Run Specific Test

**Run a specific test class:**
```bash
# Test only configuration-related functionality
python3 tests/test_config.py TestAlignmentConfig -v

# Test only DAG generation functionality  
python3 tests/test_dag_generation.py TestDAGGeneration -v
```

**Run a specific test method:**
```bash
# Test only configuration loading
python3 tests/test_config.py TestAlignmentConfig.test_load_config -v

# Test only DAG file creation
python3 tests/test_dag_generation.py TestDAGGeneration.test_dag_file_creation -v
```

**Run tests with different verbosity levels:**
```bash
# Minimal output
python3 tests/test_config.py

# Verbose output (shows each test)
python3 tests/test_config.py -v

# Very verbose output (shows detailed test execution)
python3 tests/test_config.py -vv
```

## Test Coverage

The test suite covers:

1. **Configuration Management**
   - JSON configuration loading
   - Path validation
   - Default configuration creation
   - Error handling

2. **DAG Generation**
   - DAG file structure
   - Job definitions
   - Dependency chains
   - Submit file content
   - HTCondor settings

3. **Documentation Quality**
   - Mermaid diagram syntax validation
   - Balanced brackets and parentheses
   - Valid diagram type declarations
   - Style definition correctness

4. **Integration**
   - Complete workflow execution (dry run)
   - File generation
   - Directory structure
   - RawList processing

## Test Requirements

- Python 3.6+
- Standard library modules (no external dependencies)
- Bash shell (for integration tests)

## Adding New Tests

When adding new functionality to the project, follow these guidelines for test development:

### Test Development Guidelines

1. **Add unit tests to the appropriate test file**
   - Configuration tests → `test_config.py`
   - DAG generation tests → `test_dag_generation.py`
   - Documentation tests → `test_mermaid_diagrams.py`
   - Create new test file if needed for new components

2. **Update integration test if workflow changes**
   - Modify `test_integration.sh` when adding new workflow steps
   - Ensure end-to-end scenarios are covered
   - Test both success and failure cases

3. **Ensure tests are independent**
   - Each test should be self-contained
   - Tests should not depend on execution order
   - Use `setUp()` and `tearDown()` methods for test initialization and cleanup

4. **Use temporary directories for file operations**
   - Never write to the actual repository during tests
   - Use `tempfile.mkdtemp()` for temporary directories
   - Example:
     ```python
     import tempfile
     import shutil
     
     def setUp(self):
         self.temp_dir = tempfile.mkdtemp()
     
     def tearDown(self):
         shutil.rmtree(self.temp_dir)
     ```

5. **Clean up test artifacts**
   - Remove all temporary files and directories in `tearDown()`
   - Verify cleanup with assertions if critical
   - Handle cleanup errors gracefully

### Example Test Structure

```python
import unittest
import tempfile
import shutil
import os

class TestNewFeature(unittest.TestCase):
    """Tests for new feature"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.txt')
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_feature_basic(self):
        """Test basic feature functionality"""
        # Test implementation
        self.assertTrue(True)
    
    def test_feature_edge_case(self):
        """Test edge case handling"""
        # Test implementation
        self.assertRaises(ValueError, some_function, invalid_input)

if __name__ == '__main__':
    unittest.main()
```

### Testing Best Practices

**Do:**
- ✅ Write descriptive test names: `test_config_validates_missing_paths`
- ✅ Test both success and failure scenarios
- ✅ Use assertions to verify expected behavior
- ✅ Document complex test logic with comments
- ✅ Keep tests fast (< 1 second per test when possible)

**Don't:**
- ❌ Write tests that require network access
- ❌ Write tests that depend on CERN infrastructure
- ❌ Write tests that modify the repository
- ❌ Write tests that depend on system-specific paths
- ❌ Write tests that require manual intervention

## Continuous Integration

These tests are designed to run in CI/CD pipelines without requiring:
- HTCondor installation
- CERN infrastructure access  
- External dependencies beyond Python standard library

They validate the correctness of generated files and workflow logic.

### CI/CD Integration

**Suitable for:**
- GitHub Actions
- GitLab CI/CD
- Jenkins
- Travis CI
- Any CI/CD platform with Python support

**Example GitHub Actions workflow:**
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Run unit tests
      run: |
        python3 tests/test_config.py -v
        python3 tests/test_dag_generation.py -v
        python3 tests/test_mermaid_diagrams.py
    
    - name: Run integration test
      run: bash tests/test_integration.sh
```

### Local Testing Before Commit

**Recommended workflow:**
```bash
# 1. Make your changes to the code

# 2. Run all tests locally
python3 tests/test_config.py -v
python3 tests/test_dag_generation.py -v
python3 tests/test_mermaid_diagrams.py
bash tests/test_integration.sh

# 3. Verify all tests pass

# 4. Commit your changes
git add .
git commit -m "Your commit message"
git push
```

### Troubleshooting Test Failures

**If tests fail:**

1. **Check Python version:**
   ```bash
   python3 --version
   # Must be 3.6 or newer
   ```

2. **Check for permission issues:**
   ```bash
   # Tests need write access to create temporary files
   ls -la tests/
   ```

3. **Check for conflicting test artifacts:**
   ```bash
   # Clean up any leftover test files
   rm -rf tests/tmp_*
   rm -rf Y2023_*
   ```

4. **Run tests individually:**
   ```bash
   # Isolate which test is failing
   python3 tests/test_config.py -v 2>&1 | less
   ```

5. **Check test output for details:**
   - Read the error messages carefully
   - Check which assertion failed
   - Verify test preconditions are met
