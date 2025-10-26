from discord import app_commands, Interaction, Attachment
import pdfplumber, re, io

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
        # another parameter for job description (copy & paste text in)
        async def tailor_resume(interaction: Interaction, file:Attachment):

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
            await interaction.response.send_message(f"Received {file.filename}", ephemeral=True)
            
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

            # followup uses `send`, not `send_message`
            await interaction.followup.send(
                f"Received `{file.filename}` successfully!",
                ephemeral=True
            )            

            # calls parseData?
            processed_data = text
            #parse data


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