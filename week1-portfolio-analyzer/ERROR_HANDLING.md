# Error Handling in data_loader.py

## Overview
The data_loader.py module includes comprehensive error handling for CSV file loading and validation.

## Error Types

### DataLoaderError
Base exception class for all data loading errors.

### MissingColumnError
Raised when required columns are missing from the CSV.

**Required columns:**
- `ticker` - Stock symbol
- `shares` - Number of shares
- `purchase_price` - Purchase price per share
- `purchase_date` - Date of purchase

**Example:**
```python
try:
    df = load_portfolio("portfolio.csv")
except MissingColumnError as e:
    print(f"Missing column: {e}")
```

### MalformedRowError
Raised when individual rows contain invalid data.

## Validation Rules

### Required Fields
- **ticker**: Cannot be empty or null
- **shares**: Must be a positive number
- **purchase_price**: Must be a positive number
- **purchase_date**: Must be a valid date

### Optional Fields
- **sold_price**: Must be positive if provided; must have corresponding sold_date
- **sold_date**: Must have corresponding sold_price; must be after purchase_date

### Data Cleaning
The loader automatically:
- Strips whitespace from all string values
- Converts ticker symbols to uppercase
- Converts numeric strings to floats
- Converts date strings to datetime objects
- Converts whitespace-only values to NaN

## Example Usage

### Valid CSV
```csv
ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,,
MSFT,5,280.00,2023-02-20,350.00,2024-06-15
```

### Error Cases

**Missing ticker:**
```csv
ticker,shares,purchase_price,purchase_date
,10,150.00,2023-01-15
```
→ Raises: `MalformedRowError: Row 2: Missing ticker`

**Negative price:**
```csv
ticker,shares,purchase_price,purchase_date
AAPL,10,-150.00,2023-01-15
```
→ Raises: `MalformedRowError: Row 2: Purchase price must be positive`

**Sold date before purchase date:**
```csv
ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-06-15,200.00,2023-01-15
```
→ Raises: `MalformedRowError: Row 2: Sold date is before purchase date`

**Sold price without sold date:**
```csv
ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,200.00,
```
→ Raises: `MalformedRowError: Row 2: Has sold_price but missing sold_date`

## Error Handling in Application

### In app.py
The Streamlit app catches errors from data_loader and displays them to users:

```python
try:
    df = load_portfolio("portfolio.csv")
except MissingColumnError as e:
    st.error(f"Invalid portfolio data: {e}")
except MalformedRowError as e:
    st.error(f"Data validation error: {e}")
except FileNotFoundError as e:
    st.error(f"File not found: {e}")
```

## Test Coverage

Comprehensive test suite with 26 tests covering:
- ✓ Valid CSV loading
- ✓ Whitespace trimming
- ✓ Ticker uppercase conversion
- ✓ Fractional shares
- ✓ Missing columns
- ✓ Missing values
- ✓ Invalid data types
- ✓ Negative values
- ✓ Buy/sell transaction consistency
- ✓ Date ordering validation
- ✓ File handling errors
- ✓ Multiple concurrent errors

Run tests:
```bash
pytest tests/test_data_loader.py -v
```

## Benefits

1. **User-friendly errors**: Clear messages about what went wrong and where
2. **Data integrity**: Ensures only valid data is loaded into the application
3. **Robustness**: Handles edge cases like whitespace, empty values, and type mismatches
4. **Validation**: Enforces business rules (e.g., sold_date must be after purchase_date)
5. **Debugging**: Detailed error messages with row numbers help users fix their data
