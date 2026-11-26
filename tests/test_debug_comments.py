"""The html comments of the converter are written only when asked for."""

from pdf_to_markdown import DebugComments, NumberedListAnnotator
from pdf_to_markdown.Model import DocumentHierarchicalLevel

MD026_GUARD = "<!-- markdownlint-disable-line MD026 -->"


class TestDebugComments:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv(DebugComments.ENV_VAR, raising=False)
        assert not DebugComments.enabled()
        assert DebugComments.only_if_enabled("<!-- a -->") == ""

    def test_on_with_the_environment_variable(self, monkeypatch):
        monkeypatch.setenv(DebugComments.ENV_VAR, "1")
        assert DebugComments.enabled()
        assert DebugComments.only_if_enabled("<!-- a -->") == "<!-- a -->"

    def test_any_other_value_is_off(self, monkeypatch):
        monkeypatch.setenv(DebugComments.ENV_VAR, "0")
        assert not DebugComments.enabled()


class TestEveryCommentFollowsTheSwitch:
    def test_markdownlint_guard(self, monkeypatch):
        monkeypatch.delenv(DebugComments.ENV_VAR, raising=False)
        assert DocumentHierarchicalLevel.get_header_line("What?!", 2) == "## What?!"
        monkeypatch.setenv(DebugComments.ENV_VAR, "1")
        assert (
            DocumentHierarchicalLevel.get_header_line("Stop.", 2)
            == "## Stop." + MD026_GUARD
        )

    def test_converter_note(self, monkeypatch):
        monkeypatch.delenv(DebugComments.ENV_VAR, raising=False)
        assert NumberedListAnnotator.failure_suffix() == ""
        monkeypatch.setenv(DebugComments.ENV_VAR, "1")
        assert "Converter note" in NumberedListAnnotator.failure_suffix()
