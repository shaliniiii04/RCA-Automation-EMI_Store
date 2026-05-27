"""
ClickHouse SQL Data Fetching Tool

This tool fetches data from ClickHouse database using SQL queries.
It connects to ClickHouse using credentials from .env file.
Supports pandas DataFrames for easy data manipulation.
"""

import os
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, date
from dotenv import load_dotenv
from clickhouse_driver import Client

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

load_dotenv()


class ClickHouseConnector:
    """
    Manages ClickHouse database connections and queries.
    """

    def __init__(self):
        """Initialize ClickHouse connection from .env credentials"""
        self.host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = int(os.getenv("PORT", "9000"))
        self.user = os.getenv("USER", "default")
        self.password = os.getenv("PASSWORD", "")
        self.database = os.getenv("DATABASE", "default")
        self.client = None

    def connect(self) -> bool:
        """
        Establish connection to ClickHouse.
        Returns True if successful, False otherwise.
        """
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                settings={"use_numpy": False},
            )
            # Test connection
            self.client.execute("SELECT 1")
            print(
                f"✓ Connected to ClickHouse at {self.host}:{self.port}/{self.database}"
            )
            return True
        except Exception as e:
            print(f"✗ Failed to connect to ClickHouse: {str(e)}")
            return False

    def disconnect(self):
        """Close ClickHouse connection"""
        if self.client:
            self.client.disconnect()

    def execute_query(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query and return results as list of dicts.

        Args:
            query: SQL query to execute

        Returns:
            List of dictionaries (rows) or None if query fails
        """
        if not self.client:
            if not self.connect():
                return None

        try:
            # Get column names first
            result_with_names = self.client.execute(query, with_column_types=True)

            # Extract column names and data
            if not result_with_names:
                return []

            # Format as list of dictionaries
            columns = [col[0] for col in self.client.execute(query + " FORMAT JSON")]
            if isinstance(result_with_names, list) and len(result_with_names) > 0:
                # Execute query with JSON format to get structured data
                json_result = self.client.execute(query + " FORMAT JSONCompact")
                return json_result

            return result_with_names
        except Exception as e:
            print(f"✗ Query execution failed: {str(e)}")
            return None

    def fetch_dataframe(
        self, query: str, columns: Optional[List[str]] = None
    ) -> Optional["pd.DataFrame"]:
        """
        Fetch data as a pandas DataFrame.

        Args:
            query: SQL query to execute
            columns: Optional list of column names. If None, will try to auto-detect.

        Returns:
            pandas DataFrame or None if query fails
        """
        if not HAS_PANDAS:
            print("✗ pandas is not installed. Install with: pip install pandas")
            return None

        if not self.client:
            if not self.connect():
                return None

        try:
            data = self.client.execute(query)

            if not data:
                return pd.DataFrame()

            if columns is None:
                # Try to auto-detect columns from JSON format
                try:
                    query_json = query + " FORMAT JSON"
                    result_json = self.client.execute(query_json)
                    if isinstance(result_json, str):
                        result_dict = json.loads(result_json)
                        columns = [col["name"] for col in result_dict.get("meta", [])]
                    else:
                        columns = [f"col_{i}" for i in range(len(data[0]))]
                except:
                    columns = [f"col_{i}" for i in range(len(data[0]))]

            return pd.DataFrame(data, columns=columns)
        except Exception as e:
            print(f"✗ DataFrame creation failed: {str(e)}")
            return None


# Global connector instance
_connector: Optional[ClickHouseConnector] = None


def get_connector() -> ClickHouseConnector:
    """Get or create ClickHouse connector instance"""
    global _connector
    if _connector is None:
        _connector = ClickHouseConnector()
    return _connector


def fetch_data_from_clickhouse(
    sql_query: str,
    as_dataframe: bool = False,
    columns: Optional[List[str]] = None,
) -> Union[str, Optional["pd.DataFrame"]]:
    """
    Execute a SQL query against ClickHouse and return results.

    This is the main function exposed as a tool for the orchestrator.

    Args:
        sql_query: SQL query to execute (e.g., "SELECT created_at, id FROM loan_applications_silver WHERE created_at >= '2026-05-20'")
        as_dataframe: If True, return pandas DataFrame. If False, return JSON string.
        columns: Optional list of column names for DataFrame (auto-detected if None)

    Returns:
        JSON string with results or pandas DataFrame, depending on as_dataframe parameter
    """
    from datetime import datetime

    connector = get_connector()

    if not connector.client:
        if not connector.connect():
            if as_dataframe:
                return None
            return json.dumps({"error": "Failed to connect to ClickHouse database"})

    try:
        # Clean up query - remove extra whitespace and escape characters
        query = sql_query.strip()

        # Fix common escape issues from LLM
        # Replace escaped quotes with regular quotes
        query = query.replace('\\"', "'")
        query = query.replace("\\'", "'")

        if not query:
            return {"error": "Empty SQL query provided"}

        # If user wants DataFrame, return it directly
        if as_dataframe:
            return connector.fetch_dataframe(query, columns=columns)

        # Remove FORMAT clause if it exists to avoid duplication
        query = (
            query.replace(" FORMAT JSON", "").replace(" FORMAT JSONEachRow", "").strip()
        )

        # Execute query WITHOUT FORMAT (driver returns raw data)
        result = connector.client.execute(query)

        if not result:
            return {"data": [], "count": 0}

        # Convert result to JSON-serializable format
        # Handle datetime, date, and other non-JSON-serializable types
        def convert_value(val):
            if val is None:
                return None
            elif isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, date):
                return val.isoformat()
            elif isinstance(val, (list, tuple)):
                return [convert_value(v) for v in val]
            elif isinstance(val, dict):
                return {k: convert_value(v) for k, v in val.items()}
            else:
                return val

        data = []
        for row in result:
            if isinstance(row, tuple):
                data.append([convert_value(v) for v in row])
            else:
                data.append(convert_value(row))

        return {
            "data": data,
            "count": len(data),
        }

    except Exception as e:
        error_msg = str(e)
        if as_dataframe:
            print(f"✗ Query failed: {error_msg}")
            return None
        return {"error": f"Query execution failed: {error_msg}"}


def analyze_cc_users_drop(
    current_date: str,
    previous_month_same_date: str,
    current_month_start_date: str,
    previous_month_start_date: str,
    channel: str = "online_mobile",
    threshold: float = 5.0,
    filter_conditions: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze cc_users drop for online_mobile by comparing current date vs previous month same date.
    If the drop exceeds the threshold, fetch raw last-5-day data for both months.
    """
    connector = get_connector()
    if not connector.client:
        if not connector.connect():
            return {"error": "Failed to connect to ClickHouse database"}

    where_filters = f"m.channel = '{channel}'"
    if filter_conditions:
        where_filters += f" AND {filter_conditions}"

    comparison_query = f"""
SELECT
  toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE {where_filters}
  AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) IN ('{current_date}', '{previous_month_same_date}')
GROUP BY date_x
ORDER BY date_x
"""

    comparison_result = fetch_data_from_clickhouse(comparison_query)
    if isinstance(comparison_result, dict) and comparison_result.get("error"):
        return {"error": comparison_result["error"]}

    date_counts = {}
    for row in comparison_result.get("data", []):
        if isinstance(row, list) and len(row) == 2:
            date_counts[str(row[0])] = int(row[1])

    current_count = date_counts.get(current_date)
    previous_count = date_counts.get(previous_month_same_date)
    if current_count is None or previous_count is None:
        return {
            "error": "Failed to compute comparison. Both current_date and previous_month_same_date must return results.",
            "comparison_result": comparison_result,
        }

    relative_diff = 0.0
    if previous_count > 0:
        relative_diff = round(
            (previous_count - current_count) / previous_count * 100, 2
        )

    output = {
        "current_date": current_date,
        "previous_month_same_date": previous_month_same_date,
        "current_cc_users": current_count,
        "previous_cc_users": previous_count,
        "relative_diff_pct": relative_diff,
        "threshold_pct": threshold,
        "trigger_investigation": relative_diff > threshold,
        "comparison_query": comparison_query.strip(),
    }

    if output["trigger_investigation"]:
        raw_query = f"""
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
WHERE {where_filters}
  AND ((toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}'))
GROUP BY date_x, la.tenure, la.ov_bucket, la.is_repeat, la.merchant_id, m.name, m.sub_channel
ORDER BY date_x DESC, cc_users DESC
"""
        raw_result = fetch_data_from_clickhouse(raw_query)
        output["investigation_query"] = raw_query.strip()
        output["raw_last_5_days"] = raw_result

        # Add segment summaries for quick inspection
        segment_queries = {
            "tenure_summary": f"""
SELECT
  la.tenure,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE {where_filters}
  AND ((toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}'))
GROUP BY la.tenure
ORDER BY cc_users DESC
""",
            "ov_bucket_summary": f"""
SELECT
  la.ov_bucket,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE {where_filters}
  AND ((toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}'))
GROUP BY la.ov_bucket
ORDER BY cc_users DESC
""",
            "is_repeat_summary": f"""
SELECT
  la.is_repeat,
  countDistinct(la.user_id) AS cc_users
FROM snapmint_analytics.loan_applications_silver AS la
LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id
WHERE {where_filters}
  AND ((toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{current_month_start_date}' AND '{current_date}')
    OR (toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) BETWEEN '{previous_month_start_date}' AND '{previous_month_same_date}'))
GROUP BY la.is_repeat
ORDER BY cc_users DESC
""",
        }

        segment_results = {}
        for name, q in segment_queries.items():
            segment_results[name] = fetch_data_from_clickhouse(q)
        output["segment_summaries"] = segment_results

    return output


# Tool schema for the orchestrator
sql_generator_tool_schema = {
    "name": "fetch_data_from_clickhouse",
    "description": "Fetch data from ClickHouse database using SQL queries. Returns JSON formatted results with data rows and count.",
    "parameters": {
        "type": "object",
        "properties": {
            "sql_query": {
                "type": "string",
                "description": "Complete SQL SELECT query. IMPORTANT: Use SINGLE QUOTES for all string literals in SQL (e.g., WHERE channel = 'online_mobile', NOT channel = \"online_mobile\"). Only SELECT queries. Use actual table names: snapmint_analytics.loan_applications_silver, merchants_silver, gateway_responses_silver, refunds_silver. Do NOT use invented tables (daily_cc_users, cc_users_history, etc). Example query: SELECT toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) AS date_x, countDistinct(la.user_id) AS cc_users FROM snapmint_analytics.loan_applications_silver AS la LEFT JOIN merchants_silver AS m ON la.merchant_id = m.id WHERE m.channel = 'online_mobile' AND toDate(la.created_at + INTERVAL 5 HOUR + INTERVAL 30 MINUTE) = '2026-05-14' GROUP BY date_x",
            }
        },
        "required": ["sql_query"],
    },
}

analyze_cc_users_drop_tool_schema = {
    "name": "analyze_cc_users_drop",
    "description": "Analyze cc_users drop for online_mobile by comparing the target date to the same date last month and triggering a 5-day investigation if the drop is greater than the configured threshold.",
    "parameters": {
        "type": "object",
        "properties": {
            "current_date": {
                "type": "string",
                "description": "Target date to analyze in YYYY-MM-DD format.",
            },
            "previous_month_same_date": {
                "type": "string",
                "description": "Same calendar weekday in the prior month, in YYYY-MM-DD format.",
            },
            "current_month_start_date": {
                "type": "string",
                "description": "Start date for the current 5-day investigation window in YYYY-MM-DD format.",
            },
            "previous_month_start_date": {
                "type": "string",
                "description": "Start date for the previous month 5-day investigation window in YYYY-MM-DD format.",
            },
            "channel": {
                "type": "string",
                "description": "Merchant channel to analyze, e.g., 'online_mobile'.",
                "default": "online_mobile",
            },
            "threshold": {
                "type": "number",
                "description": "Relative drop percentage threshold that triggers investigation.",
                "default": 5.0,
            },
            "filter_conditions": {
                "type": "string",
                "description": "Optional additional SQL filters to apply in the WHERE clause.",
            },
        },
        "required": [
            "current_date",
            "previous_month_same_date",
            "current_month_start_date",
            "previous_month_start_date",
        ],
    },
}
