import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

import unittest
from unittest.mock import Mock, patch, MagicMock
from parseData import ParseData
from commands.TailorResume.TailorResume import TailorResume

class TestResumeBot(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        # Create a mock PDF content for testing
        self.test_pdf_content = b"%PDF-1.4 Test PDF content"
        self.mock_resume_text = "Software Engineer\nPython, JavaScript\nProject Experience"
        self.mock_job_description = "Looking for a Software Engineer with Python experience"

    def test_parse_data_initialization(self):
        """Test ParseData class initialization"""
        # Test valid initialization
        parser = ParseData(resume="test.pdf", prompt="test prompt")
        self.assertEqual(parser.resume, "test.pdf")
        self.assertEqual(parser.prompt, "test prompt")

        # Test invalid initialization
        with self.assertRaises(ValueError):
            ParseData(resume=None, prompt="test prompt")
        with self.assertRaises(ValueError):
            ParseData(resume="test.pdf", prompt=None)

    @patch('pdfplumber.open')
    def test_pdf_text_extraction(self, mock_pdf_open):
        """Test PDF text extraction functionality"""
        # Mock PDF content
        mock_page = MagicMock()
        mock_page.extract_text.return_value = self.mock_resume_text
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        # Test extraction
        result = TailorResume.extract_text_pdf(self.test_pdf_content)
        self.assertIn("Software Engineer", result)
        self.assertIn("Python", result)

    def test_openai_integration(self):
        """Test OpenAI API integration"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        with patch('openai.OpenAI') as mock_openai_class:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_openai
            
            with patch('parseData.ParseData.check_latex_installed', return_value=True):
                with patch('tempfile.TemporaryDirectory') as mock_temp_dir:
                    mock_temp_dir.return_value.__enter__.return_value = '/fake/temp/dir'
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value.returncode = 0
                        with patch('os.path.exists', return_value=True):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__.return_value.read.return_value = b'fake pdf content'
                                try:
                                    output_file, latex_content = ParseData.parseResume(self.mock_resume_text, "test prompt")
                                    self.assertTrue(latex_content.startswith("\\documentclass"))
                                    self.assertIsInstance(output_file, str)
                                except Exception as e:
                                    self.fail(f"ParseResume raised unexpected exception: {e}")

    def test_latex_installation_check(self):
        """Test LaTeX installation checker"""
        # Test when LaTeX is not installed
        with patch('parseData.ParseData.get_pdflatex_path', return_value=None):
            self.assertFalse(ParseData.check_latex_installed())

        # Test when LaTeX is installed
        with patch('parseData.ParseData.get_pdflatex_path', return_value='/usr/bin/pdflatex'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                self.assertTrue(ParseData.check_latex_installed())

    def test_latex_compilation(self):
        """Test LaTeX compilation process"""
        test_latex = r"""
        \documentclass{article}
        \begin{document}
        Test document
        \end{document}
        """
        
        with patch('parseData.ParseData.check_latex_installed', return_value=True):
            with patch('tempfile.TemporaryDirectory') as mock_temp_dir:
                mock_temp_dir.return_value.__enter__.return_value = '/fake/temp/dir'
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = b'fake pdf content'
                            try:
                                output_file, latex_content = ParseData.parseResume(self.mock_resume_text, "test prompt")
                                self.assertIsInstance(output_file, str)
                                self.assertIsInstance(latex_content, str)
                            except Exception as e:
                                self.fail(f"LaTeX compilation failed: {e}")

    def test_strip_code_fences(self):
        """Test code fence stripping functionality"""
        test_cases = [
            ("```latex\n\\test\n```", "\\test"),
            ("```\n\\test\n```", "\\test"),
            ("\\test", "\\test"),  # No fences
            ("```latex\n\\test", "```latex\n\\test")  # Incomplete fences
        ]
        
        for input_text, expected in test_cases:
            result = ParseData._strip_code_fences(input_text)
            self.assertEqual(result.strip(), expected.strip())

if __name__ == '__main__':
    unittest.main()