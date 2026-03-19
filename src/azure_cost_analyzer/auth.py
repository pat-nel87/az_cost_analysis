"""Authentication wrapper for Azure SDK."""

import logging
import sys

from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

logger = logging.getLogger(__name__)


def get_credential() -> DefaultAzureCredential:
    """Return an authenticated DefaultAzureCredential.

    Exits with a clear message if authentication fails.
    """
    try:
        credential = DefaultAzureCredential()
        # Force a token fetch to validate credentials early
        credential.get_token("https://management.azure.com/.default")
        logger.debug("Azure authentication successful")
        return credential
    except ClientAuthenticationError as e:
        print(
            "Authentication failed. Please authenticate using one of:\n"
            "  1. Run 'az login' (Azure CLI)\n"
            "  2. Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID env vars\n"
            "  3. Use managed identity (if running in Azure)\n"
            f"\nError: {e.message}",
            file=sys.stderr,
        )
        sys.exit(1)
