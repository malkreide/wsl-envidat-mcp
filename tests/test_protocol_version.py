"""Der Protokoll-Pin muss die Revision nennen, die das SDK aushandelt.

`server.py` vergleicht `LATEST_PROTOCOL_VERSION` mit
`SUPPORTED_MCP_PROTOCOL_VERSION` und loggt bei Abweichung eine Warnung. Das ist
die richtige Beobachtung an der falschen Stelle: der Wert stand auf
`2025-11-25`, das SDK sprach `2026-07-28`, die Warnung feuerte bei jedem Start —
und nichts wurde davon rot. Eine Warnung im Log ist kein Gate.

Hier steht dieselbe Zusicherung als Test.
"""

from __future__ import annotations

import re

from mcp.types import LATEST_PROTOCOL_VERSION

from wsl_envidat_mcp.server import SUPPORTED_MCP_PROTOCOL_VERSION


def test_der_pin_nennt_die_revision_des_installierten_sdk() -> None:
    """Faellt, wenn ein SDK-Update die Protokollversion verschiebt.

    Die Loesung ist dann nicht, die Konstante blind nachzuziehen: erst das
    Spec-Changelog lesen, das Serververhalten pruefen, dann Konstante und
    `CHANGELOG.md` in einem Commit anheben.
    """
    assert SUPPORTED_MCP_PROTOCOL_VERSION == LATEST_PROTOCOL_VERSION, (
        f"gepinnt {SUPPORTED_MCP_PROTOCOL_VERSION}, das SDK handelt {LATEST_PROTOCOL_VERSION} aus"
    )


def test_der_pin_ist_ein_datum_und_kein_bewegliches_ziel() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", SUPPORTED_MCP_PROTOCOL_VERSION), (
        SUPPORTED_MCP_PROTOCOL_VERSION
    )
