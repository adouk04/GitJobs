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
                I would like you to act as a Senior Human Resources professional with 20 years 
                of Human Resources experience. You are an expert at reviewing resumes, selecting 
                the best candidates for interviews, and deciding who to hire. Your career experience 
                has made you a recognized expert in the field of Human Resources at using Applicant 
                Tracking Systems like Workday, BambooHR, Taleo, iCIMS, and others to select the best 
                resumes that have been submitted and filter out applicants who do not meet the requirements
                for the job. I am going to provide you with the text of a job description and 
                I would like you to please provide me with the three most important responsibilities 
                in the job description and the five most important key words or phrases an applicant 
                tracking system will be looking for in resumes. Here is the job description:
                {job_description}
                That was great - thank you very much for your help! Now I am going to 
                provide you with the text of my current resume. I would like you to please 
                help me tailor my resume to the job description based on the three most important 
                responsibilities and the top five key words that you noted. In addition, if there are 
                changes you believe would make my resume a stronger fit, please also provide those changes.
                I would like you to output the results in a two column format. The column on the left 
                should show the original text of my resume and the column on the right should show the 
                new text with the changes you suggest.
                This is my original resume: {text}
                Please format the tailored resume using this structure:
                When formatting, please make sure to preserve all Latex structure and formatting, escape 
                special characters properly, and do not modify macro definitions, and the output must
                be valid Latex that compiles without errors.
                {resumeFormats.alex_format}
                """
            try:
                processed_resume_path = await asyncio.to_thread(ParseData.parseResume, text, prompt)
                await interaction.followup.send(
                    content="Here’s your tailored resume!",
                    file=discord.File(processed_resume_path),
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
