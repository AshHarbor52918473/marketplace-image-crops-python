import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_images import BuyerUpdate, SellerAsset, ensure_bucket_and_service


def main() -> None:
    service = ensure_bucket_and_service()
    handoff = service.prepare_order(
        SellerAsset("lamp-17", {"base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="}),
        BuyerUpdate("order-204", ("1:1", "3:4", "16:9")),
    )
    print(handoff)
    print(service.handoff_url(handoff, "1:1"))


if __name__ == "__main__":
    main()
