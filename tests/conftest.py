# justifactu - Automated billing justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra, David Romero San Millán (DavidRomeroICIQ)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from pathlib import Path

import pytest
from pypdf import PdfWriter

# Add project root to PYTHONPATH dynamically
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def create_blank_pdf(path: Path) -> None:
    """Creates a minimal blank PDF file at the given path."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """Returns the path to a minimal blank PDF."""
    pdf_path = tmp_path / "blank.pdf"
    create_blank_pdf(pdf_path)
    return pdf_path


@pytest.fixture
def billing_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Creates bills, payments, and output directories under tmp_path."""
    bills_dir = tmp_path / "FACTURES"
    payments_dir = tmp_path / "Remeses"
    output_dir = tmp_path / "output"
    bills_dir.mkdir()
    payments_dir.mkdir()
    return bills_dir, payments_dir, output_dir
