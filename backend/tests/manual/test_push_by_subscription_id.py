# Import central model registry first to register all models with SQLAlchemy
import src.core.models  # noqa: F401

import json
import sys
from sqlalchemy import text
from pywebpush import webpush, WebPushException
from src.core.config import get_settings
from src.ingestion.engine import get_sync_engine


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python test_push_by_subscription_id.py <subscription_id> [message_body]"
        )
        sys.exit(1)

    try:
        sub_id = int(sys.argv[1])
    except ValueError:
        print("Error: subscription_id must be an integer.")
        sys.exit(1)

    body_text = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "Testing connection directly from pywebpush to your browser endpoint."
    )

    settings = get_settings()
    engine = get_sync_engine()

    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, endpoint, p256dh, auth FROM pwa_subscriptions WHERE id = :sub_id"
            ),
            {"sub_id": sub_id},
        )
        row = result.mappings().first()

    if not row:
        print(f"Error: No subscription found with ID {sub_id} in database.")
        sys.exit(1)

    sub = dict(row)
    print(f"Found subscription ID {sub['id']} with endpoint: {sub['endpoint'][:60]}...")

    payload = {
        "title": "🏉 Direct Push Test",
        "body": body_text,
        "url": "/notifications",
    }

    print("\nSending push notification...")
    try:
        res = webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_mailto},
        )
        print(f"  Success!")
        print(f"  Response Status: {res.status_code}")
        print(f"  Response Content: {res.content}")
    except WebPushException as ex:
        print(
            f"  ❌ WebPushException status={getattr(ex.response, 'status_code', 'N/A')}: {ex}"
        )
    except Exception as e:
        print(f"  ❌ General Exception: {e}")


if __name__ == "__main__":
    main()
