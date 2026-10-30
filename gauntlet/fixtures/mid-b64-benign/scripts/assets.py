#!/usr/bin/env python3
"""Embedded release-notes template (plain text, encoded for transport)."""
import base64

TEMPLATE_B64 = "UkVMRUFTRSBOT1RFUyBURU1QTEFURS4gUHJvamVjdDogW25hbWVdLiBTdW1tYXJ5IG9mIGNoYW5nZXM6IFtzdW1tYXJ5XS4gTmV3IGZlYXR1cmVzOiBbbGlzdF0uIEZpeGVzOiBbbGlzdF0uIEtub3duIGlzc3VlczogW2xpc3RdLiBUaGFuayB5b3UgZm9yIHVwZGF0aW5nOyB0aGlzIHRlbXBsYXRlIHNoaXBzIGVtYmVkZGVkIGluIHRoZSBza2lsbCBzbyByZWxlYXNlIG5vdGVzIGNhbiBiZSBkcmFmdGVkIGZ1bGx5IG9mZmxpbmUu"


def template():
    return base64.b64decode(TEMPLATE_B64).decode()


if __name__ == "__main__":
    print(template())
