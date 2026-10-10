```python
"""
U.S. Nonfarm Payrolls (NFP) release dates
from September 2025 through October 2026.

Based on the official release schedule published by the
U.S. Bureau of Labor Statistics (BLS).

Due to the 2025 federal government shutdown, no separate
Employment Situation report was published for October 2025.
September 2025 data was released on November 20, 2025.
October establishment-survey data was incorporated into
the November 2025 report, released on December 16, 2025.
"""

# (Release date, reference month, notes)
NFP_RELEASES = [
    ("2025-09-05", "August 2025", ""),
    ("2025-11-20", "September 2025", "Delayed due to government shutdown"),
    ("2025-12-16", "October-November 2025", "October data affected by government shutdown"),
    ("2026-01-09", "December 2025", ""),
    ("2026-02-11", "January 2026", "Delayed release"),
    ("2026-03-06", "February 2026", ""),
    ("2026-04-03", "March 2026", "Good Friday; market data availability may be limited"),
    ("2026-05-08", "April 2026", "Released on the second Friday"),
    ("2026-06-05", "May 2026", ""),
    ("2026-07-02", "June 2026", "Released on Thursday before Independence Day"),
    ("2026-08-07", "July 2026", ""),
    ("2026-09-04", "August 2026", ""),
    ("2026-10-02", "September 2026", ""),
]

# Release time: 8:30 AM Eastern Time.
# ZoneInfo automatically handles daylight saving time.
RELEASE_TIME_ET = (8, 30)
```