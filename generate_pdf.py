import sys
import subprocess

# Try importing fpdf2, install if missing
try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # Header banner
        self.set_fill_color(30, 41, 59) # Slate 800
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 16)
        self.set_xy(10, 10)
        self.cell(0, 10, 'AMD Developer Hackathon: ACT II - Project Submission', new_x="LMARGIN", new_y="NEXT", align='L')
        self.ln(15)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def create_submission_pdf(output_path):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Title Section
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Project: Vdcap.AI (4-Style Video Captioning Platform)', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Draw horizontal line
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # 1. Submission Title
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, 'Submission Title (min 5, max 50 characters):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, 'Vdcap.AI: Multi-Style Video Captioning Platform', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # 2. Short Description
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, 'Short Description (min 50, max 255 characters):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    short_desc = (
        "An AI-powered video captioning platform that generates 4 distinct caption styles "
        "(Formal, Sarcastic, Tech-Humor, Casual-Humor) and burns them using FFmpeg, "
        "displayed in a synchronized 4-quadrant player with rich export options."
    )
    pdf.multi_cell(190, 6, short_desc)
    pdf.ln(4)
    
    # 3. Long Description
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, 'Long Description (min 100 words, 600-2000 characters):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    long_desc = (
        "Vdcap.AI is a full-stack, automated video captioning platform that generates and compares "
        "four distinct caption styles side-by-side. Designed for creators and marketers, the system "
        "accepts video uploads and extracts audio and keyframes using FFmpeg and OpenCV. If audio is "
        "present, it uses cloud Speech-to-Text APIs (Groq, Sarvam, or Fireworks Whisper) for high-fidelity "
        "transcription. If the video is mute, the pipeline falls back to visual frame analysis.\n\n"
        "The transcript and visual context are processed via Fireworks AI using the Llama-3.1-8B-Instruct "
        "and GLM models. These generate four tailored caption styles: Formal (professional), Sarcastic "
        "(witty), Humorous-Tech (developer-oriented), and Humorous-NonTech (casual). FFmpeg overlay "
        "filters burn these captions directly onto separate video streams.\n\n"
        "On the frontend, a handcrafted dark-mode glassmorphism interface presents the results in a "
        "synchronized 4-quadrant player. Seeking, playing, or pausing any video instantly syncs the other "
        "three, allowing real-time comparison of subtitle styles. Users can export their captions as "
        "individual SRT files, structured JSON data, captioned MP4s, or a complete ZIP package including "
        "an interactive HTML summary report. Vdcap.AI also contains a modular pipeline using LoRA adapters "
        "for fine-tuning caption models on MSR-VTT and ActivityNet datasets, making it fully ready for "
        "custom AI deployment."
    )
    pdf.multi_cell(190, 5.5, long_desc)
    pdf.ln(4)
    
    # 4. Event Tracks & Categories
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, 'Event Tracks / Categories:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, 'Track: Video-Captioning Pipeline', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, 'Category: AI-Powered Video Processing & Captioning / Multi-Model AI Pipelines', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # 5. Technologies Used
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 7, 'Technologies Used:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    techs = [
        "Backend Framework: FastAPI, Python 3.10+, Uvicorn",
        "AI & LLM Services: Fireworks AI API (LLaMA-3.1-8B-Instruct, GLM-5p2), Groq Cloud API, Sarvam AI API (Speech-to-Text), Whisper STT",
        "Media & Video Processing: FFmpeg & FFprobe (audio/frame extraction, drawtext subtitle burning), OpenCV (visual frame analysis)",
        "Frontend: Vanilla HTML5 / CSS3 (dark glassmorphism design), Vanilla JavaScript (multi-player playback sync)",
        "Data & Export: SRT subtitles, JSON metadata, ZIP archive packaging"
    ]
    for tech in techs:
        pdf.multi_cell(190, 5.5, f"- {tech}")
        
    pdf.output(output_path)
    print(f"Successfully generated PDF: {output_path}")

if __name__ == "__main__":
    create_submission_pdf("D:/Antigravity/Vdcap/hackathon_submission.pdf")
