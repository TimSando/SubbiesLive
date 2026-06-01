# Import central registry first
import src.core.models  # noqa: F401
import time

from src.notifications.service import dispatch_push_notifications

def main():
    print("Broadcasting test push notification to all registered devices...")
    dispatch_push_notifications(
        title="🏉 Global Notification Test",
        body="This is a direct test of the Web Push system. It bypassed all topic filters!",
        url="/notifications"
    )
    print("Waiting 3 seconds for background threads to complete...")
    time.sleep(3)
    print("✅ Broadcast trigger completed. If your browser subscription is active, you should receive a notification shortly.")

if __name__ == "__main__":
    main()
