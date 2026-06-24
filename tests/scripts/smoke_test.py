#!/usr/bin/env python3
"""Smoke test script for Product Vehicle Compatibility Scanner."""

import argparse
import sys
from pathlib import Path

import httpx
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "smoke_config.yaml"


def load_config(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "base_url": "http://localhost:8000",
        "health_endpoint": "/api/health",
        "timeout_seconds": 30,
    }


def check_health(base_url: str, endpoint: str, timeout: float) -> bool:
    url = f"{base_url.rstrip('/')}{endpoint}"
    print(f"Checking health: {url}")
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Playwright: {data.get('playwright', {}).get('status')}")
            print(f"  LLM: {data.get('llm', {}).get('status')}")
            return data.get("status") == "ok"
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return False


def check_analyze(base_url: str, config: dict, timeout: float) -> bool:
    live = config.get("live_analyze", {})
    if not live.get("enabled"):
        print("Live analyze test skipped (disabled in config)")
        return True

    url = f"{base_url.rstrip('/')}/api/analyze"
    payload = {
        "url": live["url"],
        "vehicle": live["vehicle"],
    }
    print(f"Running live analyze: {live['url']}")
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            if response.status_code != 200:
                print(f"  FAILED: HTTP {response.status_code}")
                print(f"  {response.text[:500]}")
                return False
            data = response.json()
            print(f"  Product: {data.get('product', {}).get('name')}")
            print(f"  Compatible: {data.get('compatibility', {}).get('compatible')}")
            print(f"  Total time: {data.get('timings', {}).get('total_ms', 0):.0f} ms")
            return True
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Smoke test for product scanner")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--base-url", help="Override base URL")
    args = parser.parse_args()

    config = load_config(args.config)
    base_url = args.base_url or config.get("base_url", "http://localhost:8000")
    timeout = float(config.get("timeout_seconds", 30))

    print("=" * 50)
    print("Product Vehicle Compatibility Scanner - Smoke Test")
    print("=" * 50)

    results = []
    results.append(("Health check", check_health(base_url, config.get("health_endpoint", "/api/health"), timeout)))
    results.append(("Live analyze", check_analyze(base_url, config, timeout * 3)))

    print("\n" + "=" * 50)
    print("Results:")
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print("=" * 50)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
