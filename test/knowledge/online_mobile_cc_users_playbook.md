# Online Mobile cc_users Drop Investigation Playbook

## Overview
This playbook is for investigating drops in `cc_users` for the `online_mobile` flow using a **5% threshold-based approach**.

**Quick summary of the workflow:**
1. **Step 1** — Fetch daily cc_users for the target date
2. **Step 2** — Compare with same date from previous month and calculate relative difference
3. **Decision** — If drop > 5%, trigger investigation; else stop
4. **Step 3** — If triggered, fetch last 5 days raw data from both months
5. **Analysis** — Drill down by tenure, ov_bucket, is_repeat, merchant, and sub_channel
6. **Root cause** — Identify the specific segment(s) that dropped and explain why

Use the queries in order. Skip to next step only if the previous step confirms a drop.

## Metric definition
- `cc_users` = distinct `user_id` values in `loan_applications_silver`
- `online_mobile` filter = `m.channel = 'online_mobile'`
- use date conversion to IST: `created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE`

## Step 1: Base cc_users query
```sql
SELECT
  toDate(la.created_at + INTERVAL 330 MINUTE) AS date_x,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 330 MINUTE) BETWEEN '{start_date}' AND '{end_date}'
GROUP BY date_x
```

> Note: the alias `date_x` cannot be used directly in `WHERE` in ClickHouse, so repeat the expression or use a subquery.

## Step 2: Same-day previous month comparison and threshold check
Compare today's `cc_users` against the same date from the previous month and calculate relative difference.

### Comparison query with relative difference
```sql
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) IN ('{current_date}', '{previous_month_same_date}')
GROUP BY date_x
ORDER BY date_x
```

### Relative difference calculation
From the results, calculate the percentage drop:
```
relative_diff = (cc_users_prev_month - cc_users_current) / cc_users_prev_month * 100
```

**Decision rule:**
- If `relative_diff > 5%` → **TRIGGER INVESTIGATION** (proceed to Step 3)
- If `relative_diff <= 5%` → No significant drop, monitoring continues

### Example calculation
- Previous month (2026-04-14): 25,000 cc_users
- Current month (2026-05-14): 24,000 cc_users
- Relative diff = (25,000 - 24,000) / 25,000 * 100 = **4%** (no investigation)

- Previous month (2026-04-14): 25,000 cc_users
- Current month (2026-05-14): 23,500 cc_users
- Relative diff = (25,000 - 23,500) / 25,000 * 100 = **6%** (TRIGGER investigation)

---

## Step 3: Investigation mode (triggered when drop > 5%)
When a drop exceeds 5%, fetch raw data from the last 5 days of both months for deeper analysis.

### Last 5 days comparison query
```sql
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  la.tenure,
  la.ov_bucket,
  la.is_repeat,
  la.merchant_id,
  m.name AS merchant_name,
  m.sub_channel,
  countDistinct(la.user_id) AS cc_users,
  countDistinct(CASE WHEN la.application_status NOT IN ('rejected', 'pending') THEN la.user_id END) AS active_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND (
    (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR
    (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}')
  )
GROUP BY date_x, la.tenure, la.ov_bucket, la.is_repeat, la.merchant_id, m.name, m.sub_channel
ORDER BY date_x DESC, cc_users DESC
```

### Raw data investigation workflow
1. **By tenure**: Which tenure bucket(s) saw the biggest drop?
2. **By ov_bucket**: Which order-value bucket(s) lost the most users?
3. **By is_repeat**: Did first-time or repeat users drop more?
4. **By merchant**: Which merchant(s) contributed most to the drop?
5. **By sub_channel**: Which sub-channel within online_mobile dropped?
6. **Segment drill-down**: If a specific segment dropped > 5%, drill one level deeper

### Drill-down query template (for a specific segment)
```sql
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  la.udf2,
  COUNT(*) AS app_count,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND la.tenure = '{identified_tenure}'
  AND (
    (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR
    (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}')
  )
GROUP BY date_x, la.udf2
ORDER BY date_x DESC, cc_users DESC
```

---

## Step 2 (old): Identify the drop pattern
- Always use the actual expression in `WHERE` instead of relying on the `date_x` alias.
- Confirm whether the drop is a single-day dip or a recurring same-weekday drop month-over-month.
- If the same weekday from the previous month also fell, prioritize `tenure` and `ov_bucket` segment checks.
- Use additional filters only after the broad segment checks identify the weak bucket.

### Same-day previous month comparison query
```sql
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  la.tenure,
  la.ov_bucket,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) IN ('2026-05-14', '2026-04-16')
GROUP BY date_x, la.tenure, la.ov_bucket
ORDER BY date_x, cc_users DESC
```

- Replace `2026-04-16` with the same weekday from the prior month for the date you are investigating.
- If the drop is specific to one `tenure` or `ov_bucket`, drill deeper on that segment.

## Step 3: Drill down by tenure and ov_bucket
When a same-day prior-month drop is visible, check where the drop is concentrated.

### Tenure analysis
```sql
SELECT
  la.tenure,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{start_date}' AND '{end_date}'
GROUP BY la.tenure
ORDER BY cc_users DESC
```

### OV bucket analysis
```sql
SELECT
  la.ov_bucket,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{start_date}' AND '{end_date}'
GROUP BY la.ov_bucket
ORDER BY cc_users DESC
```

## Step 4: Compare same-day previous month
Use the same queries with a shifted date range to compare `current_day` vs `same_weekday_last_month`.

### Same-day previous month example
```sql
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  la.tenure,
  la.ov_bucket,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE m.channel = 'online_mobile'
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) IN ('{current_date}', '{previous_month_same_weekday}')
GROUP BY date_x, la.tenure, la.ov_bucket
ORDER BY date_x, cc_users DESC
```

## Step 5: Additional segment filters
If the drop remains unexplained, add filters for:
- `la.is_repeat`
- `la.merchant_id`
- `m.sub_channel`
- `la.udf2`
- `m.name`
- `la.application_status`

## Analysis guidance
**New workflow (5% threshold-based):**
1. Run the base `cc_users` query for current date and previous month same date
2. Calculate relative difference: `(prev_month - current) / prev_month * 100`
3. If drop ≤ 5% → No investigation needed
4. If drop > 5% → **TRIGGER INVESTIGATION**:
   - Fetch last 5 days from both months using Step 3 investigation query
   - Analyze by tenure, ov_bucket, is_repeat, merchant, sub_channel
   - Identify which segment(s) dropped > 5%
   - Drill down on that segment to find root cause

**Presentation of findings:**
- State the overall `cc_users` drop percentage
- Identify the primary driver (tenure, ov_bucket, merchant, repeat vs first-time)
- Back findings with actual counts and percentages from both months
- Suggest corrective action based on root cause
