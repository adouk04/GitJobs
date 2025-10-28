import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# -------------------------------------------------------
# Make project importable and install lightweight fakes
# -------------------------------------------------------
sys.path.append(str(Path(__file__).parent.parent))

# Fake 'openai' so imports don't require the real package
fake_openai = types.ModuleType("openai")
def _fake_openai_ctor(*args, **kwargs):
    class _Fake:
        pass
    return _Fake()
fake_openai.OpenAI = _fake_openai_ctor
sys.modules['openai'] = fake_openai

# Fake 'discord' to satisfy TailorResume imports
fake_discord = types.ModuleType("discord")
fake_discord.app_commands = types.ModuleType("app_commands")
fake_discord.app_commands.CommandTree = lambda *a, **k: None
fake_discord.Interaction = object
fake_discord.Attachment = object
fake_discord.File = lambda *a, **k: None
sys.modules['discord'] = fake_discord

# Fake resumeFormats
fake_resumeFormats = types.ModuleType("resumeFormats")
fake_resumeFormats.alex_format = r"% Dummy latex template"
sys.modules['resumeFormats'] = fake_resumeFormats

# Now import SUT
from parseData import ParseData

# -------------------------------------------------------
# Test Suite
# -------------------------------------------------------
class TestResumeBot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_resume_text = "Software Engineer\nPython, JavaScript\nProject Experience"
        cls.mock_job_description = "Looking for a Software Engineer with Python experience"
        cls.sample_latex_doc = (
            "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        )
        cls.test_pdf_bytes = b"%PDF-1.4 mock content"

    # ---------------------------
    # Helpers
    # ---------------------------
    def _patch_pdfplumber_with_text(self, text):
        """Install a fake pdfplumber that extracts `text` from one page."""
        import types as _types, sys as _sys
        fake_pdfplumber = _types.ModuleType('pdfplumber')

        def fake_open(_stream_or_path, *a, **k):
            class CM:
                def __enter__(self_inner):
                    page = MagicMock()
                    page.extract_text.return_value = text
                    pdf = MagicMock()
                    pdf.pages = [page]
                    return pdf
                def __exit__(self_inner, exc_type, exc, tb):
                    return False
            return CM()

        fake_pdfplumber.open = fake_open
        _sys.modules['pdfplumber'] = fake_pdfplumber

    def _patch_pdfplumber_to_raise(self, exc=ValueError("bad pdf")):
        """Install a pdfplumber that raises on open."""
        import types as _types, sys as _sys
        fake_pdfplumber = _types.ModuleType('pdfplumber')

        def fake_open(_stream_or_path, *a, **k):
            raise exc

        fake_pdfplumber.open = fake_open
        _sys.modules['pdfplumber'] = fake_pdfplumber

    def _mock_openai_returning(self, content, usage=(48, 224, 272)):
        """Patch openai.OpenAI.chat.completions.create to return `content`."""
        prompt_t, comp_t, total_t = usage
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        # usage is optional in runtime; keep it but don't assert hard
        mock_response.usage.prompt_tokens = prompt_t
        mock_response.usage.completion_tokens = comp_t
        mock_response.usage.total_tokens = total_t

        openai_patcher = patch('openai.OpenAI')
        mock_openai_class = openai_patcher.start()
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai
        self.addCleanup(openai_patcher.stop)
        return mock_openai

    # ---------------------------
    # ParseData initialization
    # ---------------------------
    def test_parse_data_initialization_valid(self):
        parser = ParseData(resume="resume.pdf", prompt="prompt")
        self.assertEqual(parser.resume, "resume.pdf")
        self.assertEqual(parser.prompt, "prompt")

    def test_parse_data_initialization_invalid(self):
        with self.assertRaises(ValueError):
            ParseData(resume=None, prompt="x")
        with self.assertRaises(ValueError):
            ParseData(resume="resume.pdf", prompt=None)
        # Empty strings should also error (defensive)
        with self.assertRaises(ValueError):
            ParseData(resume="", prompt="x")
        with self.assertRaises(ValueError):
            ParseData(resume="resume.pdf", prompt="")

    # ---------------------------
    # PDF extraction (TailorResume)
    # ---------------------------

    def test_pdf_text_extraction_handles_pdfplumber_errors(self):
        # Arrange
        self._patch_pdfplumber_to_raise(RuntimeError("cannot open"))
        from commands.TailorResume.TailorResume import TailorResume

        # Act/Assert: Function should not crash; allow either empty str or graceful handling
        try:
            out = TailorResume.extract_text_pdf(self.test_pdf_bytes)
            self.assertIsInstance(out, str)
        except Exception as e:
            self.fail(f"extract_text_pdf raised unexpected exception: {e}")

    # ---------------------------
    # LaTeX installation checks
    # ---------------------------
    def test_latex_installation_check_not_found(self):
        with patch('parseData.ParseData.get_pdflatex_path', return_value=None):
            self.assertFalse(ParseData.check_latex_installed())

    def test_latex_installation_check_found_and_version_ok(self):
        with patch('parseData.ParseData.get_pdflatex_path', return_value='/usr/bin/pdflatex'):
            with patch('subprocess.run') as mrun:
                mrun.return_value.returncode = 0
                self.assertTrue(ParseData.check_latex_installed())
                # Ensure we actually tried '--version'
                mrun.assert_called()

    def test_latex_installation_check_found_but_version_fails(self):
        with patch('parseData.ParseData.get_pdflatex_path', return_value='/usr/bin/pdflatex'):
            with patch('subprocess.run') as mrun:
                mrun.return_value.returncode = 1
                self.assertFalse(ParseData.check_latex_installed())

    # ---------------------------
    # parseResume success path (happy)
    # ---------------------------
    def test_openai_integration_and_compile_success(self):
        self._mock_openai_returning(self.sample_latex_doc)
        with patch('parseData.ParseData.check_latex_installed', return_value=True):
            with patch('tempfile.TemporaryDirectory') as mtmp:
                mtmp.return_value.__enter__.return_value = '/fake/temp/dir'
                with patch('subprocess.run') as mrun:
                    mrun.return_value.returncode = 0
                    with patch('os.path.exists', return_value=True):
                        # simulate reading compiled PDF
                        with patch('builtins.open', create=True) as mopen:
                            mopen.return_value.__enter__.return_value.read.return_value = b'%PDF'
                            try:
                                out_file, latex = ParseData.parseResume(
                                    "My resume text", "test prompt"
                                )
                                self.assertTrue(latex.strip().startswith("\\documentclass"))
                                self.assertIsInstance(out_file, str)
                            except Exception as e:
                                self.fail(f"parseResume raised unexpectedly: {e}")

    # ---------------------------
    # parseResume: model returns fragment -> wrapper added
    # ---------------------------
    def test_model_fragment_handling_wraps_into_document(self):
        fragment = "Original Resume Text | Tailored Resume Text |"
        self._mock_openai_returning(fragment)
        with patch('parseData.ParseData.check_latex_installed', return_value=True):
            with patch('tempfile.TemporaryDirectory') as mtmp:
                mtmp.return_value.__enter__.return_value = '/fake/temp/dir'
                with patch('subprocess.run') as mrun:
                    mrun.return_value.returncode = 0
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mopen:
                            mopen.return_value.__enter__.return_value.read.return_value = b'%PDF'
                            out_file, latex = ParseData.parseResume(
                                "resume text", "prompt"
                            )
                            self.assertTrue(latex.strip().startswith("\\documentclass"))
                            self.assertIn("Original Resume Text", latex)

    # ---------------------------
    # parseResume: error paths
    # ---------------------------
    def test_openai_call_raises_propagates(self):
        # Make OpenAI raise
        with patch('openai.OpenAI') as mclass:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("OpenAI down")
            mclass.return_value = mock_client

            with patch('parseData.ParseData.check_latex_installed', return_value=True):
                with self.assertRaises(Exception):
                    ParseData.parseResume("resume", "prompt")

    def test_latex_compile_failure_raises(self):
        self._mock_openai_returning(self.sample_latex_doc)
        with patch('parseData.ParseData.check_latex_installed', return_value=True):
            with patch('tempfile.TemporaryDirectory') as mtmp:
                mtmp.return_value.__enter__.return_value = '/fake/temp/dir'
                with patch('subprocess.run') as mrun:
                    mrun.return_value.returncode = 1  # pdflatex error
                    with self.assertRaises(Exception):
                        ParseData.parseResume("resume", "prompt")

    def test_pdf_missing_after_compile_raises(self):
        self._mock_openai_returning(self.sample_latex_doc)
        with patch('parseData.ParseData.check_latex_installed', return_value=True):
            with patch('tempfile.TemporaryDirectory') as mtmp:
                mtmp.return_value.__enter__.return_value = '/fake/temp/dir'
                with patch('subprocess.run') as mrun:
                    mrun.return_value.returncode = 0
                    with patch('os.path.exists', return_value=False):
                        with self.assertRaises(Exception):
                            ParseData.parseResume("resume", "prompt")

    # ---------------------------
    # Code-fence stripping
    # ---------------------------
    def test_strip_code_fences_variants(self):
        cases = [
            ("```latex\n\\x\n```", "\\x"),
            ("```\n\\x\n```", "\\x"),
            ("```tex\n\\x\n```", "\\x"),
            ("```LaTeX\n\\x\n```", "\\x"),
            ("   ```latex\n\\x\n```\n  ", "\\x"),
            ("\\x", "\\x"),  # no fences
            ("```latex\n\\x", "```latex\n\\x"),  # incomplete -> unchanged
            ("```latex\n\\a\n\\b\n```\n", "\\a\n\\b"),
            ("```random\n\\x\n```", "\\x"),
        ]
        for src, exp in cases:
            with self.subTest(src=src):
                self.assertEqual(ParseData._strip_code_fences(src).strip(), exp.strip())


if __name__ == '__main__':
    unittest.main()
