"""PC-102: the least S3 the platform needs - list and delete a project's files - with no dependency.

The agent engine keeps no runtime dependencies (pyproject: external-runtime-dependencies = false),
so this signs requests itself (AWS Signature Version 4, path-style), which Cloudflare R2 and AWS S3
both accept. The generated apps use boto3; only the platform's clean-up uses this. Keys are never
logged or included in an error.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_EMPTY_SHA = hashlib.sha256(b"").hexdigest()
_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


class S3Error(RuntimeError):
    pass


@dataclass(frozen=True)
class S3Target:
    endpoint: str  # "https://<account>.r2.cloudflarestorage.com" or "https://s3.<region>.amazonaws.com"
    region: str
    bucket: str
    access_key: str
    secret_key: str = ""

    def __repr__(self) -> str:  # never show the secret
        return f"S3Target(endpoint={self.endpoint!r}, bucket={self.bucket!r})"


def target_from_settings(settings: dict[str, str]) -> S3Target:
    region = settings.get("S3_REGION") or "us-east-1"
    endpoint = settings.get("S3_ENDPOINT") or f"https://s3.{region}.amazonaws.com"
    return S3Target(endpoint.rstrip("/"), region, settings["S3_BUCKET"], settings["S3_ACCESS_KEY_ID"],
                    settings["S3_SECRET_ACCESS_KEY"])


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _request(target: S3Target, method: str, key: str = "", query: dict[str, str] | None = None,
             now: _dt.datetime | None = None, timeout: float = 30.0) -> bytes:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    amz_date, date = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    host = urllib.parse.urlparse(target.endpoint).netloc
    path = "/" + urllib.parse.quote(target.bucket) + ("/" + urllib.parse.quote(key, safe="/~") if key else "")
    canonical_query = "&".join(
        f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}" for k, v in sorted((query or {}).items())
    )
    headers = {"host": host, "x-amz-content-sha256": _EMPTY_SHA, "x-amz-date": amz_date}
    signed = ";".join(sorted(headers))
    canonical = "\n".join([method, path, canonical_query, "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)),
                           signed, _EMPTY_SHA])
    scope = f"{date}/{target.region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key_bytes = _sign(_sign(_sign(_sign(("AWS4" + target.secret_key).encode(), date), target.region), "s3"), "aws4_request")
    signature = hmac.new(key_bytes, to_sign.encode(), hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        f"{target.endpoint}{path}" + (f"?{canonical_query}" if canonical_query else ""),
        method=method,
        headers={
            "x-amz-content-sha256": _EMPTY_SHA,
            "x-amz-date": amz_date,
            "Authorization": f"AWS4-HMAC-SHA256 Credential={target.access_key}/{scope}, SignedHeaders={signed}, Signature={signature}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        code = ""
        try:
            code = ET.fromstring(error.read()).findtext("Code") or ""
        except ET.ParseError:
            pass
        raise S3Error(f"{method} answered {error.code} {code}".strip()) from None
    except OSError as error:
        raise S3Error(f"{method} failed: {type(error).__name__}") from None


def list_keys(target: S3Target, prefix: str) -> list[str]:
    keys: list[str] = []
    token = ""
    while True:
        query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            query["continuation-token"] = token
        root = ET.fromstring(_request(target, "GET", query=query))
        keys += [node.findtext(f"{_NS}Key") or node.findtext("Key") for node in
                 (root.findall(f"{_NS}Contents") or root.findall("Contents"))]
        token = root.findtext(f"{_NS}NextContinuationToken") or root.findtext("NextContinuationToken") or ""
        if not token:
            return [k for k in keys if k]


def delete_key(target: S3Target, key: str) -> None:
    _request(target, "DELETE", key)


def delete_prefix(target: S3Target, prefix: str) -> int:
    """Delete every object under ``prefix`` (which must name a project's folder); return how many."""
    if not prefix.strip("/") or prefix.count("/") < 1:
        raise S3Error("refusing to delete without a project prefix")
    keys = list_keys(target, prefix)
    for key in keys:
        delete_key(target, key)
    return len(keys)
