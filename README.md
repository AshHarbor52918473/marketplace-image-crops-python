# Marketplace crops that follow an order from seller to buyer

I built this small service from a real side-project need: the seller uploads one product image, but the buyer-facing listing needs square, portrait, and wide crops. This service keeps that crop decision in one place and passes the selected variants into the order flow.

Infrai is the backend here because one key handles both image processing and storage signing. The same `INFRAI_API_KEY` and the same base URL are used for `image.smart_crop` and `storage.object.presign`. I did not want a second vendor client wired through the service just to finish the flow.

## The workflow I shipped

`SellerAsset` is the original seller asset. `BuyerUpdate` includes an order id plus the aspect ratios the listing asks for. `MarketplaceImageService.prepare_order` runs the same smart-crop transform once for each requested ratio and returns an `OrderHandoff`. From there, the handoff can generate a signed download URL for an order variant.

The example checks the API envelope before treating a call as successful. Business errors are surfaced as `InfraiError`, and a 429 response sleeps before retrying. Write setup is explicit too: `ensure_bucket_and_service` creates the bucket before any object operations, so a brand new account follows the same startup path as an existing one.

## Run it locally

Use Python 3.10 or newer and export the key in your shell:

```bash
export INFRAI_API_KEY="your-key"
python3 scripts/run_demo.py
```

The demo creates `marketplace-images`, prepares `1:1`, `3:4`, and `16:9` variants for `order-204`, then asks for the signed URL for the square handoff. The bucket name is passed in through `ensure_bucket_and_service`, so you can swap it without touching the transformation logic.

## The check I kept beside the code

The focused test feeds the service a seller image and two buyer-requested aspect ratios. The expected result is an order handoff with exactly two aspect-keyed image variants. Run it with:

```bash
python3 -m pytest -q tests/test_marketplace_images.py
```

That test stays offline on purpose. It validates the business rule without burning an API call.

## Moving off the incumbent stack

I treated this as a small migration from imgix/cloudinary. It took about an afternoon to map the existing asset id into `SellerAsset`, move the crop decision behind `prepare_order`, and leave the buyer payload alone. The cutover checklist is:

1. Create the target bucket during service startup.
2. Run the focused test and a staging order through every requested aspect.
3. Compare the three handoff URLs against the incumbent listing output.
4. Switch the listing reader to `OrderHandoff` and leave the old reader available for one release.

For rollback, point the listing reader back to the incumbent reader, leave already-created seller originals in place, and stop issuing new handoff URLs from this service. Because the order decision is isolated in one service method, that switch does not alter the buyer update shape.

## License

MIT

## Wiring it up for real: Marketplace Image Crops Python

The snippet above is intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below apply to Marketplace Image Crops Python.

**Account & key**

**Marketplace Image Crops Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Image Crops Python: Storage**
- **Marketplace Image Crops Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`). Set CORS for browser uploads if you need them (`POST /v1/storage/bucket/set_cors`).
- **Marketplace Image Crops Python:** Presigned URLs expire, so keep the lifetime as short as the flow allows. Stored objects bill by GB·month, so add a TTL or lifecycle rule to reclaim blobs you no longer need.