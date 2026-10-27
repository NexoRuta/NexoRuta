from contextlib import contextmanager
import io
import json
import threading
import unittest
from unittest.mock import Mock
import urllib.error
import urllib.parse

import control_lock as locks


def conflict():
    return urllib.error.HTTPError("https://storage.invalid", 412, "precondition", {}, io.BytesIO())


class MemoryStore:
    def __init__(self):
        self.generation = 0
        self.value = None
        self.writes, self.deletes = [], []

    def read(self):
        return str(self.generation if self.value is not None else 0), self.value

    def write(self, generation, value):
        self.writes.append((generation, value))
        current = self.generation if self.value is not None else 0
        if int(generation) != current:
            raise conflict()
        self.generation += 1
        self.value = value.copy()
        return str(self.generation)

    def delete(self, generation):
        self.deletes.append(generation)
        if str(self.generation) != generation or self.value is None:
            raise conflict()
        self.value = None


class ControlLockTests(unittest.TestCase):
    def test_owned_live_lease_excludes_other_owners_and_renews_with_its_generation(self):
        store, now = MemoryStore(), [1000.0]
        first = locks.ControlLock(store, owner="a" * 32, clock=lambda: now[0]).acquire()
        with self.assertRaisesRegex(RuntimeError, "Another"):
            locks.ControlLock(store, owner="b" * 32, clock=lambda: now[0]).acquire()
        now[0] += 30
        first.renew()
        self.assertEqual(store.writes[-1][0], "1")
        self.assertEqual(store.value, {"owner": "a" * 32, "expires_at": 1630.0})
        first.check()

    def test_expired_lease_is_stolen_by_cas_and_old_owner_cannot_release_new_owner(self):
        store, now = MemoryStore(), [1000.0]
        first = locks.ControlLock(store, owner="a" * 32, clock=lambda: now[0]).acquire()
        now[0] = 1601
        second = locks.ControlLock(store, owner="b" * 32, clock=lambda: now[0]).acquire()
        self.assertEqual(store.writes[-1][0], "1")
        with self.assertRaisesRegex(RuntimeError, "release"):
            first.release()
        self.assertEqual(store.value["owner"], second.owner)
        second.check()

    def test_generation_race_is_retried_but_never_overwrites_the_winning_live_owner(self):
        store = MemoryStore()
        original = store.write

        def race(generation, value):
            original(generation, {"owner": "b" * 32, "expires_at": 1600})
            raise conflict()

        store.write = race
        with self.assertRaisesRegex(RuntimeError, "Another"):
            locks.ControlLock(store, clock=lambda: 1000).acquire()
        self.assertEqual(store.value["owner"], "b" * 32)
        self.assertEqual(len(store.writes), 1)

    def test_renewal_failure_and_expiry_fail_closed(self):
        store, now = MemoryStore(), [1000.0]
        lease = locks.ControlLock(store, clock=lambda: now[0]).acquire()
        store.write = Mock(side_effect=conflict())
        with self.assertRaisesRegex(RuntimeError, "renew"):
            lease.renew()
        with self.assertRaisesRegex(RuntimeError, "lost"):
            lease.check()
        other = locks.ControlLock(MemoryStore(), clock=lambda: now[0]).acquire()
        now[0] += 600
        with self.assertRaisesRegex(RuntimeError, "lost"):
            other.check()

    def test_context_preserves_original_exception_when_release_also_fails(self):
        store = MemoryStore()
        store.delete = Mock(side_effect=conflict())
        with self.assertRaisesRegex(ValueError, "original operation failure"):
            with locks.control_lock({}, store=store, clock=lambda: 1000):
                raise ValueError("original operation failure")

    def test_background_renewal_marks_loss_and_context_exit_reports_it(self):
        store = MemoryStore()
        renewed = threading.Event()
        original = store.write

        def renew_failure(generation, value):
            if generation != "0":
                renewed.set()
                raise conflict()
            return original(generation, value)

        store.write = renew_failure
        with self.assertRaisesRegex(RuntimeError, "lost"):
            with locks.control_lock({}, store=store, clock=lambda: 1000, renew_interval=0.001) as lease:
                self.assertTrue(renewed.wait(1))
                self.assertTrue(lease.lost.wait(1))
        self.assertIsNone(store.value)

    def test_json_api_binds_reads_uploads_and_deletes_to_exact_generations(self):
        calls, replies = [], [{"generation": "7"}, {"owner": "a" * 32, "expires_at": 1000}, {"generation": "8"}, None]

        @contextmanager
        def opener(request, timeout):
            calls.append(request)
            reply = replies.pop(0)
            yield io.BytesIO(json.dumps(reply).encode() if reply is not None else b"")

        store = locks.JsonStorage("demo-state-bucket", "private-token", opener=opener)
        generation, value = store.read()
        self.assertEqual(generation, "7")
        self.assertEqual(store.write(generation, value), "8")
        store.delete("8")
        queries = [urllib.parse.parse_qs(urllib.parse.urlsplit(call.full_url).query) for call in calls]
        self.assertEqual(queries[1]["ifGenerationMatch"], ["7"])
        self.assertEqual(queries[2], {"uploadType": ["media"], "name": [locks.OBJECT_NAME], "ifGenerationMatch": ["7"]})
        self.assertEqual(queries[3]["ifGenerationMatch"], ["8"])
        self.assertEqual([call.method for call in calls], ["GET", "GET", "POST", "DELETE"])
        self.assertTrue(all("private-token" not in call.full_url for call in calls))


if __name__ == "__main__":
    unittest.main()
