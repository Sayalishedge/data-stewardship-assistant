import streamlit as st
from snowflake.snowpark import Session
from typing import Dict, Any, Optional, List


# ================== #
# CONNECTION HELPERS #
# ================== #

@st.cache_resource
def get_snowflake_session(
    account: str = None,
    user: str = None,
    password: str = None,
    warehouse: str = None,
    database: str = None,
    schema: str = None,
    role: str = None,
    use_secrets: bool = True
) -> Session:
    """
    Create a Snowflake session using credentials.

    Args:
        account: Snowflake account (or use secrets)
        user: Username (or use secrets)
        password: Password (or use secrets)
        warehouse: Warehouse name (or use secrets)
        database: Database name (or use secrets)
        schema: Schema name (or use secrets)
        role: Role name (or use secrets)
        use_secrets: If True, use st.secrets for credentials

    Returns:
        Snowflake Session object
    """
    if use_secrets:
        connection_parameters = {
            "account": st.secrets["snowflake"]["account"],
            "user": st.secrets["snowflake"]["user"],
            "password": st.secrets["snowflake"]["password"],
            "warehouse": st.secrets["snowflake"]["warehouse"],
            "database": st.secrets["snowflake"]["database"],
            "schema": st.secrets["snowflake"]["schema"],
            "role": st.secrets["snowflake"]["role"],
        }
    else:
        connection_parameters = {
            "account": account,
            "user": user,
            "password": password,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "role": role,
        }

    return Session.builder.configs(connection_parameters).create()


@st.cache_resource
def get_snowflake_session_from_dict(_config: Dict[str, str]) -> Session:
    """
    Create a Snowflake session from a configuration dictionary.
    Uses @st.cache_resource to prevent re-creating session on every rerun.

    Args:
        _config: Dictionary with connection parameters (underscore prefix for unhashable)

    Returns:
        Snowflake Session object
    """
    return Session.builder.configs(_config).create()


def get_connection_config_from_secrets() -> Dict[str, str]:
    """
    Get connection configuration from Streamlit secrets.

    Returns:
        Dictionary with connection parameters
    """
    return {
        "account": st.secrets["snowflake"]["account"],
        "user": st.secrets["snowflake"]["user"],
        "password": st.secrets["snowflake"]["password"],
        "warehouse": st.secrets["snowflake"]["warehouse"],
        "database": st.secrets["snowflake"]["database"],
        "schema": st.secrets["snowflake"]["schema"],
        "role": st.secrets["snowflake"]["role"],
    }

# ============================================================================
# QUERY HELPERS
# ============================================================================

def execute_sql(
    session: Session,
    query: str,
    return_pandas: bool = False
):
    """
    Execute a SQL query.

    Args:
        session: Snowflake session
        query: SQL query string
        return_pandas: If True, return pandas DataFrame

    Returns:
        Query results (list of rows or DataFrame)
    """
    try:
        if return_pandas:
            return session.sql(query).to_pandas()
        return session.sql(query).collect()
    except Exception as e:
        print(f"SQL execution error: {e}")
        return [] if not return_pandas else None


def get_table_columns(
    session: Session,
    table_name: str,
    database: str = None,
    schema: str = None
) -> List[str]:
    """
    Get column names for a table.

    Args:
        session: Snowflake session
        table_name: Table name
        database: Optional database name
        schema: Optional schema name

    Returns:
        List of column names
    """
    try:
        if database and schema:
            full_table = f'"{database}"."{schema}"."{table_name}"'
        else:
            full_table = f'"{table_name}"'

        query = f"DESCRIBE TABLE {full_table}"
        result = session.sql(query).collect()
        return [row['name'] for row in result]
    except Exception as e:
        print(f"Error getting table columns: {e}")
        return []


def table_exists(
    session: Session,
    table_name: str,
    database: str = None,
    schema: str = None
) -> bool:
    """
    Check if a table exists.

    Args:
        session: Snowflake session
        table_name: Table name
        database: Optional database name
        schema: Optional schema name

    Returns:
        True if table exists
    """
    try:
        if database and schema:
            query = f"SHOW TABLES LIKE '{table_name}' IN \"{database}\".\"{schema}\""
        else:
            query = f"SHOW TABLES LIKE '{table_name}'"

        result = session.sql(query).collect()
        return len(result) > 0
    except Exception as e:
        print(f"Error checking table existence: {e}")
        return False


# ============================================================================
# TOKEN/AUTH HELPERS
# ============================================================================

def get_session_token(session: Session) -> str:
    """
    Get the authentication token from a session.

    Args:
        session: Snowflake session

    Returns:
        Token string
    """
    return session.connection.rest.token


def build_api_headers(token: str) -> Dict[str, str]:
    """
    Build API headers for Snowflake REST API calls.

    Args:
        token: Authentication token

    Returns:
        Headers dictionary
    """
    return {
        "Authorization": f"Snowflake Token=\"{token}\"",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_cortex_api_url(account: str, endpoint: str = "inference:complete") -> str:
    """
    Build Cortex API URL.

    Args:
        account: Snowflake account identifier
        endpoint: API endpoint (default: inference:complete)

    Returns:
        Full API URL
    """
    account_url = account.replace("_", "-").replace(".", "-")
    return f"https://{account_url}.snowflakecomputing.com/api/v2/cortex/{endpoint}"
