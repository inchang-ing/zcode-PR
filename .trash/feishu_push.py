#!/usr/bin/env python3
"""Feishu app-bot push notification for the PR pipeline (self-healing).

Usage:
  python feishu_push.py "<title>" "<body markdown>"   # push a card to the group
  python feishu_push.py --test                        # send a test card
  python feishu_push.py --ensure                      # verify/repair the group route:
                                                      #   if the cached chat_id is dead
                                                      #   (send fails or group gone),
                                                      #   recreate the group, re-add the
                                                      #   owner, re-send, re-cache.

Config: C:/Users/ROG/.Codex/feishu.json
  {
    "mode": "app",
    "app_id": "cli_...",
    "app_secret": "...",          # keep SECRET — never commit
    "open_id": "ou_...",          # the owner's open_id (for adding them back)
    "chat_id": "oc_..."           # the bot-owned group chat (p2p is blocked on
                                  # this tenant with 230101 — group route only)
  }

Platform constraints discovered on this tenant (豆包账号 personal edition):
  * p2p bot→user sends are platform-blocked (error 230101) — ALWAYS use a
    bot-owned group chat as the transport.
  * Custom group bots ("自定义机器人" webhooks) are admin-disabled — an
    app bot (self-built app with 机器人 capability) is the only option.
"""
import json
import sys
import urllib.request

CFG_PATH = r"C:\Users\ROG\.Codex\feishu.json"
API = "https://open.feishu.cn/open-apis"
GROUP_NAME = "PR流水线通知"


def _request(method: str, path: str, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method,
    )
    return json.load(urllib.request.urlopen(req, timeout=20))


def _post(path, payload, token=None):
    return _request("POST", path, payload, token)


def _get(path, token):
    return _request("GET", path, token=token)


def tenant_token(cfg: dict) -> str:
    r = _post("/auth/v3/tenant_access_token/internal",
              {"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]})
    if r.get("code") != 0:
        raise RuntimeError(f"token failed: {r}")
    return r["tenant_access_token"]


def _send_card(token: str, chat_id: str, title: str, body: str, color: str = "blue") -> str:
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title},
                   "template": color},
        "elements": [{"tag": "markdown", "content": body or " "}],
    }
    r = _post("/im/v1/messages?receive_id_type=chat_id",
              {"receive_id": chat_id, "msg_type": "interactive",
               "content": json.dumps(card)},
              token)
    if r.get("code") != 0:
        raise RuntimeError(f"send failed: {r.get('code')} {r.get('msg')}")
    return r["data"]["message_id"]


def _ensure_group(token: str, cfg: dict) -> str:
    """Create the transport group and add the owner. Returns chat_id."""
    r = _post("/im/v1/chats?user_id_type=open_id",
              {"name": GROUP_NAME,
               "description": "开源贡献流水线事件推送"}, token)
    if r.get("code") != 0:
        raise RuntimeError(f"group create failed: {r}")
    chat_id = r["data"]["chat_id"]
    if cfg.get("open_id"):
        m = _post(f"/im/v1/chats/{chat_id}/members?user_id_type=open_id",
                  {"id_list": [cfg["open_id"]]}, token)
        if m.get("code") != 0:
            print(f"WARN: add-member failed: {m.get('code')} {m.get('msg')}")
    cfg["chat_id"] = chat_id
    json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), indent=2,
              ensure_ascii=False)
    print(f"created group {chat_id}")
    return chat_id


def _send_with_repair(cfg: dict, title: str, body: str, color: str = "blue") -> str:
    token = tenant_token(cfg)
    chat_id = cfg.get("chat_id")
    if not chat_id:
        chat_id = _ensure_group(token, cfg)
    try:
        return _send_card(token, chat_id, title, body, color)
    except RuntimeError as e:
        # The cached group may have been deleted or the bot removed from it.
        # Self-heal: recreate and retry exactly once.
        print(f"WARN: cached route failed ({e}) — rebuilding group")
        chat_id = _ensure_group(token, cfg)
        return _send_card(token, chat_id, title, body, color)


def push(cfg: dict, title: str, body: str, color: str = "blue") -> str:
    mid = _send_with_repair(cfg, title, body, color)
    print(f"sent OK, message_id: {mid}")
    return mid


def ensure(cfg: dict) -> str:
    token = tenant_token(cfg)
    chat_id = cfg.get("chat_id")
    if chat_id:
        try:
            return _send_card(token, chat_id, "飞书链路自检", "route OK", "green")
        except RuntimeError as e:
            print(f"WARN: cached route failed ({e}) — rebuilding")
    chat_id = _ensure_group(token, cfg)
    return _send_card(token, chat_id, "飞书链路自检", "route rebuilt OK", "green")


if __name__ == "__main__":
    cfg = json.load(open(CFG_PATH, encoding="utf-8"))
    if "--test" in sys.argv:
        push(cfg, "PR 流水线测试", "通知链路自检")
    elif "--ensure" in sys.argv:
        ensure(cfg)
        print("ensure OK")
    else:
        title = sys.argv[1] if len(sys.argv) > 1 else "PR 流水线通知"
        body = sys.argv[2] if len(sys.argv) > 2 else "通知链路已就绪"
        color = sys.argv[3] if len(sys.argv) > 3 else "blue"
        push(cfg, title, body, color)
