import asyncio
import logging
import os
from expert_option_improved.client import ExpertOptionClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# CHANGE THIS TO YOUR REAL TOKEN
TOKEN = "45ea718ccac89f6f21e933139ebe6050" 

async def main():
    if TOKEN == "YOUR_TOKEN_HERE":
        print("Please edit this file and set your real Expert Option TOKEN.")
        return

    print("Connecting to Expert Option...")
    async with ExpertOptionClient(token=TOKEN, demo=True) as client:
        # 1. Connection established in __aenter__
        
        # 2. Get Profile
        print("\n--- Fetching Profile ---")
        try:
            profile_response = await client.get_profile()
            print(f"Profile Response: {profile_response}")
        except Exception as e:
            print(f"Failed to fetch profile: {e}")

        # 3. Get Candles
        print("\n--- Fetching Candles (EURUSD) ---")
        try:
            candles_response = await client.get_candles(asset_id=240, period=60)
            print(f"Candles Response: {candles_response}")
        except Exception as e:
            print(f"Failed to fetch candles: {e}")

        # 4. Simulated Trade (Uncomment to test if you have demo balance)
        # print("\n--- Placing Demo Trade ---")
        # try:
        #     trade_response = await client.buy(amount=10, action_type="call", assetid=240, duration=60)
        #     print(f"Trade Response: {trade_response}")
        # except Exception as e:
        #     print(f"Trade failed: {e}")

        # Keep alive for a bit to see background pings
        print("\n--- Waiting 10 seconds ---")
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
