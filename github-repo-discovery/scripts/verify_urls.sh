#!/usr/bin/env bash
# verify_urls.sh — spot-check that GitHub URLs are real (200/301/302).
#
# Usage:
#   verify_urls.sh url1 url2 url3 ...
#   echo url1 url2 | xargs verify_urls.sh
#
# Exit 0 if all URLs are reachable, 1 if any fail.
# Prints "OK    <status>  <url>" or "FAIL  <status>  <url>" per URL.

set -u

if [[ $# -eq 0 ]]; then
  echo "usage: $0 url1 [url2 ...]" >&2
  exit 2
fi

fail=0
for url in "$@"; do
  status=$(curl -s -o /dev/null -L -w "%{http_code}" \
    -A "github-repo-discovery/1.0" \
    --max-time 10 \
    "$url" 2>/dev/null || echo "000")

  case "$status" in
    200|301|302)
      printf "OK    %s  %s\n" "$status" "$url"
      ;;
    *)
      printf "FAIL  %s  %s\n" "$status" "$url"
      fail=1
      ;;
  esac
done

exit $fail
