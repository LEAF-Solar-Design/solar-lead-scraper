#!/usr/bin/env python3
"""
Patch camoufox to use GITHUB_TOKEN environment variable.

This works around the rate limiting issue when fetching releases from GitHub.
See: https://github.com/daijro/camoufox/issues/285

Once camoufox releases a version with PR #351 merged, this patch can be removed.
"""

import os
import site


def patch_camoufox():
    """Find and patch camoufox pkgman.py to use GITHUB_TOKEN."""
    search_paths = site.getsitepackages()
    try:
        search_paths.append(site.getusersitepackages())
    except AttributeError:
        pass

    for sp in search_paths:
        pkgman = os.path.join(sp, "camoufox", "pkgman.py")
        if os.path.exists(pkgman):
            with open(pkgman, "r") as f:
                content = f.read()

            # Check if already patched
            if "GITHUB_TOKEN" in content:
                print(f"Already patched: {pkgman}")
                return True

            # Add GITHUB_TOKEN support to the headers
            old = 'headers = {"Accept": "application/vnd.github.v3+json"}'
            new = '''headers = {"Accept": "application/vnd.github.v3+json"}
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"'''

            if old in content:
                content = content.replace(old, new)
                with open(pkgman, "w") as f:
                    f.write(content)
                print(f"Patched GITHUB_TOKEN support into: {pkgman}")
                return True
            else:
                print(f"Could not find headers line to patch in: {pkgman}")
                return False

    print("Warning: Could not find camoufox pkgman.py to patch")
    return False


if __name__ == "__main__":
    patch_camoufox()
