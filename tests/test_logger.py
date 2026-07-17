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

from justifactu.logger import configure_logging_from_settings, get_logger


def test_qa_report_captures_tagged_records_at_any_level(tmp_path):
    qa_report_path = tmp_path / "qa_report.log"
    configure_logging_from_settings(qa_files_log_file=qa_report_path)
    log = get_logger("test_qa_report")

    log.warning("tagged warning", extra={"qa_report": True})
    log.error("tagged error", extra={"qa_report": True})
    log.error("untagged error")

    content = qa_report_path.read_text()
    assert "tagged warning" in content
    assert "tagged error" in content
    assert "untagged error" not in content
