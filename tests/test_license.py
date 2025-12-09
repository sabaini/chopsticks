# Copyright (C) 2024 Canonical Ltd.
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


"""Test suite to ensure GPLv3 license compliance."""

import pathlib


def test_license_file_exists():
    """Ensure LICENSE file exists in project root."""
    project_root = pathlib.Path(__file__).parent.parent
    license_file = project_root / "LICENSE"
    
    assert license_file.exists(), "LICENSE file must exist in project root"


def test_license_is_gplv3():
    """Ensure LICENSE file contains GPLv3 text."""
    project_root = pathlib.Path(__file__).parent.parent
    license_file = project_root / "LICENSE"
    
    content = license_file.read_text()
    
    # Check for GPLv3 markers
    assert "GNU GENERAL PUBLIC LICENSE" in content, "Must be GNU GPL"
    assert "Version 3, 29 June 2007" in content, "Must be GPL version 3"
    
    # Check for key GPL terms
    assert "copyleft" in content.lower(), "GPL is a copyleft license"
    assert "free software" in content.lower(), "Must reference free software"


def test_pyproject_declares_gplv3():
    """Ensure pyproject.toml declares GPL-3.0-or-later license."""
    project_root = pathlib.Path(__file__).parent.parent
    pyproject_file = project_root / "pyproject.toml"
    
    content = pyproject_file.read_text()
    
    assert 'license = {text = "GPL-3.0-or-later"}' in content, (
        "pyproject.toml must declare GPL-3.0-or-later license"
    )
