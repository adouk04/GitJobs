import dotenv
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from discord import app_commands, Interaction
import discord 

load_dotenv()
client = OpenAI()

OPENAI_ASSISTANT_KEY = os.getenv("OPENAI_ASSISTANT_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

thread = client.beta.threads.create()


class ParseData:

    def __init__(self, resume, prompt):
        if not resume:
            raise ValueError("No file attached — please upload a PDF resume")
        if not prompt:
            raise ValueError("No prompt returned, check TailorResume.py")
        self.resume = resume
        self.prompt = prompt

    @staticmethod
    def parseResume(resume, prompt):

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional resume editor."},
                {"role": "user", "content": prompt}
            ]
        )

        tailored_resume = response.choices[0].message.content

        filename = "Tailored_Resume.pdf"
        ParseData.save_pdf(tailored_resume, filename)

        return filename


    @staticmethod
    def save_pdf(text: str, filename: str):
        c = canvas.Canvas(filename, pagesize=LETTER)
        width, height = LETTER
        margin = 50
        y = height - margin

        for line in text.split("\n"):
            if y < 50:  # start new page if text runs out
                c.showPage()
                y = height - margin
            c.drawString(margin, y, line)
            y -= 14
        c.save()
