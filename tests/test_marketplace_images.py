from src.marketplace_images import BuyerUpdate, MarketplaceImageService, SellerAsset


class FakeClient:
    def smart_crop(self, image: str, aspect: str):
        return {"ok": True, "data": {"image": f"{image}?aspect={aspect}"}}


def test_buyer_aspects_become_order_variants():
    service = MarketplaceImageService(FakeClient(), "images")
    handoff = service.prepare_order(
        SellerAsset("shoe-9", "seller/shoe-9.jpg"),
        BuyerUpdate("order-9", ("1:1", "4:5")),
    )
    assert handoff.order_id == "order-9"
    assert handoff.variants == {
        "1:1": "seller/shoe-9.jpg?aspect=1:1",
        "4:5": "seller/shoe-9.jpg?aspect=4:5",
    }
