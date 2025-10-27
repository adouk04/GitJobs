from discord import app_commands, Interaction, Attachment
import pdfplumber, re, io
from parseData import ParseData
import discord
import resumeFormats
import asyncio

class TailorResume:
    def __init__(self, tree: app_commands.CommandTree):
        if not tree:
            raise ValueError("No tree available, discord bot failed to run")
        self.tree = tree
        self._register()

    def _register(self):
        @self.tree.command(name="tailor_resume", description="tailors resume for user")
        async def tailor_resume(interaction: Interaction, file: Attachment, job_description: str):
            # 1) Acknowledge ONCE
            await interaction.response.defer(ephemeral=True, thinking=True)

            # 2) All messages after defer -> followup.send
            if not file.filename.lower().endswith(".pdf"):
                await interaction.followup.send("Please upload a valid `.pdf` file.", ephemeral=True)
                return

            if file.size > 25 * 1024 * 1024:
                await interaction.followup.send("File too large! Please upload a file smaller than 25MB.", ephemeral=True)
                return

            await interaction.followup.send(f"Received `{file.filename}`. Extracting text…", ephemeral=True)

            # 3) Extract text (ensure `text` defined on error paths)
            text = ""
            try:
                pdf_bytes = await file.read()
                text = extract_text_pdf(pdf_bytes)
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

            # 4) Build prompt & generate PDF
            prompt = f"""
            Act as a **Senior Technical Recruiter (20+ yrs)** experienced in hiring **Software Engineers** at top tech firms.
            You are an expert at using **ATS (Workday, Lever, Greenhouse, Taleo, iCIMS)** to evaluate resumes for 
            **SWE, SDE Intern, and Data/Systems** roles.

            ---

            ### Stage 1 — Job Description Analysis
            From the job description below, extract:
            - **Top 3 responsibilities**
            - **Top 5 ATS keywords** (focus on SWE-relevant terms like data structures, algorithms, debugging, scalability, APIs, testing, collaboration).

            ---

            ### Stage 2 — Resume Tailoring
            Then tailor the provided resume to align with those responsibilities and keywords.

            Guidelines:
            - Use **action verbs + quantifiable impact** (e.g., “Improved system efficiency by 20%”).
            - Highlight problem-solving, teamwork, and scalability experience.
            - **Do NOT add or infer** any new tech stacks, frameworks, or tools not already in the resume.
            - You may reword, reorder, or tighten bullets for clarity and ATS optimization.
            - Maintain **factual accuracy** and preserve all **LaTeX structure/macros** so the output compiles cleanly.
            - Avoid soft, generic language (e.g., “motivated,” “team player”) unless contextualized.

            ---

            ### Output
            Return a **two-column markdown table**:

            | Original Resume Text | Tailored Resume Text |
            |-----------------------|----------------------|

            After the table, add a short **Summary of Changes** listing:
            - Top 3 changes that improved ATS alignment
            - Example phrases made more technical or measurable.

            ---

            **Job Description:**  
            {job_description}

            **Candidate Resume:**  
            {text}

            Follow {resumeFormats.alex_format} for LaTeX formatting consistency.
            """

            try:
                pdf_path, tailored_latex = await asyncio.to_thread(ParseData.parseResume, text, prompt)
                change_md = await asyncio.to_thread(ParseData.summarize_changes, text, tailored_latex)

                await interaction.followup.send(
                    content="Here’s your tailored resume!",
                    file=discord.File(pdf_path),
                    ephemeral=True
                )
                # 2) Send the change summary (inline if short; else attach)
                if len(change_md) <= 1800:
                    await interaction.followup.send(content=change_md, ephemeral=True)
                else:
                    # write to a temp markdown file and attach
                    fname = "changes.md"
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(change_md)
                    await interaction.followup.send(
                        content="Summary of changes attached.",
                        file=discord.File(fname),
                        ephemeral=True
                    )
            except Exception as e:
                await interaction.followup.send(f"Error generating tailored resume: {e}", ephemeral=True)

        def extract_text_pdf(pdf_bytes: bytes) -> str:
            text_chunks = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    text_chunks.append(t)
            text = "\n".join(text_chunks)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            return text
