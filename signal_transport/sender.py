import requests
import json
import logging

logger = logging.getLogger(__name__)


class SignalSender:
    """
    Sends messages to signal groups via signal-cli http daemon. Requires 
    signal-cli daemon to be running with http api enabled.
    """

    def __init__(self, daemon_url: str, number: str, group_id: str):
        self.daemon_url = daemon_url
        self.number = number
        self.group_id = group_id

    # send a message to the configured signal group
    def send(self, message: str) -> bool:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "send",
            "params": {
                "account": self.number,
                "message": message,
                "groupId": self.group_id
            }
        }
        try:
            response = requests.post(
                f"{self.daemon_url}/api/v1/rpc",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return True
                else:
                    logger.error("Signal send failed: %s", result.get("error", "Unknown error"))
                    return False
            else:
                logger.error("Signal send failed: HTTP %d - %s", response.status_code, response.text)
                return False
        except requests.RequestException as exc:
            logger.error("Signal send failed: %s", exc)
            return False

