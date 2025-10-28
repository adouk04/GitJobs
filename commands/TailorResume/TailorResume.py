from discord import app_commands, Interaction, Attachment
import pdfplumber, re, io
from parseData import ParseData
import discord
import resumeFormats
import asyncio

# lingo
# ephemeral - indicates to only the user that runs the command

class TailorResume:
    def __init__(self, tree: app_commands.CommandTree):
        if not tree:
            raise ValueError("No tree available, discord bot failed to run")
        self.tree = tree  
        self._register()

    def _register(self):
        @self.tree.command(name="tailor_resume", description="tailors resume for user")
        
        async def tailor_resume(interaction: Interaction, file:Attachment, job_description: str):

            if not file.filename.lower().endswith(".pdf"):
                await interaction.response.send_message(
                    "Please upload a valid `.pdf` file.",
                    ephemeral=True
                )
                return
            
            # check file size before sending the initial response so we only
            # call interaction.response.send_message once per interaction
            if file.size > 25 * 1024 * 1024:
                await interaction.response.send_message(
                    "File too large! Please upload a file smaller than 25MB.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True, thinking=True)

            await interaction.followup.send_message(f"Received {file.filename}", ephemeral=True)
            
            try:
                pdf_bytes = await file.read()

                text = extract_text_pdf(pdf_bytes)

                if not text.strip():
                    await interaction.followup.send(
                        "I couldn’t extract any text—this PDF may be image-only. Try an OCRed PDF.",
                        ephemeral=True
                    )
                    return

                await interaction.followup.send(
                    f"Received `{file.filename}` successfully! Extracted ~{len(text)} characters.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"Failed to parse the PDF: {e}", ephemeral=True)

            await interaction.followup.send(
                f"Received `{file.filename}` successfully!",
                ephemeral=True
            )            

            resume = text
            #parse data
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
                # Run the blocking LaTeX call in a background thread
                processed_resume_path = await asyncio.to_thread(ParseData.parseResume, text, prompt)

                await interaction.followup.send(
                    content="Here’s your tailored resume!",
                    file=discord.File(processed_resume_path),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(
                    f"Error generating tailored resume: {e}",
                    ephemeral=True
                )            


        def extract_text_pdf(pdf_bytes: bytes) -> str:
            text_chunks = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""      # None for scanned pages
                    text_chunks.append(t)
            text = "\n".join(text_chunks)
            # light cleanup
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            return text