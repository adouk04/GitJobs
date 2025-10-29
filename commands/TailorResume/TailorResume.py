from discord import app_commands, Interaction, Attachment
import pdfplumber, re, io
from parseData import ParseData
import discord
import resumeFormats
import asyncio
import time

class TailorResume:
    def __init__(self, tree: app_commands.CommandTree):
        if not tree:
            raise ValueError("No tree available, discord bot failed to run")
        self.tree = tree
        self._register()

    @staticmethod
    def extract_text_pdf(pdf_bytes: bytes) -> str:
        try:
            text_chunks = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    text_chunks.append(t)
            text = "\n".join(text_chunks)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            return text
        except Exception:
            return ""
        

    def _register(self):
        @self.tree.command(name="tailor_resume", description="Input a job link or job description to receive a tailored resume")
        async def tailor_resume(interaction: Interaction, file: Attachment, application_link: str):

            if not file.filename.lower().endswith(".pdf"):
                await interaction.response.send_message("Please upload a valid `.pdf` file.", ephemeral=True)
                return
        
            if file.size and file.size > 25 * 1024 * 1024:
                await interaction.response.send_message("File too large (>25MB).", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True, thinking=True)
            start_total = time.monotonic()

            await interaction.followup.send(f"Received `{file.filename}`. Extracting text…", ephemeral=True)
            t0 = time.monotonic()

            text = ""
            try:
                pdf_bytes = await file.read()
                text = TailorResume.extract_text_pdf(pdf_bytes)

                t1 = time.monotonic()
                print(f"[TIMER] PDF extraction: {t1 - t0:.2f}s")

                if not text.strip():
                    await interaction.followup.send(
                        "I couldn’t extract any text—this PDF may be image-only. Try an OCR’d PDF.",
                        ephemeral=True
                    )
                    return
                
                await interaction.followup.send(
                    f"Extracted ~{len(text)} characters. Tailoring now…", ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"Failed to parse the PDF: {e}", ephemeral=True)
                return

            RULES = r"""
            ROLE: Senior tech recruiter (20+ yrs) hiring SWE/SDE/Data interns. ATS-savvy (Workday, Greenhouse, Lever, Taleo, iCIMS).
            GOAL: Tailor the resume to the JD with maximal relevance.

            OUTPUT FORMAT (CRITICAL):
            - Return ONLY valid, compilable LaTeX starting with \documentclass
            - NO markdown code fences (no ```latex or ```)
            - NO explanatory text before or after the LaTeX
            - NO comments about changes made
            - Must include \begin{document} and \end{document}

            CONSTRAINTS:
            1) One page max. 
            2) Preserve ALL macros/structure from TEMPLATE. 
            3) No new tools/frameworks; stay factual.
            4) Bullets: action-verb, Google XYZ format (Accomplished X by doing Y resulting in Z)
            5) Optimize ATS keywords from JD (repeat key terms naturally)
            6) May reorder/reword for relevance; remove redundancy; prefer measurable impact.
            7) Do NOT change packages/geometry/fonts or add \usepackage lines.
            8) Escape LaTeX special chars: & % $ # _ { } ~ ^ \
            9) No extra whitespace at file start/end; no stray % lines; balanced braces.
            10) If space is tight, compress phrasing before dropping content; keep education + top skills.
            """


            prompt = f"""\
            {RULES}

            ========== TEMPLATE (PRESERVE STRUCTURE) ==========
            {resumeFormats.alex_format}

            ========== JOB DESCRIPTION (SOURCE KEYWORDS) ==========
            {application_link}

            ========== CURRENT RESUME (SOURCE CONTENT) ==========
            {text}

            ========== TASK ==========
            Generate ONE complete LaTeX document that:
            - Uses the TEMPLATE structure exactly
            - Incorporates content from RESUME
            - Optimizes for keywords in JOB DESCRIPTION
            - Follows all CONSTRAINTS above

            OUTPUT ONLY THE LATEX CODE. START WITH \\documentclass.
            """
            try:
                t2 = time.monotonic()

                pdf_path = await asyncio.to_thread(ParseData.parseResume, prompt)
                t3 = time.monotonic()
                print(f"[TIMER] parseResume (OpenAI + LaTeX): {t3 - t2:.2f}s")
                print(f"DEBUG: parseResume returned: {pdf_path}")
                total_time = time.monotonic() - start_total
                print(f"[TIMER] Total command runtime: {total_time:.2f}s")
                with open(pdf_path, "rb") as f:
                    await interaction.followup.send(
                        content="Here’s your tailored resume!",
                        file=discord.File(fp=io.BytesIO(f.read()), filename="Tailored_Resume.pdf"),
                        ephemeral=True
                    )
                        
            except Exception as e:
                await interaction.followup.send(
                content="Error: LaTeX failed to compile. Debug files saved locally.",
                ephemeral=True
            )