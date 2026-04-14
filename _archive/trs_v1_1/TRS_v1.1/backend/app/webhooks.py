"""
TRS-306: Webhook notifications for proposal events.

Sends notifications to Slack, Discord, or custom webhooks when:
- New proposal submitted
- Proposal approved/rejected
- Release created

Configuration via environment variables:
    TRS_WEBHOOK_URL: Webhook endpoint
    TRS_WEBHOOK_TYPE: slack | discord | generic (default: generic)
    TRS_NOTIFY_ON: comma-separated list of events (default: all)

Usage:
    from backend.app.webhooks import notify_proposal_created, notify_release
    
    await notify_proposal_created(proposal)
    await notify_release(version, changes)
"""

from __future__ import annotations
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Optional

import httpx

# Configuration
WEBHOOK_URL = os.getenv("TRS_WEBHOOK_URL", "")
WEBHOOK_TYPE = os.getenv("TRS_WEBHOOK_TYPE", "generic")
NOTIFY_ON = set(os.getenv("TRS_NOTIFY_ON", "proposal_created,proposal_reviewed,release_created").split(","))


async def send_webhook(payload: dict) -> bool:
    """Send a webhook notification. Returns True if successful."""
    if not WEBHOOK_URL:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(WEBHOOK_URL, json=payload)
            return response.status_code < 400
    except Exception as e:
        print(f"Webhook failed: {e}")
        return False


def format_slack_message(title: str, fields: list[tuple[str, str]], color: str = "#36a64f") -> dict:
    """Format a Slack webhook message."""
    return {
        "attachments": [
            {
                "color": color,
                "title": title,
                "fields": [
                    {"title": k, "value": v, "short": True}
                    for k, v in fields
                ],
                "footer": "TRS Notification",
                "ts": int(datetime.now().timestamp()),
            }
        ]
    }


def format_discord_message(title: str, fields: list[tuple[str, str]], color: int = 0x36a64f) -> dict:
    """Format a Discord webhook message."""
    return {
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": [
                    {"name": k, "value": v, "inline": True}
                    for k, v in fields
                ],
                "timestamp": datetime.now().isoformat(),
            }
        ]
    }


def format_generic_message(event: str, data: dict) -> dict:
    """Format a generic webhook message."""
    return {
        "event": event,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }


def format_message(event: str, title: str, fields: list[tuple[str, str]], color: str = "green") -> dict:
    """Format a message based on webhook type."""
    color_map = {
        "green": ("#36a64f", 0x36a64f),
        "yellow": ("#ffcc00", 0xffcc00),
        "red": ("#ff0000", 0xff0000),
        "blue": ("#0066ff", 0x0066ff),
    }
    
    hex_color, int_color = color_map.get(color, color_map["green"])
    
    if WEBHOOK_TYPE == "slack":
        return format_slack_message(title, fields, hex_color)
    elif WEBHOOK_TYPE == "discord":
        return format_discord_message(title, fields, int_color)
    else:
        return format_generic_message(event, {"title": title, "fields": dict(fields)})


# ============================================================================
# Notification Functions
# ============================================================================

async def notify_proposal_created(
    proposal_id: int,
    tag_id: str,
    proposal_type: str,
    submitter: str,
    canonical_name: Optional[str] = None,
) -> bool:
    """Notify when a new proposal is created."""
    if "proposal_created" not in NOTIFY_ON:
        return False
    
    emoji = {"new_tag": "➕", "modify_tag": "✏️", "deprecate_tag": "🗑️"}.get(proposal_type, "📋")
    
    payload = format_message(
        event="proposal_created",
        title=f"{emoji} New Proposal #{proposal_id}",
        fields=[
            ("Tag ID", tag_id),
            ("Type", proposal_type),
            ("Name", canonical_name or "N/A"),
            ("Submitter", submitter),
        ],
        color="blue",
    )
    
    return await send_webhook(payload)


async def notify_proposal_reviewed(
    proposal_id: int,
    tag_id: str,
    decision: str,
    reviewer: str,
    comment: Optional[str] = None,
) -> bool:
    """Notify when a proposal is reviewed."""
    if "proposal_reviewed" not in NOTIFY_ON:
        return False
    
    emoji_map = {"approve": "✅", "reject": "❌", "request_changes": "📝"}
    color_map = {"approve": "green", "reject": "red", "request_changes": "yellow"}
    
    emoji = emoji_map.get(decision, "❓")
    color = color_map.get(decision, "blue")
    
    fields = [
        ("Proposal", f"#{proposal_id}"),
        ("Tag ID", tag_id),
        ("Decision", decision.replace("_", " ").title()),
        ("Reviewer", reviewer),
    ]
    
    if comment:
        fields.append(("Comment", comment[:100]))
    
    payload = format_message(
        event="proposal_reviewed",
        title=f"{emoji} Proposal #{proposal_id} {decision.replace('_', ' ').title()}",
        fields=fields,
        color=color,
    )
    
    return await send_webhook(payload)


async def notify_release_created(
    version: str,
    released_by: str,
    tags_added: int = 0,
    tags_modified: int = 0,
    tags_removed: int = 0,
    proposals_merged: int = 0,
) -> bool:
    """Notify when a release is created."""
    if "release_created" not in NOTIFY_ON:
        return False
    
    changes = f"+{tags_added} / ~{tags_modified} / -{tags_removed}"
    
    payload = format_message(
        event="release_created",
        title=f"🚀 Release {version}",
        fields=[
            ("Version", version),
            ("Released By", released_by),
            ("Changes", changes),
            ("Proposals Merged", str(proposals_merged)),
        ],
        color="green",
    )
    
    return await send_webhook(payload)


# ============================================================================
# Sync Wrappers
# ============================================================================

def notify_proposal_created_sync(*args, **kwargs) -> bool:
    """Sync wrapper for notify_proposal_created."""
    try:
        return asyncio.get_event_loop().run_until_complete(
            notify_proposal_created(*args, **kwargs)
        )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(notify_proposal_created(*args, **kwargs))


def notify_proposal_reviewed_sync(*args, **kwargs) -> bool:
    """Sync wrapper for notify_proposal_reviewed."""
    try:
        return asyncio.get_event_loop().run_until_complete(
            notify_proposal_reviewed(*args, **kwargs)
        )
    except RuntimeError:
        return asyncio.run(notify_proposal_reviewed(*args, **kwargs))


def notify_release_created_sync(*args, **kwargs) -> bool:
    """Sync wrapper for notify_release_created."""
    try:
        return asyncio.get_event_loop().run_until_complete(
            notify_release_created(*args, **kwargs)
        )
    except RuntimeError:
        return asyncio.run(notify_release_created(*args, **kwargs))
