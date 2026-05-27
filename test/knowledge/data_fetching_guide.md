# ClickHouse Data Fetching Guide

## Overview
Learn how to fetch data from ClickHouse database using the SQL data fetching tool.

## Available Tables

### loan_applications_silver
Main table containing loan application data.

**Key Columns:**
- `id` - Unique loan application ID
- `user_id` - User identifier (e.g., 58905225)
- `created_at` - Timestamp when application was created
- `loan_amount` - Amount of the loan
- `merchant_id` - Associated merchant
- `application_status` - Current status of application
- `order_value` - Order value
- `tenure` - Loan tenure in months
- `emi_amount` - EMI amount
- `field_of_study` - Field of study (app version)
- `is_repeat` - Whether it's a repeat customer (0 or 1)
- `udf2` - Platform identifier (android_customer_app, ios_customer_app, etc.)

### merchants_silver
Table containing merchant information.

**Key Columns:**
- `id` - Merchant ID
- `name` - Merchant name
- `channel` - Merchant channel (online_mobile, etc.)
- `is_evoucher_merchant` - Whether merchant accepts e-vouchers

## Query Examples

### 1. Fetch data for a specific user
**Task:** Get created_at, id, and user_id for user_id 58905225 from loan_applications_silver

**Query:**
```sql
SELECT created_at, id, user_id 
FROM loan_applications_silver 
WHERE user_id = '58905225'
LIMIT 100
```

**Using the tool:** "Fetch created_at, id, user_id from loan_applications_silver where user_id is 58905225"

### 2. Fetch data by date range
**Task:** Get loan data created after 2026-05-20

**Query:**
```sql
SELECT created_at, id, user_id, loan_amount 
FROM loan_applications_silver 
WHERE created_at >= '2026-05-20'
LIMIT 1000
```

**Using the tool:** "Fetch loan applications created after 2026-05-20 with id, user_id, and loan_amount columns"

### 3. Fetch with multiple filters
**Task:** Get loan data for specific user with status filter

**Query:**
```sql
SELECT created_at, id, user_id, loan_amount, application_status 
FROM loan_applications_silver 
WHERE user_id = '58905225' 
AND application_status IN ('approved', 'completed')
```

**Using the tool:** "Fetch loan data for user 58905225 with approved or completed status"

### 4. Complex joins with merchants
**Task:** Get loan applications with merchant details

**Query:**
```sql
SELECT 
    la.created_at,
    la.id,
    la.user_id,
    la.loan_amount,
    m.name AS merchant_name,
    m.channel
FROM loan_applications_silver la
LEFT JOIN merchants_silver m ON la.merchant_id = m.id
WHERE la.created_at >= '2026-05-20'
LIMIT 500
```

**Using the tool:** "Fetch loan applications with merchant names created after 2026-05-20"

## Key Tips

### Date Filters
- Always use ISO format: YYYY-MM-DD
- Use `>=` for "after a date" and `<` for "before a date"
- Example: `WHERE created_at >= '2026-05-20' AND created_at < '2026-05-21'`

### String Values
- User IDs and identifiers are strings: `WHERE user_id = '58905225'`
- Use single quotes for string values in SQL

### Column Names
- Use exact column names as listed above
- Common columns: `created_at`, `id`, `user_id`, `loan_amount`, `application_status`

### Performance
- Always add `LIMIT` for large queries to avoid timeouts
- Use specific WHERE conditions to filter data early
- Example: `LIMIT 1000` for 1000 rows

### Aggregations
- Use `COUNT()` for counting records
- Use `SUM()` for totals
- Use `AVG()` for averages
- Use `GROUP BY` for grouping results

## Common Query Patterns

### Count records for a user
```sql
SELECT COUNT(*) as count 
FROM loan_applications_silver 
WHERE user_id = '58905225'
```

### Get latest records
```sql
SELECT * FROM loan_applications_silver 
WHERE user_id = '58905225' 
ORDER BY created_at DESC 
LIMIT 10
```

### Filter by status
```sql
SELECT * FROM loan_applications_silver 
WHERE application_status = 'approved'
LIMIT 100
```

### Filter by merchant channel
```sql
SELECT * FROM loan_applications_silver 
WHERE udf2 = 'android_customer_app' 
AND is_repeat = 0
LIMIT 100
```

## Root-cause Playbooks
- `knowledge/online_apparel_tv_cc_drop_playbook.md` — tv/cc drop investigation playbook for `online_apparel`
- `knowledge/online_mobile_cc_users_playbook.md` — cc_users drop investigation playbook for `online_mobile`

## Usage Instructions

When you need to fetch data:
1. **Specify the table** - Which table to query (loan_applications_silver, merchants_silver, etc.)
2. **Choose columns** - Which columns you need (id, user_id, created_at, etc.)
3. **Add filters** - Any WHERE conditions (user_id, date range, status, etc.)
4. **Set limit** - How many rows you need (add LIMIT to avoid too much data)

Example requests:
- "Fetch all loans for user 58905225"
- "Get loan data created after 2026-05-20 with amount > 10000"
- "Count how many approved loans we have for user 58905225"
- "Show merchant names for loans in the last 7 days"
