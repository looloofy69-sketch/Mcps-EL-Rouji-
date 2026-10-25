#!/usr/bin/env python3
"""Manually invoked, read-only smoke check for the registered EL-Rouji health tool."""
from __future__ import annotations

import asyncio
import json
import sys

from el_rouji_mcp import server


def main() -> int:
    try:
        result = json.loads(asyncio.run(server.el_rouji_health()))
    except Exception as exc:  # Do not print transport details or arbitrary exception text in CI logs.
        print(f"EL-Rouji health smoke failed ({type(exc).__name__}).")
        return 1

    health = result.get("health")
    if (
        result.get("reachable") is True
        and isinstance(health, dict)
        and health.get("ok") is True
        and health.get("service") == "core-assistant"
    ):
        print("EL-Rouji health smoke passed: the configured read-only health tool reached core-assistant.")
        return 0

    print("EL-Rouji health smoke failed: the configured endpoint did not report a healthy core-assistant.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
