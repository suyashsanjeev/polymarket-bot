import argparse
import asyncio
import logging
import random
import sys
import time
import yaml
from pathlib import Path

from polymarket.api import (
    fetch_all_markets,
    extract_markets,
    backoff_delay,
)
from signal_transport.sender import SignalSender
from storage.file_store import FileHistory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# check if a market title contains any of the specified keywords
def is_relevant(title_lower: str, keywords):
    return any(k in title_lower for k in keywords)

# split message lines into chunks that fit within signals character limit
def chunk_message(lines, char_limit):
    out, chunk = [], ""
    for line in lines:
        if len(chunk) + len(line) > char_limit:
            out.append(chunk)
            chunk = ""
        chunk += line
    if chunk:
        out.append(chunk)
    return out


class MarketMonitor:
    """Monitors polymarket for new markets matching specified keywords"""

    SIGNAL_CHAR_LIMIT = 2000

    def __init__(self, sender, history, keywords, interval):
        self.sender = sender
        self.history = history
        self.keywords = keywords
        self.interval = interval

    # send a summary of all current markets matching the keywords
    def send_all_relevant_markets(self):
        print("Fetching all markets...")
        api_data = asyncio.run(fetch_all_markets())
        markets = extract_markets(api_data)
        relevant = [(t, s) for t, s in markets if is_relevant(t, self.keywords)]

        if not relevant:
            self.sender.send("No relevant markets found.")
            print("No relevant markets found.")
            return

        lines = ["🔍 All related markets on Polymarket:\n\n"]
        for i, (title, slug) in enumerate(relevant, 1):
            lines.append(f"{i}. {title}\nhttps://polymarket.com/event/{slug}\n\n")

        print(f"Sending summary of {len(relevant)} relevant markets...")
        for chunk in chunk_message(lines, self.SIGNAL_CHAR_LIMIT):
            self.sender.send(chunk)
            time.sleep(1)

    # continuously monitor for new markets and send alerts when found
    def run_forever(self):
        attempt = 0
        print(f"Starting continuous monitoring (checking every {self.interval}s)...")

        while True:
            try:
                api_data = asyncio.run(fetch_all_markets())
                markets = extract_markets(api_data)

                new_found = False
                for title, slug in markets:
                    if slug in self.history or not is_relevant(title, self.keywords):
                        continue
                    new_found = True
                    self.history.add(slug)
                    print(f"🚨 New market found: {title}")
                    self.sender.send(
                        f"🚨 New Market!\n\n{title}\n\nhttps://polymarket.com/event/{slug}"
                    )
                if not new_found:
                    print(".", end="", flush=True)

                attempt = 0
                sleep_for = self.interval * random.uniform(0.9, 1.1)  # jitter
            except Exception as exc:
                logger.error(f"Error in monitor loop: {exc}")
                sleep_for = backoff_delay(attempt=attempt)
                attempt += 1

            time.sleep(sleep_for)

# handles command line arguments and starts the appropriate mode
def main():
    parser = argparse.ArgumentParser(description="Polymarket bot for monitoring and alerting on new markets")
    parser.add_argument("--send-summary", action="store_true", help="Send summary of all current relevant markets")
    parser.add_argument("--monitor", action="store_true", help="Run continuous monitoring for new markets")
    parser.add_argument("--check-once", action="store_true", help="Check once for new markets and exit")
    parser.add_argument("--config", default="config.yaml", help="Path to config file (default: config.yaml)")
    args = parser.parse_args()

    # load config
    cfg = yaml.safe_load(Path(args.config).read_text())

    sender = SignalSender(
        cfg["signal"]["daemon_url"], cfg["signal"]["number"], cfg["signal"]["group_id"]
    )
    history = FileHistory(cfg["history_file"])
    keywords = [k.lower() for k in cfg["keywords"]]
    monitor = MarketMonitor(sender, history, keywords, cfg["check_interval"])

    # execute the requested mode
    if args.send_summary:
        monitor.send_all_relevant_markets()
    elif args.monitor:
        monitor.run_forever()
    elif args.check_once:
        print("Checking once for new markets...")
        api_data = asyncio.run(fetch_all_markets())
        markets = extract_markets(api_data)

        new_found = False
        for title, slug in markets:
            if slug in history or not is_relevant(title, keywords):
                continue
            new_found = True
            history.add(slug)
            print(f"🚨 New market found: {title}")
            sender.send(
                f"🚨 New Market!\n\n{title}\n\nhttps://polymarket.com/event/{slug}"
            )

        if not new_found:
            print("No new related markets found.")
        else:
            print("New markets found and alerts sent!")
    else:
        parser.error("Specify --send-summary, --monitor, or --check-once")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

