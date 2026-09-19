import requests

GRAPH_URL = "https://graph.facebook.com/v19.0/me/messages"
REQUEST_TIMEOUT_SECONDS = 10


def _post(access_token: str, payload: dict) -> bool:
    """POST to the Send API. Returns True on success, never raises."""
    if not access_token:
        print("Messenger API skipped: page has no access token")
        return False
    try:
        response = requests.post(
            GRAPH_URL,
            params={"access_token": access_token},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # The exception text embeds the request URL, which carries the access token.
        print(f"Messenger API error: {type(exc).__name__}")
        return False
    if response.status_code >= 400:
        print(f"Messenger API returned {response.status_code}")
        return False
    return True


def send_typing(access_token: str, psid: str) -> bool:
    return _post(access_token, {"recipient": {"id": psid}, "sender_action": "typing_on"})


def send_text(access_token: str, psid: str, text: str) -> bool:
    return _post(
        access_token, {"recipient": {"id": psid}, "message": {"text": text}}
    )
