"""Producer/consumer wire contract and standalone deployment copy stay in sync."""
import base64
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import notification_contract as contract
import poll_fresh


class NotificationContractTests(unittest.TestCase):
    def event(self):
        return {"repo": "Owner/Repo", "number": 12, "title": "Fix `syntax` @someone other/repo#9\nnew line",
                "labels": ["bug", "@team"], "url": "https://github.com/Owner/Repo/issues/12",
                "created_at": "2026-10-25T09:00:00Z"}

    def test_standalone_monitor_has_identical_contract(self):
        self.assertEqual((ROOT / "tools/notification_contract.py").read_bytes(),
                         (ROOT / "repo-monitor/notification_contract.py").read_bytes())

    def test_roundtrip_preserves_data_and_canonicalizes_identity(self):
        event = self.event()
        block = contract.encode_events([event])
        self.assertNotIn("@someone", block)
        self.assertNotIn("https://github.com", block)
        expected = dict(event, repo="owner/repo", key="owner/repo#12")
        self.assertEqual(contract.decode_events("Display text\n" + block), [expected])
        self.assertEqual(contract.decode_events(block.replace("\n", "\r\n")), [expected])
        self.assertEqual(contract.decode_events(contract.encode_events([])), [])

    def test_legacy_prose_and_embedded_marker_are_not_protocol_blocks(self):
        for body in ("Legacy digest", "`<!-- zcode-events-v1`", "Title mentioning zcode-events-v2"):
            self.assertIsNone(contract.decode_events(body))

    def test_bad_payloads_cannot_fall_back_to_prose(self):
        block = contract.encode_events([self.event()])
        for body in (block.replace("v1", "v2"), block + "\n" + block,
                     "<!-- zcode-events-v1\ninvalid!\n-->", block[:-1]):
            with self.subTest(body=body), self.assertRaises(ValueError):
                contract.decode_events(body)
        for payload in ({"version": 2, "events": []}, {"version": True, "events": []},
                        {"version": 1, "events": {}}, {"version": 1, "events": [None]}):
            encoded = base64.b64encode(json.dumps(payload).encode()).decode()
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                contract.decode_events(f"<!-- zcode-events-v1\n{encoded}\n-->")

    def test_required_fields_are_typed_and_time_is_aware(self):
        for key, value in (("repo", "../owner/repo"), ("number", True), ("number", 0),
                           ("title", None), ("url", []), ("labels", [1]),
                           ("created_at", "2026-10-25")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                contract.encode_events([dict(self.event(), **{key: value})])

    def test_renderer_has_no_active_upstream_reference_and_emits_parseable_events(self):
        event = self.event()
        item = dict(event, _canon=event["repo"], labels=[{"name": label} for label in event["labels"]])
        body = poll_fresh.render([item], 10)
        self.assertIn("`Fix 'syntax' @someone other/repo#9 new line`", body)
        self.assertNotIn("https://github.com", body)
        decoded = contract.decode_events(body)
        self.assertEqual(decoded[0]["title"], event["title"])
        self.assertEqual(decoded[0]["labels"], event["labels"])
        self.assertEqual(decoded[0]["key"], "owner/repo#12")


if __name__ == "__main__":
    unittest.main()
