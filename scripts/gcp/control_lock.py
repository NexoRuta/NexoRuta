"""Shared Actions/guard mutex backed by GCS object generations, never local process state."""

from contextlib import contextmanager
import json
import math
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

OBJECT_NAME = "locks/demo-control.json"
TTL_SECONDS = 600
RENEW_SECONDS = 30


class JsonStorage:
    def __init__(self, bucket, access_token, opener=urllib.request.urlopen):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
            raise ValueError("Invalid control-lock bucket")
        self.bucket, self.access_token, self.opener = bucket, access_token, opener
        self.object_url = ("https://storage.googleapis.com/storage/v1/b/" + bucket
                           + "/o/" + urllib.parse.quote(OBJECT_NAME, safe=""))

    def request(self, method, url, data=None):
        request = urllib.request.Request(url, method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": "Bearer " + self.access_token, "Content-Type": "application/json"})
        with self.opener(request, timeout=15) as response:
            body = response.read(65536)
        return json.loads(body) if body else {}

    def read(self):
        try:
            generation = str(self.request("GET", self.object_url + "?fields=generation")["generation"])
            if not generation.isdigit() or int(generation) <= 0:
                raise ValueError("Invalid control-lock object generation")
            value = self.request("GET", self.object_url + "?alt=media&ifGenerationMatch=" + generation)
            return generation, value
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return "0", None
            raise

    def write(self, generation, value):
        query = urllib.parse.urlencode({"uploadType": "media", "name": OBJECT_NAME,
                                       "ifGenerationMatch": generation})
        url = "https://storage.googleapis.com/upload/storage/v1/b/" + self.bucket + "/o?" + query
        result = self.request("POST", url, value)
        updated = str(result["generation"])
        if not updated.isdigit() or int(updated) <= 0:
            raise ValueError("Invalid control-lock write generation")
        return updated

    def delete(self, generation):
        self.request("DELETE", self.object_url + "?ifGenerationMatch=" + str(generation))


class ControlLock:
    def __init__(self, store, *, owner=None, clock=time.time):
        self.store, self.clock = store, clock
        self.owner = owner or uuid.uuid4().hex
        if not re.fullmatch(r"[a-f0-9]{32}", self.owner):
            raise ValueError("Invalid control-lock owner")
        self.generation = None
        self.expires_at = 0.0
        self.lost = threading.Event()
        self.mutex = threading.Lock()

    def acquire(self):
        for _ in range(3):
            try:
                generation, value = self.store.read()
                if value is not None:
                    expiry = value.get("expires_at")
                    if (not re.fullmatch(r"[a-f0-9]{32}", value.get("owner", ""))
                            or not isinstance(expiry, (int, float)) or not math.isfinite(expiry)):
                        raise RuntimeError("The shared control lock is malformed; refusing to overwrite it")
                    if expiry > self.clock():
                        raise RuntimeError("Another demo control operation holds the shared lock")
                expiry = self.clock() + TTL_SECONDS
                self.generation = self.store.write(generation, {"owner": self.owner, "expires_at": expiry})
                self.expires_at = expiry
                return self
            except urllib.error.HTTPError as error:
                if error.code not in (409, 412):
                    raise RuntimeError("Unable to acquire the shared demo control lock") from None
        raise RuntimeError("The shared demo control lock changed concurrently; retry the operation")

    def check(self):
        with self.mutex:
            if self.generation is None or self.clock() >= self.expires_at:
                self.lost.set()
            if self.lost.is_set():
                raise RuntimeError("The shared demo control lock was lost; refusing further operations")

    def renew(self):
        with self.mutex:
            if self.lost.is_set() or self.generation is None or self.clock() >= self.expires_at:
                self.lost.set()
                raise RuntimeError("The shared demo control lock expired before renewal")
            try:
                expiry = self.clock() + TTL_SECONDS
                self.generation = self.store.write(self.generation, {"owner": self.owner, "expires_at": expiry})
                self.expires_at = expiry
            except Exception:
                self.lost.set()
                raise RuntimeError("Unable to renew the shared demo control lock") from None

    def release(self):
        with self.mutex:
            try:
                if self.generation is not None:
                    self.store.delete(self.generation)
            except Exception:
                self.lost.set()
                raise RuntimeError("Unable to release the owned shared demo control lock") from None
            finally:
                self.generation = None


@contextmanager
def control_lock(config, *, store=None, clock=time.time, renew_interval=RENEW_SECONDS):
    if store is None:
        import demo_session
        access_token = demo_session.command("gcloud", "auth", "print-access-token",
                                            "--project=" + config["GCP_PROJECT_ID"], capture=True).strip()
        if not access_token:
            raise RuntimeError("No Google access token is available for the shared control lock")
        store = JsonStorage(config["GCP_STATE_BUCKET"], access_token)
    lease = ControlLock(store, clock=clock).acquire()
    stop = threading.Event()

    def renew():
        while not stop.wait(renew_interval):
            try:
                lease.renew()
            except Exception:
                lease.lost.set()
                return

    worker = threading.Thread(target=renew, name="demo-control-lock-renewal", daemon=True)
    worker.start()
    failed = False
    try:
        yield lease
        lease.check()
    except BaseException:
        failed = True
        raise
    finally:
        stop.set()
        worker.join(timeout=20)
        if worker.is_alive():
            lease.lost.set()
        try:
            lease.release()
            if lease.lost.is_set():
                raise RuntimeError("The shared demo control lock was lost during this operation")
        except Exception:
            if not failed:
                raise
