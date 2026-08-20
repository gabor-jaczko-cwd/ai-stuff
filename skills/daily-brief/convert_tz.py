#!/usr/bin/env python3
"""Convert a batch of (dateTime, timeZone) pairs into a display timezone.

Usage: convert_tz.py <display_tz> <dateTime_1> <timeZone_1> [<dateTime_2> <timeZone_2> ...]
Prints one HH:MM per pair, in input order.
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

args = sys.argv[1:]
display_tz = ZoneInfo(args[0])
pairs = args[1:]
for raw, src_tz in zip(pairs[0::2], pairs[1::2]):
    converted = datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo(src_tz)).astimezone(display_tz)
    print(converted.strftime("%H:%M"))
