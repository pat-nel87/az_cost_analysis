"""Subscription enumeration via Azure Resource Manager."""

import logging

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient

logger = logging.getLogger(__name__)


def list_subscriptions(
    credential: DefaultAzureCredential,
    filter_ids: list[str] | None = None,
) -> list[dict]:
    """Enumerate accessible Azure subscriptions.

    Args:
        credential: Authenticated Azure credential.
        filter_ids: Optional list of subscription IDs to include.
            If None, returns all accessible subscriptions.

    Returns:
        List of dicts with id, display_name, and subscription_id.
    """
    client = SubscriptionClient(credential)
    subscriptions = []

    for sub in client.subscriptions.list():
        entry = {
            "id": sub.id,
            "display_name": sub.display_name,
            "subscription_id": sub.subscription_id,
        }
        if filter_ids is None or sub.subscription_id in filter_ids:
            subscriptions.append(entry)

    logger.info("Discovered %d subscription(s)", len(subscriptions))
    if filter_ids and len(subscriptions) < len(filter_ids):
        found = {s["subscription_id"] for s in subscriptions}
        missing = set(filter_ids) - found
        logger.warning("Subscription(s) not found or not accessible: %s", ", ".join(missing))

    return subscriptions
