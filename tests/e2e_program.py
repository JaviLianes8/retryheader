"""The programs the end-to-end tests run against an installed retryheader."""

from __future__ import annotations

# A consumer: every public name from the installed package, and a real HTTP exchange with
# Python's own server and clients over a local socket.
PROGRAM = r"""
import http.client, http.server, importlib.metadata, importlib.resources, pickle, threading
import urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
import retryheader
from retryheader import *

assert "site-packages" in retryheader.__file__, retryheader.__file__
assert importlib.metadata.version("retryheader") == retryheader.__version__ == "1.0.0"
assert importlib.metadata.requires("retryheader") is None
assert importlib.resources.files("retryheader").joinpath("py.typed").is_file()
assert sorted(n for n in dir(retryheader) if not n.startswith("_")) == sorted(retryheader.__all__)

now = datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)
for text in ("Wed, 21 Oct 2026 07:30:00 GMT", "Wednesday, 21-Oct-26 07:30:00 GMT",
             "Wed Oct 21 07:30:00 2026"):
    assert parse_retry_after(text, now=now, strict=True) == 120.0, text
assert parse_http_date("Monday, 01-Jan-60 00:00:00 GMT", now=now).year == 2060
assert build_retry_after(2.5) == "3"
assert build_retry_after(timedelta(seconds=1, microseconds=1)) == "2"
assert format_http_date(now) == "Wed, 21 Oct 2026 07:28:00 GMT"
for bad in ("Wed, 21 Oct 2026 07:30:00", "-5", "x" * 10**6):
    try:
        parse_retry_after(bad)
    except RetryAfterError as error:
        assert len(str(error)) < 120
    else:
        raise AssertionError(bad[:40])
policies = parse_ratelimit_policy('"burst";q=100;w=60, "daily";q=1000;w=86400')
assert parse_ratelimit_policy(build_ratelimit_policy(policies)) == policies
limits = parse_ratelimit(['"a";r=0;t=30', '"b";r=5;pk=:QXBwLTk5OQ==:'])
assert limits[1] == ServiceLimit("b", 5, None, b"App-999")
assert pickle.loads(pickle.dumps(limits[1])) == limits[1]
assert QuotaPolicy.__module__ == "retryheader"
try:
    parse_ratelimit('"a";r=-1')
except RateLimitError:
    pass
else:
    raise AssertionError("negative quota accepted")

T = 1_700_000_000


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response_only(429)
        self.send_header("Date", self.date_time_string(T))
        if self.path == "/date":
            self.send_header("Retry-After", self.date_time_string(T + 7))
        self.send_header("RateLimit", '"burst";r=0;t=30')
        self.send_header("RateLimit", '"daily";r=0;t=86400')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
try:
    urllib.request.urlopen(base + "/date")
except urllib.error.HTTPError as error:
    assert error.code == 429
    assert delay_from_headers(error.headers, use_date_header=True) == 7.0
connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
connection.request("GET", "/limits")
response = connection.getresponse()
assert response.status == 429
assert delay_from_headers(response.headers) == delay_from_headers(response.getheaders()) == 86400.0
connection.close()
server.shutdown()
print("e2e ok")
"""

# The same calls on 0.2.1 and 1.0.0; the last line is a pickle. With an argument (a pickle
# in hex) it only checks that the pickle loads as the expected value.
PROBE = r"""
import pickle, sys
from datetime import datetime, timezone
import retryheader as r

expected = r.ServiceLimit("burst", 0, 30, b"user-1", {"acme": "x"})
if len(sys.argv) > 1:
    assert pickle.loads(bytes.fromhex(sys.argv[1])) == expected
    print("pickle ok")
    raise SystemExit
now = datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)
print(r.__version__)
print(r.parse_retry_after("120"), r.parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=now))
print(r.parse_http_date("Sunday, 06-Nov-94 08:49:37 GMT", now=now))
print(r.build_retry_after(2.5), r.format_http_date(now))
print(r.parse_ratelimit('"a";r=0;t=30, "b";r=5;pk=:YQ==:'))
print(r.parse_ratelimit_policy('"burst";q=100;w=60;qu="content-bytes"'))
print(r.build_ratelimit([expected]))
print(r.delay_from_headers({"Retry-After": "7", "RateLimit": '"a";r=0;t=30'}))
print(pickle.dumps(expected, protocol=4).hex())
"""
