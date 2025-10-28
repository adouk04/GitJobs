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
import logging


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
                        "Do not include code fences, analysis, or markdown. "
                        "Use the provided LaTeX template structure and ensure it compiles."
                    )},
                    {"role": "user", "content": prompt}
                ],
                # max_tokens can be omitted or set high if you expect long docs
                temperature=0.2,
            )
            usage = response.usage
            logging.info(f"Prompt Resume Tailor tokens: {usage.prompt_tokens}, Completion tokens: {usage.completion_tokens}, Total: {usage.total_tokens}")

            # You can also print it for Cloud Run logs
            print(f"[OpenAI Tokens] Resume Tailor prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
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
            
            LATEX_TIMEOUT = int(os.getenv("LATEX_TIMEOUT_SEC", "300"))  # per-run timeout (sec)

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
                        timeout=LATEX_TIMEOUT  # prevent hanging
                    )
                    if result.returncode != 0:
                        # Surface the most useful error lines
                        log_path = os.path.join(temp_dir, "resume.log")
                        excerpt = ""
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                                lines = lf.readlines()
                            bang = [ln for ln in lines if ln.lstrip().startswith("!")]
                            excerpt = "".join(bang[:20]) or "".join(lines[-80:])  # fallback: last lines
                        raise Exception(
                            "LaTeX compilation failed.\n"
                            f"stderr:\n{result.stderr}\n\n"
                            f"log (first errors):\n{excerpt or '(no error lines found)'}"
                        )

                # success: return/move PDF
                temp_pdf = os.path.join(temp_dir, "resume.pdf")
                if not os.path.exists(temp_pdf):
                    raise Exception("PDF was not generated. Check LaTeX packages/macros in the output.")
                output_filename = "Tailored_Resume.pdf"
                with open(temp_pdf, "rb") as src, open(output_filename, "wb") as dst:
                    dst.write(src.read())
                return output_filename, latex_content

            except subprocess.TimeoutExpired:
                # Include a bit of the log to help diagnose slow/looping compiles
                log_path = os.path.join(temp_dir, "resume.log")
                tail = ""
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                        tail = "".join(lf.readlines()[-120:])
                raise Exception(
                    "LaTeX compilation timed out. Consider increasing LATEX_TIMEOUT_SEC or simplifying the template.\n"
                    f"Log tail:\n{tail}"
                )

    @staticmethod
    def summarize_changes(original_text: str, tailored_latex: str) -> str:
        """
        Ask the model to summarize changes between original resume text and
        tailored LaTeX output. Returns a markdown string (<= 1800 chars if possible).
        """
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert technical recruiter. "
                            "Summarize the precise edits made to a resume. "
                            "Output concise **Markdown** only. "
                            "Prefer short bullets with action verbs and measurable outcomes."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            "Original resume text:\n"
                            "-----\n"
                            f"{original_text}\n"
                            "-----\n\n"
                            "Tailored LaTeX output (resume body; ignore LaTeX boilerplate):\n"
                            "-----\n"
                            f"{tailored_latex}\n"
                            "-----\n\n"
                            "Return:\n"
                            "1) **Top 3 improvements** (ATS or clarity/impact) as bullets\n"
                            "2) **Changed phrases**: a short list of before → after pairs (3–6 items)\n"
                            "3) **Keywords surfaced**: comma-separated\n"
                            "Keep under ~1800 characters."
                        )
                    }
                ],
            )
            usage = res.usage
            logging.info(f"Summary Prompt tokens: {usage.prompt_tokens}, Completion tokens: {usage.completion_tokens}, Total: {usage.total_tokens}")

            # You can also print it for Cloud Run logs
            print(f"[OpenAI Tokens] Summary prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
            md = res.choices[0].message.content or "No change summary produced."
            return md.strip()
        except Exception as e:
            return f"Could not produce change summary: {e}"
    @staticmethod
    def _strip_code_fences(latex: str) -> str:
        """Ensure the LaTeX content is valid by adding missing document tags."""
        m = re.search(r"```(?:latex)?\s*(.*?)```", latex, re.DOTALL | re.IGNORECASE)
        content = m.group(1).strip() if m else latex.strip()
        
        # Ensure \begin{document} and \end{document} are present
        if not re.search(r"\\begin\{document\}", content):
            content = "\\begin{document}\n" + content
        if not re.search(r"\\end\{document\}", content):
            content += "\n\\end{document}"
        
        return content