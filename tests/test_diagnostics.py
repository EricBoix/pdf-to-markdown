"""Tests for the diagnostics channel of the package.

All diagnostics go through the standard `logging` module, using the logger
named "pdf_to_markdown". The package never prints, except for the report
oriented module Traces.py.
"""

import logging
import pathlib

import pdf_to_markdown
from pdf_to_markdown import SinglePatternSplitter
from pdf_to_markdown.DiagnosticsReporter import DiagnosticsReporter

LOGGER_NAME = "pdf_to_markdown"


class TestDiagnosticsReporter:
    def test_warn_emits_warning_record(self, caplog):
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            DiagnosticsReporter().warn("something is odd")
        assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
            (logging.WARNING, "something is odd")
        ]

    def test_debug_emits_debug_record(self, caplog):
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            DiagnosticsReporter().debug("some trace")
        assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
            (logging.DEBUG, "some trace")
        ]

    def test_debug_hidden_at_warning_level(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            DiagnosticsReporter().debug("some trace")
        assert caplog.records == []

    def test_package_logger_is_silent_by_default(self):
        handlers = logging.getLogger(LOGGER_NAME).handlers
        assert any(isinstance(handler, logging.NullHandler) for handler in handlers)


class TestModelWarningsUseLogging:
    def test_splitter_warning_is_a_log_record(self, caplog):
        splitter = SinglePatternSplitter(r"\n## ", r"## (.+)\n")
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            splitter.get_sublevel_name("plain text with no heading")
        assert "Sublevel name not found." in caplog.text


class TestNoLoosePrint:
    def test_no_print_outside_traces(self):
        package_directory = pathlib.Path(pdf_to_markdown.__file__).parent
        offenders = [
            source_file.name
            for source_file in package_directory.glob("*.py")
            if source_file.name != "Traces.py"
            and "print(" in source_file.read_text(encoding="utf-8")
        ]
        assert offenders == []
