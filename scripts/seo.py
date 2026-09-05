"""Shared constants for the generated pages.

`SITE_URL` is the one thing that must be right before publishing: canonical
tags, the sitemap and the Open Graph tags are all built from it, and a canonical
pointing at the wrong host is worse than none at all. Change it here, rebuild,
and every page follows.
"""

from __future__ import annotations

import re

SITE_URL = "https://mdhrshohel.github.io/bd-bank-routing"
REPO_URL = "https://github.com/MdHRShohel/bd-bank-routing"

AUTHOR_NAME = "Md. Habibur Rahman Shohel"
AUTHOR_SITE = "https://shohel.bro.bd"
AUTHOR_GITHUB = "https://github.com/MdHRShohel"

#: What the site calls itself to people and to crawlers. The package and
#: repository keep the install-name spelling, `bd-bank-routing`.
SITE_NAME = "BD Bank Routing"


def slugify(name: str) -> str:
    """A stable, readable URL segment for a bank name.

    Kept boring on purpose: these become permanent URLs, and a slug that shifts
    when a bank's stored name is tidied up breaks every link anyone shared.
    """
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
