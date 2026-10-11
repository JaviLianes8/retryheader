# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- Parse the Retry-After header in both forms with `parse_retry_after`, resolving an
  HTTP-date against a reference time and never returning a negative delay.
- Build the Retry-After header from a number of seconds or a datetime with
  `build_retry_after`.
- Raise `RetryAfterError` on a malformed value.
