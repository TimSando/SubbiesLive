# Import central model registry first to register all models with SQLAlchemy
import src.core.models  # noqa: F401

import json
from sqlalchemy import text
from pywebpush import webpush, WebPushException
from src.core.config import get_settings
from src.ingestion.engine import get_sync_engine

def main():
    settings = get_settings()
    engine = get_sync_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT endpoint, p256dh, auth FROM pwa_subscriptions"))
        subscriptions = [dict(row) for row in result.mappings()]
        
    print(f"Loaded {len(subscriptions)} registered push endpoints from database.")
    
    payload = {
        "title": "🏉 Direct Push Test",
        "body": "Testing connection directly from pywebpush to your browser endpoint.",
        "url": "/notifications"
    }
    
    for i, sub in enumerate(subscriptions):
        print(f"\n[{i+1}/{len(subscriptions)}] Sending to endpoint: {sub['endpoint'][:50]}...")
        try:
            res = webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {
                        "p256dh": sub["p256dh"],
                        "auth": sub["auth"]
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={
                    "sub": settings.vapid_mailto
                }
            )
            print(f"  Response Status: {res.status_code}")
            print(f"  Response Content: {res.content}")
        except WebPushException as ex:
            print(f"  ❌ WebPushException status={getattr(ex.response, 'status_code', 'N/A')}: {ex}")
        except Exception as e:
            print(f"  ❌ General Exception: {e}")

if __name__ == "__main__":
    main()
