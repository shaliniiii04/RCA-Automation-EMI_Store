"""
ClickHouse SQL Query Examples

This file shows how to use the ClickHouse connector tool for common queries.
"""

from tools.sql_generator import ClickHouseConnector, fetch_data_from_clickhouse
import pandas as pd

# ==============================================================================
# EXAMPLE 1: Using the connector directly (like your original code)
# ==============================================================================


def example_loan_applications_query():
    """
    Fetch loan application data with complex transformations.
    Similar to your cc_tv_fxn implementation.
    """
    connector = ClickHouseConnector()
    connector.connect()

    query = """
        SELECT
            DATE(la.created_at + INTERVAL '330' MINUTE) AS date_x,
            la.created_at + INTERVAL '330' MINUTE as created_at_loan,
            toStartOfHour(la.created_at + INTERVAL 330 MINUTE) AS hour_x,
            la.user_id,
            la.is_repeat,
            la.id AS loan_id,
            m.id AS mer_id,
            m.name AS merchant_name,
            m.is_evoucher_merchant,
            m.channel AS mer_channel,
            la.field_of_study as field_of_study,
            la.order_value,
            la.tenure,
            (la.down_payment + la.processing_fees - la.cashback) AS tdp,
            COALESCE(la.merchant_closing_fees, 0) + COALESCE(la.merchant_fees, 0) + COALESCE(la.subvention_fees, 0) + COALESCE(la.p_and_s_charges, 0) + COALESCE(la.customer_subvention, 0)
            + COALESCE(la.processing_fees, 0) + COALESCE(la.documentation_charges, 0) + COALESCE((la.emi_amount * la.tenure) - la.loan_amount, 0) - COALESCE(la.cashback, 0) AS total_loan_revenue,
            la.application_status,
            la.product_master_id,
            la.emi_amount,
            la.loan_amount,
            (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0)- COALESCE(la.loan_amount,0)) AS interest,
            CASE WHEN (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0) - COALESCE(la.loan_amount,0)) = 0 THEN la.user_id
            ELSE NULL
            END AS zero_interest_user,
            CASE WHEN (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0) - COALESCE(la.loan_amount,0)) = 0 AND la.processing_fees = 0 THEN la.user_id
            ELSE NULL
            END AS zero_interest_tag_user
        FROM loan_applications_silver la
        LEFT JOIN merchants_silver m
            ON m.id = la.merchant_id  
        WHERE la.created_at >= '2026-05-20'
            AND la.created_at < '2026-05-21'
            AND la.field_of_study IS NOT NULL
            AND la.udf2 = 'android_customer_app'
            AND m.channel IN ('online_mobile')
            AND la.is_repeat = 0
            AND tdp = 19
    """

    # Get data as pandas DataFrame
    df = connector.fetch_dataframe(query)
    connector.disconnect()

    return df


# ==============================================================================
# EXAMPLE 2: Using the fetch function directly (simpler)
# ==============================================================================


def example_simple_query():
    """
    Simple query - fetch data from a table.
    Returns JSON string by default.
    """
    query = """
        SELECT created_at, id, user_id, loan_amount
        FROM loan_applications_silver
        WHERE created_at >= '2026-05-20'
        LIMIT 100
    """

    # Returns JSON string
    result = fetch_data_from_clickhouse(query)
    print(result)


# ==============================================================================
# EXAMPLE 3: Using the fetch function with DataFrame
# ==============================================================================


def example_with_dataframe():
    """
    Fetch data and get it as a pandas DataFrame directly.
    """
    query = """
        SELECT created_at, id, user_id, loan_amount
        FROM loan_applications_silver
        WHERE created_at >= '2026-05-20'
        LIMIT 100
    """

    # Pass column names for better control
    columns = ["created_at", "id", "user_id", "loan_amount"]
    df = fetch_data_from_clickhouse(query, as_dataframe=True, columns=columns)

    if df is not None:
        print(f"Fetched {len(df)} rows")
        print(df.head())
        return df


# ==============================================================================
# EXAMPLE 4: Parametrized function (like your cc_tv_fxn)
# ==============================================================================


def cc_tv_fxn(start_date, end_date, is_repeat=0):
    """
    Parametrized loan application query.
    Similar to your original implementation.

    Args:
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        is_repeat: Filter by is_repeat flag (0 or 1)
    """
    query = f"""
        SELECT
            DATE(la.created_at + INTERVAL '330' MINUTE) AS date_x,
            la.created_at + INTERVAL '330' MINUTE as created_at_loan,
            toStartOfHour(la.created_at + INTERVAL 330 MINUTE) AS hour_x,
            la.user_id,
            la.is_repeat,
            la.id AS loan_id,
            m.id AS mer_id,
            m.name AS merchant_name,
            m.is_evoucher_merchant,
            m.channel AS mer_channel,
            la.field_of_study as field_of_study,
            la.order_value,
            la.tenure,
            (la.down_payment + la.processing_fees - la.cashback) AS tdp,
            COALESCE(la.merchant_closing_fees, 0) + COALESCE(la.merchant_fees, 0) + COALESCE(la.subvention_fees, 0) + COALESCE(la.p_and_s_charges, 0) + COALESCE(la.customer_subvention, 0)
            + COALESCE(la.processing_fees, 0) + COALESCE(la.documentation_charges, 0) + COALESCE((la.emi_amount * la.tenure) - la.loan_amount, 0) - COALESCE(la.cashback, 0) AS total_loan_revenue,
            la.application_status,
            la.product_master_id,
            la.emi_amount,
            la.loan_amount,
            (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0)- COALESCE(la.loan_amount,0)) AS interest,
            CASE WHEN (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0) - COALESCE(la.loan_amount,0)) = 0 THEN la.user_id
            ELSE NULL
            END AS zero_interest_user,
            CASE WHEN (COALESCE(la.tenure,0) * COALESCE(la.emi_amount,0) - COALESCE(la.loan_amount,0)) = 0 AND la.processing_fees = 0 THEN la.user_id
            ELSE NULL
            END AS zero_interest_tag_user
        FROM loan_applications_silver la
        LEFT JOIN merchants_silver m ON m.id = la.merchant_id  
        WHERE la.created_at BETWEEN '{start_date}' AND '{end_date}'
            AND la.field_of_study IS NOT NULL
            AND la.udf2 = 'android_customer_app'
            AND m.channel IN ('online_mobile')
            AND la.is_repeat = {is_repeat}
            AND tdp = 19
    """

    columns = [
        "date_x",
        "created_at_loan",
        "hour_x",
        "user_id",
        "is_repeat",
        "loan_id",
        "mer_id",
        "merchant_name",
        "is_evoucher_merchant",
        "mer_channel",
        "field_of_study",
        "order_value",
        "tenure",
        "tdp",
        "total_loan_revenue",
        "application_status",
        "product_master_id",
        "emi_amount",
        "loan_amount",
        "interest",
        "zero_interest_user",
        "zero_interest_tag_user",
    ]

    df = fetch_data_from_clickhouse(query, as_dataframe=True, columns=columns)
    return df


# ==============================================================================
# USAGE
# ==============================================================================

if __name__ == "__main__":
    # Example 1: Direct connector usage
    print("Example 1: Complex loan query with DataFrame")
    print("=" * 60)
    # df = example_loan_applications_query()
    # print(f"Rows: {len(df)}")
    # print(df.info())

    # Example 2: Simple query
    print("\nExample 2: Simple query (JSON)")
    print("=" * 60)
    # example_simple_query()

    # Example 3: With DataFrame
    print("\nExample 3: DataFrame with columns")
    print("=" * 60)
    # df = example_with_dataframe()

    # Example 4: Parametrized function
    print("\nExample 4: Parametrized cc_tv_fxn")
    print("=" * 60)
    df = cc_tv_fxn("2026-05-20", "2026-05-21", is_repeat=0)
    if df is not None:
        print(f"✓ Fetched {len(df)} rows")
        print(f"✓ Columns: {list(df.columns)}")
        print(df.head())
    else:
        print("✗ Failed to fetch data")
