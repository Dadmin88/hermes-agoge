from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--free-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    hermes_root = Path(args.hermes_root).resolve()
    sys.path.insert(0, str(hermes_root))
    from hermes_cli.models import (
        get_pricing_for_provider,
        partition_nous_models_by_tier,
        provider_model_ids,
    )

    provider = args.provider.strip().lower()
    model_ids = provider_model_ids(provider, force_refresh=args.refresh)
    pricing = get_pricing_for_provider(provider, force_refresh=args.refresh)
    if args.free_only:
        if provider != "nous":
            raise RuntimeError("free-only filtering is currently proven only for Nous")
        model_ids, _ = partition_nous_models_by_tier(model_ids, pricing, True)

    rows = []
    for model_id in model_ids:
        price = pricing.get(model_id) or {}
        try:
            is_free = float(price.get("prompt", "1")) == 0 and float(
                price.get("completion", "1")
            ) == 0
        except (TypeError, ValueError):
            is_free = False
        rows.append(
            {
                "provider": provider,
                "model_id": model_id,
                "pricing": {
                    key: str(value)
                    for key, value in sorted(price.items())
                    if value is not None
                },
                "free": is_free,
            }
        )
    print(
        json.dumps(
            {
                "schema": "agoge.hermes-provider-catalog-bridge.v1",
                "provider": provider,
                "free_only": bool(args.free_only),
                "count": len(rows),
                "models": rows,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
