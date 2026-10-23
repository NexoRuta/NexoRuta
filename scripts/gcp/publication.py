"""Advance the published channel atomically, without letting old Actions runs win a race."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def request(url, data=None):
    call = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                  headers={"Authorization": "Bearer " + os.environ["CLOUDSDK_AUTH_ACCESS_TOKEN"],
                                           "Content-Type": "application/json"})
    with urllib.request.urlopen(call, timeout=30) as response:
        return json.load(response)


def order(pointer):
    value = pointer.get("publication_order")
    # The previous pipeline had no ordering metadata. Its first tagged successor may replace it.
    if value is None:
        return (0, 0)
    if not isinstance(value, list) or len(value) != 2 or any(type(v) is not int or v < 1 for v in value):
        raise ValueError("Invalid channel publication order")
    return tuple(value)


def promote(bucket, pointer):
    candidate = order(pointer)
    if candidate == (0, 0):
        raise ValueError("New publications must include their Actions execution order")
    name = "channels/main.json"
    base = "https://storage.googleapis.com/storage/v1/b/" + urllib.parse.quote(bucket, safe="") + "/o/" + urllib.parse.quote(name, safe="")
    for _ in range(8):
        try:
            generation = request(base)["generation"]
            previous = request(base + "?" + urllib.parse.urlencode({"alt": "media", "generation": generation}))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            generation, previous = "0", {}
        if previous and (previous.get("channel") != "main" or not previous.get("release")):
            raise ValueError("Invalid existing publication channel")
        if order(previous) > candidate:
            print("Older publication retained as a release; current channel is unchanged.")
            return False
        if order(previous) == candidate:
            if previous != pointer:
                raise ValueError("Publication identity collision")
            return True
        query = urllib.parse.urlencode({"uploadType": "media", "name": name, "ifGenerationMatch": generation})
        try:
            request("https://storage.googleapis.com/upload/storage/v1/b/" + urllib.parse.quote(bucket, safe="") + "/o?" + query, pointer)
            return True
        except urllib.error.HTTPError as error:
            if error.code != 412:
                raise
            # Someone advanced the channel: reread its generation and ordering before retrying.
    raise RuntimeError("Publication channel changed repeatedly; retry publication")
