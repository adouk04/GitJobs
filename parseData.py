from typing import Optional
import re
import shutil
import os
import os
import subprocess
import tempfile
import shutil
import re
from dotenv import load_dotenv
from openai import OpenAI
import discord

load_dotenv()
client = OpenAI()

class ParseData:
    def __init__(self, resume, prompt):
        if not resume:
            raise ValueError("No file attached — please upload a PDF resume")
        if not prompt:
            raise ValueError("No prompt returned, check TailorResume.py")
        self.resume = resume
        self.prompt = prompt

    @staticmethod
    def get_pdflatex_path() -> Optional[str]:
        """Locate pdflatex with env override, PATH probe, and common install dirs."""
        # 1) Env override
        custom_path = os.getenv('PDFLATEX_PATH')
        if custom_path and os.path.exists(custom_path):
            return custom_path

        # 2) PATH
        which = shutil.which('pdflatex')
        if which:
            return which

        # 3) Common paths
        paths = []
        if os.name == 'nt':  # Windows
            paths.extend([
                os.path.expandvars(r'%ProgramFiles%\MiKTeX\miktex\bin\x64\pdflatex.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\MiKTeX\miktex\bin\pdflatex.exe'),
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'),
                os.path.expandvars(r'%USERPROFILE%\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'),
            ])
        else:  # macOS/Linux
            paths.extend([
                '/Library/TeX/texbin/pdflatex',     # MacTeX
                '/usr/local/texlive/2024/bin/x86_64-linux/pdflatex',
                '/usr/local/texlive/2023/bin/x86_64-linux/pdflatex',
                '/usr/local/bin/pdflatex',
                '/usr/bin/pdflatex',
            ])
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def check_latex_installed() -> bool:
        path = ParseData.get_pdflatex_path()
        if not path:
            return False
        try:
            subprocess.run([path, "--version"], capture_output=True, text=True, check=True)
            return True
        except Exception:
            return False

    @staticmethod
    def _strip_code_fences(latex: str) -> str:
        """Remove ```...``` fences if the model returned them."""
        m = re.search(r"```(?:latex)?\s*(.*?)```", latex, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else latex

    @staticmethod
    def parseResume(resume, prompt):
        # Ensure LaTeX present
        if not ParseData.check_latex_installed():
            raise Exception(
                "LaTeX (pdflatex) not found.\n"
                "- Windows: install MiKTeX (https://miktex.org/download) or `winget install MiKTeX.MiKTeX`\n"
                "- macOS: install MacTeX (https://tug.org/mactex/)\n"
                "- Linux: install TeX Live (e.g., `sudo apt install texlive-full`)."
            )

        # Call OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-4o",  # modern model
                messages=[
                    {"role": "system", "content": (
                        "You are a professional resume editor who outputs ONLY valid LaTeX. "
                        "Do not include code fences. Preserve the LaTeX structure exactly as provided."
                    )},
                    {"role": "user", "content": prompt}
                ],
                # max_tokens can be omitted or set high if you expect long docs
                temperature=0.2,
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

        latex_content = response.choices[0].message.content or ""
        latex_content = ParseData._strip_code_fences(latex_content)

        pdflatex_path = ParseData.get_pdflatex_path()
        if not pdflatex_path:
            raise Exception("Could not find pdflatex executable. Please ensure LaTeX is installed.")

        # Compile LaTeX
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = os.path.join(temp_dir, "resume.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            try:
                # Run pdflatex 2–3 times; include safe flags and a timeout
                for i in range(3):
                    result = subprocess.run(
                        [
                            pdflatex_path,
                            "-interaction=nonstopmode",
                            "-halt-on-error",
                            "-file-line-error",
                            "-no-shell-escape",
                            "resume.tex"  # use basename since cwd=temp_dir
                        ],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=60  # prevent hanging
                    )
                    if result.returncode != 0:
                        # Surface the most useful error lines
                        log_path = os.path.join(temp_dir, "resume.log")
                        excerpt = ""
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                                lines = lf.readlines()
                            bang_lines = [ln for ln in lines if ln.lstrip().startswith("!")]
                            excerpt = "".join(bang_lines[:10])
                        raise Exception(
                            "LaTeX compilation failed.\n"
                            f"stderr:\n{result.stderr}\n\n"
                            f"log (first errors):\n{excerpt or '(no error lines found)'}"
                        )

                temp_pdf = os.path.join(temp_dir, "resume.pdf")
                if not os.path.exists(temp_pdf):
                    raise Exception("PDF was not generated. Check LaTeX packages/macros in the output.")
                output_filename = "Tailored_Resume.pdf"
                with open(temp_pdf, "rb") as src, open(output_filename, "wb") as dst:
                    dst.write(src.read())
                return output_filename

            except subprocess.TimeoutExpired:
                raise Exception("LaTeX compilation timed out. Check for infinite loops or very large includes.")
            except Exception as e:
                raise Exception(f"Failed to generate PDF: {e}")
