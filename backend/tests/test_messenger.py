import requests

from app.services import messenger


class FakeResponse:
    status_code = 200


def test_send_text_posts_the_message_payload(monkeypatch):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append({"url": url, "params": params, "json": json})
        return FakeResponse()

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    result = messenger.send_text("token-abc", "psid-1", "Chào em")

    assert result is True
    assert calls[0]["url"] == messenger.GRAPH_URL
    assert calls[0]["params"] == {"access_token": "token-abc"}
    assert calls[0]["json"] == {
        "recipient": {"id": "psid-1"},
        "message": {"text": "Chào em"},
    }


def test_send_typing_posts_the_sender_action(monkeypatch):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    messenger.send_typing("token-abc", "psid-1")

    assert calls[0] == {"recipient": {"id": "psid-1"}, "sender_action": "typing_on"}


def test_network_failure_returns_false_instead_of_raising(monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        raise requests.RequestException("boom")

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    assert messenger.send_text("token-abc", "psid-1", "Chào em") is False


def test_network_failure_does_not_log_the_access_token(monkeypatch, capsys):
    def fake_post(url, params=None, json=None, timeout=None):
        raise requests.ConnectionError(
            "Max retries exceeded with url: /v19.0/me/messages?access_token=EAAG-secret"
        )

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    messenger.send_text("EAAG-secret", "psid-1", "Chào em")

    captured = capsys.readouterr()
    assert "EAAG-secret" not in captured.out + captured.err


def test_missing_access_token_short_circuits(monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        raise AssertionError("must not call the Graph API without a token")

    monkeypatch.setattr(messenger.requests, "post", fake_post)

    assert messenger.send_text("", "psid-1", "Chào em") is False
