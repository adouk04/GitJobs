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

            # 2) All messages after defer -> followup.send
            if not file.filename.lower().endswith(".pdf"):
                await interaction.response.send_message("Please upload a valid `.pdf` file.", ephemeral=True)
                return

            if file.size > 25 * 1024 * 1024:
                await interaction.response.send_message("File too large! Please upload a file smaller than 25MB.", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True, thinking=True)
            
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
            You are a **Senior Technical Recruiter (20+ yrs)** experienced in hiring **Software Engineers** at top tech firms.
            You are an expert at using **ATS (Workday, Lever, Greenhouse, Taleo, iCIMS)** to evaluate resumes for 
            **SWE Interns, SDE Intern, Data/Systems interns, etc** roles.

            ---

            ### Task
            Analyze the following job description and candidate resume, then **tailor the resume** to align with the most relevant
            responsibilities and keywords from the description.

            ### Guidelines
            - Focus on **data structures, algorithms, debugging, scalability, APIs, CI/CD, distributed systems, and ownership**.
            - Use **action verbs + quantifiable impact** (e.g., “Improved system efficiency by 20%”).
            - Highlight collaboration, problem-solving, and scalability experience.
            - **Do NOT add or infer** any new tech stacks, frameworks, or tools not already listed.
            - Maintain **factual accuracy** and preserve all **LaTeX structure/macros**.
            - **Output only valid LaTeX** that compiles. Do NOT include markdown, analysis, explanations, or code fences.

            ---

            **Job Description:**  
            {job_description}

            **Candidate Resume (plain text):**  
            {text}

            Use this LaTeX template for formatting consistency:  
            {resumeFormats.alex_format}
            """
            try:
                pdf_path, tailored_latex = await asyncio.to_thread(ParseData.parseResume, text, prompt)
                change_md = await asyncio.to_thread(ParseData.summarize_changes, text, tailored_latex)
                print(f"Change summary length: {len(change_md)}")
                await interaction.followup.send(
                    content="Here’s your tailored resume!",
                    file=discord.File(pdf_path),
                    ephemeral=True
                )
                # 2) Send the change summary (inline if short; else attach)
                if change_md:
                    parts = split_message(change_md)
                    for i, chunk in enumerate(parts):
                        await interaction.followup.send(
                            content=f"**Change Summary (Part {i+1}/{len(parts)})**\n{chunk}",
                            ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        content="No summary of changes was generated.",
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
        
        def split_message(text, limit=1800):
            """Split text safely into chunks below Discord's 2000-char limit."""
            clean = text.replace("```", "`").replace("@", "@\u200b")  # prevent accidental mentions
            return [clean[i:i+limit] for i in range(0, len(clean), limit)]

           