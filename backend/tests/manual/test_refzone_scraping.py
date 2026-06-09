import asyncio
import os
import src.core.models  # noqa: F401
import httpx
from fastapi import HTTPException
from src.refzone.router import (
    fetch_fresh_rx_basic_token,
    rx_login,
    LoginRequest,
)
import src.refzone.router as rx_router

async def test_scraping():
    print("--- Testing Token Scraping ---")
    async with httpx.AsyncClient() as client:
        try:
            token = await fetch_fresh_rx_basic_token(client)
            print(f"✅ Successfully scraped token! Length: {len(token)}")
            assert len(token) > 20, "Scraped token seems too short"
            return token
        except Exception as e:
            print(f"❌ Failed to scrape token: {e}")
            raise e

async def test_retry_flow():
    print("\n--- Testing Login Retry Flow with Poisoned Token ---")
    # Poison the token cache
    rx_router._cached_basic_token = "invalid_token_to_force_failure"
    print(f"Poisoned token cache. Current: {rx_router._cached_basic_token}")

    email = os.environ.get("RX_TEST_EMAIL")
    password = os.environ.get("RX_TEST_PASSWORD")

    if email and password:
        print("Real credentials found in environment. Testing full login success...")
        body = LoginRequest(email=email, password=password)
        try:
            # Call rx_login. This should:
            # 1. Attempt login with "invalid_token_to_force_failure" (fails)
            # 2. Trigger warning and token refresh
            # 3. Fetch fresh token and update cache
            # 4. Retry login with fresh token and real credentials (succeeds!)
            response = await rx_login(body)
            print("✅ Login succeeded after token refresh!")
            assert isinstance(response, dict), "Expected dictionary response from login"
            assert "accessToken" in response or "id" in response or "userId" in response, "Response did not contain user authentication details"
            print("✅ Verified login response payload is correct.")
        except Exception as e:
            print(f"❌ Login with real credentials failed: {e}")
            raise e
    else:
        print("No test credentials in environment. Falling back to dummy credentials check...")
        body = LoginRequest(email="test_user@example.com", password="dummy_password")
        try:
            await rx_login(body)
            print("❌ Expected login to fail with dummy credentials but it succeeded!")
            raise AssertionError("Login succeeded with dummy credentials")
        except HTTPException as e:
            print(f"✅ Caught expected HTTPException: status_code={e.status_code}")
            # Correct Basic token + incorrect user credentials returns 401 Unauthorized
            assert e.status_code == 401, f"Expected status 401 for bad credentials, got {e.status_code}"
            print("✅ Verified correct HTTP 401 was returned.")
        except Exception as e:
            print(f"❌ Caught unexpected exception: {e}")
            raise e

    # Verify that the token cache was successfully updated to something other than the poisoned value
    updated_token = rx_router._cached_basic_token
    print(f"Updated token cache: {updated_token}")
    if updated_token == "invalid_token_to_force_failure":
        print("❌ Token cache was NOT updated!")
        raise AssertionError("Token cache was not updated")
    else:
        print("✅ Token cache was successfully restored/updated to a valid token!")

async def main():
    try:
        await test_scraping()
        await test_retry_flow()
    except Exception as e:
        print(f"Test suite failed: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
