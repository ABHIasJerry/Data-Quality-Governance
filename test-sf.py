##################################################################
"""
Configure .env File
Create a file named .env in your project root directory.

Depending on your login method, configure SNOWFLAKE_AUTHENTICATOR:

Set to snowflake for username/password authentication.

Set to externalbrowser for SSO (Okta, Azure AD/Entra ID, Ping, etc.).

# Required Settings
SNOWFLAKE_ACCOUNT=orgname-accountname   # Example: xy12345.us-east-1 or orgname-accountname
SNOWFLAKE_USER=your_username

# Authentication Type: 'snowflake' (Password) or 'externalbrowser' (SSO)
SNOWFLAKE_AUTHENTICATOR=externalbrowser

# Required ONLY if SNOWFLAKE_AUTHENTICATOR=snowflake
SNOWFLAKE_PASSWORD=your_password_here

# Optional Context (Leave blank if not needed)
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=MY_DATABASE
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=MY_ROLE

When testing SSO (externalbrowser): A default browser window will automatically launch asking you to log in via your 
Identity Provider (Okta, Azure AD, etc.). Once complete, the browser tab displays "Initiated navigation to your application," 
and the terminal will log your successful session context.
"""
#################################################################
import os
import sys
import logging
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector import SnowflakeConnection
from snowflake.connector.errors import Error as SnowflakeError

# Set up clean logging output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SnowflakeTest")


def get_connection_config() -> dict:
    """Loads environment variables and validates required fields."""
    load_dotenv()

    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "snowflake").lower()
    password = os.getenv("SNOWFLAKE_PASSWORD")

    if not account or not user:
        logger.error("Missing required environment variables: SNOWFLAKE_ACCOUNT or SNOWFLAKE_USER")
        sys.exit(1)

    # Build connection kwargs
    config = {
        "account": account,
        "user": user,
        "authenticator": authenticator,
    }

    # If using standard password auth, ensure password exists
    if authenticator == "snowflake":
        if not password:
            logger.error("SNOWFLAKE_AUTHENTICATOR is set to 'snowflake', but SNOWFLAKE_PASSWORD is missing in .env")
            sys.exit(1)
        config["password"] = password
    elif authenticator == "externalbrowser":
        logger.info("SSO mode active ('externalbrowser'). A browser tab will open for authentication.")

    # Optional parameters
    optional_keys = {
        "warehouse": "SNOWFLAKE_WAREHOUSE",
        "database": "SNOWFLAKE_DATABASE",
        "schema": "SNOWFLAKE_SCHEMA",
        "role": "SNOWFLAKE_ROLE",
    }

    for config_key, env_var in optional_keys.items():
        val = os.getenv(env_var)
        if val:
            config[config_key] = val

    return config


def test_snowflake_connection() -> bool:
    """Attempts to connect to Snowflake and run a verification query."""
    config = get_connection_config()
    conn: SnowflakeConnection = None

    try:
        logger.info(f"Connecting to Snowflake account: '{config['account']}' as user: '{config['user']}'...")
        conn = snowflake.connector.connect(**config)

        logger.info("Connection established successfully!")

        # Execute test query
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    CURRENT_USER(), 
                    CURRENT_ROLE(), 
                    CURRENT_WAREHOUSE(), 
                    CURRENT_DATABASE(), 
                    CURRENT_VERSION()
            """)
            result = cur.fetchone()

            logger.info("--- Session Context Verification ---")
            logger.info(f"User          : {result[0]}")
            logger.info(f"Role          : {result[1]}")
            logger.info(f"Warehouse     : {result[2]}")
            logger.info(f"Database      : {result[3]}")
            logger.info(f"Snowflake Ver : {result[4]}")
            logger.info("-----------------------------------")

        return True

    except SnowflakeError as e:
        logger.error(f"Snowflake Connection Failed! Error Code [{e.errno}]: {e.msg}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return False
    finally:
        if conn and not conn.is_closed():
            conn.close()
            logger.info("Snowflake connection closed.")


if __name__ == "__main__":
    success = test_snowflake_connection()
    if not success:
        sys.exit(1)
