#!/usr/bin/env python3
"""Add GPLv3 license headers to Python source files."""

import pathlib
import sys

HEADER = '''# Copyright (C) 2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''


def has_license_header(content: str) -> bool:
    """Check if file already has a license header."""
    return "GNU General Public License" in content or "Copyright" in content


def add_header_to_file(filepath: pathlib.Path) -> bool:
    """Add license header to a Python file if it doesn't have one.
    
    Returns True if header was added, False if skipped.
    """
    content = filepath.read_text()
    
    if has_license_header(content):
        return False
    
    # Preserve shebang if present
    lines = content.split('\n')
    new_content = []
    
    if lines and lines[0].startswith('#!'):
        new_content.append(lines[0])
        new_content.append(HEADER)
        new_content.extend(lines[1:])
    else:
        new_content.append(HEADER)
        new_content.extend(lines)
    
    filepath.write_text('\n'.join(new_content))
    return True


def main():
    """Add headers to all Python files in src/ and tests/."""
    project_root = pathlib.Path(__file__).parent.parent
    
    # Find all Python files
    python_files = []
    for pattern in ['src/**/*.py', 'tests/**/*.py']:
        python_files.extend(project_root.glob(pattern))
    
    added_count = 0
    skipped_count = 0
    
    for filepath in python_files:
        if add_header_to_file(filepath):
            print(f"✅ Added header to {filepath.relative_to(project_root)}")
            added_count += 1
        else:
            print(f"⏭️  Skipped {filepath.relative_to(project_root)} (already has header)")
            skipped_count += 1
    
    print(f"\n✨ Summary: {added_count} headers added, {skipped_count} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
