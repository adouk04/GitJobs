from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import os, re, shutil, subprocess, tempfile, time, logging



load_dotenv()
class ParseData:

    @staticmethod
    def get_pdflatex_path() -> Optional[str]:
        custom_path = os.getenv('PDFLATEX_PATH')
        if custom_path and os.path.exists(custom_path):
            return custom_path
        which = shutil.which('pdflatex')
        if which:
            return which
        paths = [
            "/Library/TeX/texbin/pdflatex",
            "/usr/local/texlive/2024/bin/x86_64-linux/pdflatex",
            "/usr/local/texlive/2023/bin/x86_64-linux/pdflatex",
            "/usr/local/bin/pdflatex",
            "/usr/bin/pdflatex",
        ]
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
            rc = subprocess.run([path, "--version"], capture_output=True)
            return rc.returncode == 0
        except Exception:
            return False
        
    @staticmethod
    def _strip_code_fences(latex: str) -> str:
        if latex is None:
            return ""
        text = latex.strip()
        m = re.match(r"^```[ \t]*([A-Za-z0-9_-]+)?\s*\n(.*)\n```[ \t]*$", text, flags=re.DOTALL)
        if m:
            return m.group(2).strip()
        m = re.match(r"^```[ \t]*([A-Za-z0-9_-]+)?[ \t]*(.*)```[ \t]*$", text, flags=re.DOTALL)
        if m:
            return m.group(2).strip()
        m = re.match(r"^```\s*\n(.*)\n```\s*$", text, flags=re.DOTALL)
        if m:
            return m.group(1).strip()
        return latex
    
    @staticmethod
    def parseResume(prompt):
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
            # instantiate OpenAI client at call-time so tests can patch OpenAI
            client = OpenAI()

            response = client.chat.completions.create(
                model="gpt-4",  # modern model
                # max_tokens can be omitted or set high if you expect long docs
                temperature=0.0,
                top_p=1.0,
                messages=[
                    {"role": "system", "content": (
                        "You are a professional resume editor who MUST output ONLY a complete, compilable LaTeX document. "
                        "The document MUST start with a \\documentclass declaration and include \\begin{document} and \\end{document}. "
                        "Do NOT include any explanation, analysis, code fences, markdown, or extra commentary — return only valid LaTeX source. "
                        "If you cannot produce a full document, return the word 'ERROR' only."
                    )},
                    {"role": "user", "content": prompt}
                ],
            )
            if hasattr(response, "usage"):
                u = response.usage
                logging.info(f"Prompt tokens={u.prompt_tokens}, Completion tokens={u.completion_tokens}, Total={u.total_tokens}")
                print(f"[OpenAI Tokens] prompt={u.prompt_tokens}, completion={u.completion_tokens}, total={u.total_tokens}")   
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")


        latex_content = ParseData._strip_code_fences(response.choices[0].message.content or "")
        if not (r"\begin{document}" in latex_content or r"\documentclass" in latex_content):
            logging.warning("Model returned fragment; wrapping into minimal LaTeX document.")
            latex_content = (
                "\\documentclass{article}\n"
                "\\usepackage[utf8]{inputenc}\n"
                "\\begin{document}\n"
                + latex_content +
                "\n\\end{document}\n"
            )
        
        pdflatex_path = ParseData.get_pdflatex_path()
        if not pdflatex_path:
            raise Exception("Could not find pdflatex executable. Please ensure LaTeX is installed.")
        
        LATEX_TIMEOUT = int(os.getenv("LATEX_TIMEOUT_SEC", "300"))  # per-run timeout (sec)

        # Compile LaTeX
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = os.path.join(temp_dir, "resume.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)
        
            try:
                for _ in range(3):
                    proc = subprocess.run(
                        [pdflatex_path, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-no-shell-escape", "resume.tex"],
                        cwd=temp_dir, capture_output=True, text=True, timeout=LATEX_TIMEOUT
                    )
                    if proc.returncode != 0:
                        log_path = os.path.join(temp_dir, "resume.log")
                        excerpt = ""
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                                lines = lf.readlines()
                            bang = [ln for ln in lines if ln.lstrip().startswith("!")]
                            excerpt = "".join(bang[:20]) or "".join(lines[-80:])
                        preview = (latex_content[:1000]).replace("\n", "\\n")
                        # try to persist debug
                        try:
                            ts = int(time.time())
                            failed_tex = os.path.abspath(f"failed_resume_{ts}.tex")
                            failed_log = os.path.abspath(f"failed_resume_{ts}.log")
                            shutil.copy(log_path, failed_log)
                            if os.path.exists(log_path):
                                shutil.copy(log_path, failed_log)
                        except Exception:
                            failed_tex = failed_log = "(debug save failed)"
                        raise Exception(
                            "LaTeX compilation failed.\n"
                            f"stderr:\n{proc.stderr}\n\n"
                            f"log (first errors):\n{excerpt or '(no error lines found)'}\n\n"
                            f"latex_preview(first 1000 chars):\n{preview}\n\n"
                            f"Saved debug files: {failed_tex}, {failed_log}\n"
                        )

                pdf_src = os.path.join(temp_dir, "resume.pdf")
                if not os.path.exists(pdf_src):
                    raise Exception("PDF was not generated. Check LaTeX packages/macros in the output.")
                output_filename = "Tailored_Resume.pdf"
                with open(pdf_src, "rb") as src, open(output_filename, "wb") as dst:
                    dst.write(src.read())
                return output_filename 

            except subprocess.TimeoutExpired:
                raise Exception("LaTeX compilation timed out. Consider increasing LATEX_TIMEOUT_SEC.")
            except Exception as e:
                raise Exception(f"Failed to generate PDF: {e}")