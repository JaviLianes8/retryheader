# retryheader guide

The behaviour of every public name in detail. Each Python block below runs as a test: a
comment line after a `print` holds what it prints.

## Retry-After

`parse_retry_after(value, *, now=None, strict=False)` returns the delay in seconds as a
`float`, never negative.

- **delay-seconds** is one or more ASCII digits and nothing else: `+5`, `-5`, `1.5`,
  `1e3` and Arabic-Indic digits are refused. A value too large for a float gives
  `math.inf`; cap it before sleeping.
- **An HTTP-date** in any of its three formats is measured from `now`, the current UTC
  time by default; a naive `now` is read as UTC. A date in the past gives `0.0`. An aware
  `now` whose UTC moment falls outside years 1 to 9999 is a `ValueError`, checked on
  entry whatever the value (the same holds for `parse_http_date` and
  `delay_from_headers`).
- Only spaces and tabs around the value are ignored (RFC 9110 optional whitespace).
- `strict` applies to the date form, see below.

`build_retry_after(value)` writes the header for a server:

- An `int`, `float` or `timedelta` becomes delay-seconds. A fraction rounds **up** and a
  negative delay becomes `0`, so a client is never asked back sooner than intended. An
  `int` subclass, such as an `IntEnum`, is written as its number.
- A `datetime` becomes an IMF-fixdate in GMT (naive means UTC); a fraction of a second
  rounds up to the next second.
- A subclass of `int`, `float`, `timedelta` or `datetime` is read as its value: its own
  methods never change the text written.

```python
from datetime import datetime, timedelta, timezone

from retryheader import build_retry_after, parse_retry_after

print(build_retry_after(2.000001), build_retry_after(timedelta(seconds=-3)))
# 3 0
print(build_retry_after(datetime(2026, 10, 21, 7, 28, 0, 1, tzinfo=timezone.utc)))
# Wed, 21 Oct 2026 07:28:01 GMT
print(parse_retry_after(" \t42 "), parse_retry_after("9" * 400))
# 42.0 inf
```

## HTTP-date

`parse_http_date(value, *, now=None, strict=False)` returns an aware UTC `datetime`.

All three formats of RFC 9110 section 5.6.7 are read: IMF-fixdate
(`Sun, 06 Nov 1994 08:49:37 GMT`), the obsolete RFC 850 form
(`Sunday, 06-Nov-94 08:49:37 GMT`) and asctime (`Sun Nov  6 08:49:37 1994`).

- **Two-digit years** (RFC 850 form) follow RFC 9110: a year that appears to be more
  than 50 years after `now` is the most recent past year with the same last two digits.
  Exactly 50 years ahead, to the second, is still in the future.
- **Leap seconds**: `23:59:60` reads as the first second of the next day. It is accepted
  only at the end of a UTC day; the list of leap seconds actually inserted is not
  consulted.
- Impossible dates (30 February, hour 24) are refused.

**`strict=True`** accepts the RFC 9110 grammar and nothing else: the exact letter case,
single spaces, `GMT`, and a day name that is the day the date falls on (RFC 9110 adopts
the RFC 5322 meaning of the day name).

**The default mode** is robust, as RFC 9110 asks recipients to be. On top of the strict
grammar it reads:

- the three formats in any letter case, without checking the day name;
- RFC 5322 dates (section 3.3, with the obsolete forms of section 4.3, but no comments):
  an optional day name, a one- or two-digit day, a two- to four-digit year, seconds
  optional, flexible spaces (also around the colons of the time, `08 : 49 : 37`), and a
  zone that is numeric (`+0200`, up to `+9959`, minutes
  up to 59) or one of `UT`, `UTC`, `GMT`, `EST`, `EDT`, `CST`, `CDT`, `MST`, `MDT`, `PST`,
  `PDT`. A two-digit year below 50 is 20xx, from 50 19xx; a three-digit year counts from
  1900. A named zone may follow the time without a space (verified erratum 6639).

A date with no zone, a military single-letter zone (`Z`) or an unknown name (`CET`) is
refused in both modes. RFC 5322 suggests reading those as `-0000`, but a guessed zone
would silently move a delay by hours.

```python
from datetime import datetime, timezone

from retryheader import RetryAfterError, parse_http_date

now = datetime(2026, 10, 21, tzinfo=timezone.utc)
print(parse_http_date("Thursday, 01-Jan-76 00:00:00 GMT", now=now).year)
# 2076
print(parse_http_date("sun, 6 nov 94 08:49 EST", now=now))
# 1994-11-06 13:49:00+00:00
for text in ("Mon, 06 Nov 1994 08:49:37 GMT", "Sun, 06 Nov 1994 08:49:37 CET"):
    try:
        parse_http_date(text, strict=text.endswith("GMT"))
    except RetryAfterError as error:
        print(error)
# the day name does not match the date: 'Mon, 06 Nov 1994 08:49:37 GMT'
# invalid HTTP-date: 'Sun, 06 Nov 1994 08:49:37 CET'
```

`format_http_date(moment)` writes the IMF-fixdate, the only form senders may use: naive
means UTC, other zones are converted, a fraction of a second rounds up, the year has four
digits. A moment whose UTC time (rounded up) leaves years 1 to 9999 is a `ValueError`.

## RateLimit and RateLimit-Policy

The fields follow draft-ietf-httpapi-ratelimit-headers-11, an Internet-Draft. Both are
Structured Field lists (RFC 9651) of items whose value is a String naming the policy;
a Token, a Display String or any other type there makes the field malformed.

| Field | Parameter | Attribute | Rule |
| --- | --- | --- | --- |
| RateLimit-Policy | `q` | `QuotaPolicy.quota` | required Integer, at least 0 |
| | `w` | `window` | optional Integer, at least 1 |
| | `qu` | `unit` | optional String, `"requests"` by default |
| | `pk` | `partition_key` | optional Byte Sequence |
| RateLimit | `r` | `ServiceLimit.remaining` | required Integer, at least 0 |
| | `t` | `window` | optional Integer, at least 0 |
| | `pk` | `partition_key` | optional Byte Sequence |

Any other parameter lands in `extra`, a read-only dict. A Date becomes an aware UTC
`datetime`; a Token comes back as a `Token` and a Display String as a `DisplayString`,
both public `str` subclasses, and each is written back in its own form. Build an `extra`
value with `Token("sliding")` or `DisplayString("café")` to send those types; a plain
`str` is sent as a String. A `DisplayString` holds any text UTF-8 can encode: building one
with a lone surrogate raises `ValueError`. A repeated parameter keeps its last value (RFC 9651).

`parse_ratelimit_policy` and `parse_ratelimit` take the field value or all its field
lines (combined with commas, as RFC 9651 requires). The policy field must list at least
one policy; an empty `RateLimit` field has no limits. Anything malformed raises
`RateLimitError` for the whole field.

`QuotaPolicy` and `ServiceLimit` check their values on creation (`TypeError` for a wrong
type, `bool` included, `ValueError` for a number out of range: a count or an integer
`extra` value has at most 15 digits, as in a structured field) and store every value as
its exact built-in type (`str`, `int`, `float`, `bytes`, `bool`, `datetime`; `Token` and
`DisplayString` keep theirs), so a subclass never changes how a value shows or hashes.
They are frozen, compare with `extra`, hash without it, and pickle by public names only
(`retryheader.<Name>`, `extra` as a plain dict).
`build_ratelimit_policy` and `build_ratelimit` raise `ValueError` for what a structured
field cannot carry: text outside printable ASCII, an integer past 15 digits, a decimal
past 12 integer digits, an invalid parameter name, an `extra` name that is already a
defined parameter, a date with a fraction of a second. Decimals round half to even to
three places, whatever the caller's `decimal` context.

```python
from retryheader import ServiceLimit, build_ratelimit, parse_ratelimit

(limit,) = parse_ratelimit('"a";r=1;t=2;mode=sliding;note=%"caf%c3%a9";at=@0')
print(limit.extra["mode"], limit.extra["note"], limit.extra["at"])
# sliding café 1970-01-01 00:00:00+00:00
print(build_ratelimit([limit]))
# "a";r=1;t=2;mode=sliding;note=%"caf%c3%a9";at=@0
print(build_ratelimit([ServiceLimit("a", 0, extra={"ratio": 0.0625})]))
# "a";r=0;ratio=0.062
```

## How long to wait: `delay_from_headers`

`delay_from_headers(headers, *, now=None, use_date_header=False)` reads a mapping, any
object with `items()` (`http.client.HTTPMessage`, werkzeug `Headers`) or an iterable of
`(name, value)` pairs. Names match without case; repeated fields are all read.

1. A valid Retry-After wins (the draft: it takes precedence); with several valid ones,
   the longest delay.
2. Otherwise, the longest `t` of a service limit whose `r` is 0.
3. Otherwise `None`.

Malformed fields are ignored, as both specifications ask. The shapes of older drafts are
not read: `limit=2, remaining=0, reset=60` is a malformed RateLimit field under draft -11,
and `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset` are not draft -11
fields. The RateLimit fields of a response with an `Age` above zero, which a cache
served, are ignored too (draft section 7.3); the first non-empty member of `Age` is read
and an invalid `Age` is ignored (RFC 9111, RFC 9110 section 5.6.1.2). With
`use_date_header=True`, an HTTP-date in Retry-After is measured from the response's own
`Date` when the response has exactly one `Date` field line and it is valid, which cancels
clock skew. `Date` is a singleton field, so two `Date` lines, even if one is valid, make
it unusable and `now` is used instead.

requests (`CaseInsensitiveDict`) and httpx (`Headers` as a mapping) join repeated lines
of a field with a comma. Joined RateLimit lines read the same as separate lines; a joined
Retry-After is not a valid value and is ignored. Pass httpx's `multi_items()` to keep
every line. Names and values must be `str`: bytes pairs (as in ASGI) are a `TypeError`.

## Errors

| Error | When |
| --- | --- |
| `RetryAfterError` (a `ValueError`) | a Retry-After value or an HTTP-date cannot be parsed |
| `RateLimitError` (a `ValueError`) | a RateLimit or RateLimit-Policy field is malformed |
| `ValueError` | a value cannot be built: non-finite or huge number, out-of-range date, unrepresentable field; an aware `now` outside years 1 to 9999 in UTC |
| `TypeError` | an argument of the wrong type, `bool` where a number is expected included |

Messages quote at most 40 characters of the input and describe a huge integer by its size.

## Stability

From 1.0.0 the fifteen names of `retryheader.__all__`, their signatures, defaults and
error types follow Semantic Versioning. The type aliases in the signatures are not
exported: an `extra` value is `int | float | str | bytes | bool | datetime`, and
`headers` is a mapping of `str` to `str`, an object whose `items()` gives `(str, str)`
pairs, or an iterable of such pairs. The RateLimit fields follow draft -11; if a later
revision or the RFC changes them, the change is released as documented in the changelog.
Everything else is private and may change.

## Upgrading from 0.2

Every 0.2.1 call keeps its result except for these changes (all in the changelog):

- Python 3.10 works (0.2.1 failed on `import`).
- Error messages are cut to 40 characters of input; some say more precisely what is wrong.
- `strict=True` refuses a day name that is not the day of the date.
- The default mode reads a named zone right after the time (`08:49:37GMT`).
- A Display String where the draft requires a String (the policy name, `qu`) and a byte
  sequence made only of padding (`:=:`) make a RateLimit field malformed.
- `delay_from_headers` ignores the RateLimit fields of a response with an `Age` above zero,
  and refuses a header that is not a `(name, value)` pair with `TypeError`.
- `QuotaPolicy` and `ServiceLimit` check `extra` on creation (names `str`, values of the
  supported types) and store plain built-in values; they show and pickle as
  `retryheader.<Name>`, and pickles made by 0.2.1 still load.
- A float `extra` value too large for a decimal is a `ValueError` (it raised
  `decimal.InvalidOperation`), and the caller's `decimal` context no longer matters.
- A count (`quota`, `remaining`, `window`) or an integer `extra` value past 15 digits is
  a `ValueError` on creation; 0.2.1 accepted it and failed only when building.
- `Token` and `DisplayString` are public, and their pickles name `retryheader`.
- A `DisplayString` UTF-8 cannot encode (a lone surrogate) is the library's own short
  `ValueError` when built; 0.2.1 raised the codec's `UnicodeEncodeError`.
- An aware `now` with no UTC moment in years 1 to 9999 is a `ValueError` on entry; 0.2.1
  raised it only for some header forms.
- The default mode reads spaces around the colons of an RFC 5322 time, and
  `delay_from_headers` skips empty members of `Age`.
- A subclass of `int`, `float`, `str`, `bytes`, `datetime` or `timedelta` is read and
  stored as its plain value, so its own methods no longer change what is written.
