import asyncio
import logging
import random
import threading
import sys
from expert_option_improved.client import ExpertOptionClient
from expert_option_improved.constants import Actions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ExpertBot")

# Your Token
TOKEN = "45ea718ccac89f6f21e933139ebe6050" 

class BotState:
    def __init__(self):
        self.is_running = False
        self.is_demo = True
        self.should_exit = False
        self.asset_id = 240 # EURUSD
        self.amount = 50
        self.duration = 10 # 10 seconds trade

state = BotState()

def input_listener():
    """Reads user input from console in a separate thread."""
    print("\n--- CONTROLS ---")
    print("Type 'start' to enable auto-trading")
    print("Type 'stop' to pause auto-trading")
    print("Type 'demo' to switch to DEMO account")
    print("Type 'real' to switch to REAL account")
    print("Type 'exit' to close the bot")
    print("----------------\n")
    
    while not state.should_exit:
        try:
            cmd = input().strip().lower()
            if cmd == "start":
                state.is_running = True
                logger.info(">>> AUTO-TRADING STARTED <<<")
            elif cmd == "stop":
                state.is_running = False
                logger.info(">>> AUTO-TRADING STOPPED <<<")
            elif cmd == "demo":
                state.is_demo = True
                logger.info(">>> SWITCHED TO DEMO MODE. PLEASE RESTART CONNECTION IF NEEDED <<<")
            elif cmd == "real":
                state.is_demo = False
                logger.warning(">>> SWITCHED TO REAL MODE. USE CAUTION! <<<")
            elif cmd == "exit":
                state.is_running = False
                state.should_exit = True
                logger.info("Exiting...")
                break
        except EOFError:
            break

from expert_option_improved.ai.predictor import AIPredictor

# Initialize AI
ai = AIPredictor()

# Global candle storage
candles_data = []

def on_candle(data):
    """Callback for real-time candle updates."""
def on_candle(data):
    """Callback for real-time candle updates."""
    try:
        msg = data.get('message', {})
        new_candles = []
        
        if 'candles' in msg:
            new_candles = msg['candles']
        elif 'close' in msg or 'c' in msg: 
             new_candles = [msg]
             
        for c in new_candles:
             # Normalize keys (handle standard and abbreviated)
             clean_c = c.copy()
             
             # Map abbreviated to full
             if 'c' in c: clean_c['close'] = c['c']
             if 'o' in c: clean_c['open'] = c['o']
             if 'h' in c: clean_c['high'] = c['h']
             if 'l' in c: clean_c['low'] = c['l']
             if 'v' in c: clean_c['volume'] = c['v']
             
             # Map high/low to max/min if needed by AI
             if 'high' in clean_c: clean_c['max'] = clean_c['high']
             if 'low' in clean_c: clean_c['min'] = clean_c['low']
             
             # Ensure floats
             for k in ['close', 'open', 'high', 'low', 'max', 'min']:
                 if k in clean_c:
                     clean_c[k] = float(clean_c[k])

             if 'close' not in clean_c:
                 # logger.warning(f"Ignoring bad candle: {clean_c.keys()}")
                 continue
                 
             candles_data.append(clean_c)
             if len(candles_data) > 60: 
                 candles_data.pop(0)

    except Exception as e:
        logger.error(f"Candle error: {e}")

async def analyze_market(client, asset_id):
    """
    Analyzes using Advanced AI (Neural + LLM).
    """
    if len(candles_data) < 40:
        logger.info(f"Gathering AI data... ({len(candles_data)}/40 candles)")
        return None

    # Run AI Analysis
    try:
        prediction = ai.analyze(candles_data)
        if prediction:
            signal = prediction.get('signal', 'NEUTRAL').upper()
            conf_str = str(prediction.get('confidence', '0')).replace('%', '')
            try:
                confidence = float(conf_str)
            except:
                confidence = 0
            
            # Reduce threshold to 60% for more activity
            THRESHOLD = 60 
            
            if confidence >= THRESHOLD and signal in ['CALL', 'PUT']:
                logger.info(f"🎉 AI SIGNAL ACCEPTED: {signal} ({confidence}%) - {prediction.get('reason')}")
                return signal.lower() # 'call' or 'put'
            else:
                if signal != "NEUTRAL":
                    logger.info(f"✋ Signal Rejected: {signal} ({confidence}%) - Below Threshold {THRESHOLD}%")
                else:
                    logger.info(f"AI Neutral: {prediction.get('reason')}")
                
    except Exception as e:
        logger.error(f"AI Error: {e}")
        
    return None

async def run_bot():
    # Start input thread
    t = threading.Thread(target=input_listener, daemon=True)
    t.start()
    
    logger.info("Connecting to ExpertOption...")
    
    current_mode = state.is_demo

    async with ExpertOptionClient(token=TOKEN, demo=state.is_demo) as client:
        # Register callback
        client.on_candle_update = on_candle
        
        # Initial profile fetch
        profile = await client.get_profile()
        name = profile.get('message', {}).get('profile', {}).get('name', 'User')
        logger.info(f"Connected as: {name}")
        
        # Subscribe to candles
        # Need history?
        await client.get_candles(state.asset_id, period=60)
        logger.info("Subscribed to market data...")

        while not state.should_exit:
            # Check for mode switch
            if state.is_demo != current_mode:
                logger.info(f"Switching Account Mode to {'DEMO' if state.is_demo else 'REAL'}...")
                await client.set_mode(1 if state.is_demo else 0)
                current_mode = state.is_demo
                await asyncio.sleep(1)

            if state.is_running:
                # 1. Analyze
                logger.info(f"Analyzing market for {state.asset_id}...")
                signal = await analyze_market(client, state.asset_id)
                
                if signal:
                    logger.info(f"STRONG SIGNAL DETECTED: {signal.upper()}")
                    # 2. Trade
                    try:
                        result = await client.buy(
                            amount=state.amount,
                            action_type=signal,
                            assetid=state.asset_id,
                            duration=state.duration
                        )
                        logger.info(f"Trade Sent: {signal.upper()} @ ${state.amount} (10s)")
                    except Exception as e:
                        logger.error(f"Trade Execution Failed: {e}")
                else:
                    logger.info("No strong signal. Waiting...")
                
                # Wait for next trade opportunity
                await asyncio.sleep(state.duration + 2) # Wait for trade to finish + buffer
            else:
                # Idle loop
                await asyncio.sleep(1)

    logger.info("Bot stopped.")

if __name__ == "__main__":
    if TOKEN == "YOUR_TOKEN_HERE":
         print("ERROR: Please update the TOKEN variable in bot.py")
    else:
         try:
            asyncio.run(run_bot())
         except KeyboardInterrupt:
            pass
