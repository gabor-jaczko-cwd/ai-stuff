#!/usr/bin/env python3
"""Send a Slack DM via a dedicated bot token.

Usage: send_slack_message.py <slack_user_id>
Reads the bot token from ./slack-bot-token and the message text from stdin.
Prints the final Slack API response as JSON and exits non-zero on failure.
"""
import json
import sys
import urllib.request


def slack_post(method, token, payload):
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    slack_user_id = sys.argv[1]
    text = sys.stdin.read()
    with open("slack-bot-token") as f:
        token = f.read().strip()

    opened = slack_post("conversations.open", token, {"users": slack_user_id})
    if not opened.get("ok"):
        print(json.dumps(opened))
        sys.exit(1)
    channel = opened["channel"]["id"]

    sent = slack_post("chat.postMessage", token, {"channel": channel, "text": text})
    print(json.dumps(sent))
    if not sent.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
