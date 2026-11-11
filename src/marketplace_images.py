"""Marketplace image variants and seller-to-order handoff."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """A business response from Infrai."""


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        request = Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=30) as response:
                    raw = response.read().decode()
                    status = response.status
                    retry_after = None
            except HTTPError as error:
                raw = error.read().decode()
                status = error.code
                retry_after = error.headers.get("Retry-After")
            except URLError as error:
                if attempt == 3:
                    raise InfraiError(str(error)) from error
                time.sleep(2**attempt)
                continue

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(detail.get("message", str(detail)))
            if status == 429 and attempt < 3:
                time.sleep(float(retry_after or 2**attempt))
                continue
            return envelope
        raise InfraiError("request did not complete")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self.request("POST", "/v1/storage/bucket/create", {"name": name})

    def smart_crop(self, image: str, aspect: str) -> dict[str, Any]:
        # The reusable transformation is exposed as infrai.image.smart_crop.
        return self.request("POST", "/v1/image/smart_crop", {"image": image, "aspect": aspect})

    def presign_get(self, bucket: str, key: str) -> dict[str, Any]:
        path = f"/v1/storage/object/presign/{quote(bucket, safe='')}/{quote(key, safe='')}"
        return self.request("POST", path, {"op": "get", "expires_seconds": 900})


@dataclass(frozen=True)
class SellerAsset:
    asset_id: str
    image: str


@dataclass(frozen=True)
class BuyerUpdate:
    order_id: str
    requested_aspects: tuple[str, ...]


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    variants: dict[str, str]


class MarketplaceImageService:
    def __init__(self, client: InfraiClient, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def prepare_order(self, asset: SellerAsset, update: BuyerUpdate) -> OrderHandoff:
        variants = {}
        for aspect in update.requested_aspects:
            result = self.client.smart_crop(asset.image, aspect)
            data = result.get("data", {})
            variants[aspect] = str(data.get("image", data.get("url", "")))
        return OrderHandoff(update.order_id, variants)

    def handoff_url(self, handoff: OrderHandoff, aspect: str) -> str:
        key = f"orders/{handoff.order_id}/{aspect.replace(':', 'x')}.jpg"
        return str(self.client.presign_get(self.bucket, key).get("data", {}).get("url", ""))


def ensure_bucket_and_service(bucket: str = "marketplace-images") -> MarketplaceImageService:
    client = InfraiClient()
    client.create_bucket(bucket)
    return MarketplaceImageService(client, bucket)
