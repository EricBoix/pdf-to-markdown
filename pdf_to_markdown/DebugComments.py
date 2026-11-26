import os


class DebugComments:
    """Whether the markdown carries the html comments of the converter.

    These comments are not part of the text of the document, they tell what the
    converter did, for the human or the tool reading the markdown:

    - the page markers (see PageMarker): where each page starts;
    - the markdownlint guards, e.g. <!-- markdownlint-disable-line MD026 -->;
    - the converter notes, e.g. <!-- Converter note: picture removed -->.

    They are off by default. The environment variable ENV_VAR set to "1" switches
    them all on, so that a converter (its entrypoint, its tests) can be asked for
    them without being modified.
    """

    ENV_VAR = "PDF_TO_MARKDOWN_DEBUG_COMMENTS"

    @classmethod
    def enabled(cls) -> bool:
        return os.environ.get(cls.ENV_VAR) == "1"

    @classmethod
    def only_if_enabled(cls, comment: str) -> str:
        """The comment when the debug comments are on, else nothing."""
        return comment if cls.enabled() else ""
