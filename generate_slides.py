import sys
import subprocess

# Try importing fpdf2, install if missing
try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

class SlidePDF(FPDF):
    def __init__(self):
        # Initialize in Landscape mode (A4)
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_margin(15)
        self.slide_title = ""
        self.is_title_page = False
        # Set auto page break margin small enough to not conflict with footer
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.is_title_page:
            # Dark title slide background
            self.set_fill_color(30, 41, 59) # Slate 800
            self.rect(0, 0, 297, 210, 'F')
            
            # Highlight stripe
            self.set_fill_color(251, 146, 60) # Orange 400
            self.rect(0, 195, 297, 15, 'F')
        else:
            # Regular slide template
            # Clear background
            self.set_fill_color(248, 250, 252) # Slate 50
            self.rect(0, 0, 297, 210, 'F')
            
            # Header banner
            self.set_fill_color(30, 41, 59) # Slate 800
            self.rect(0, 0, 297, 28, 'F')
            
            # Highlight stripe in header
            self.set_fill_color(251, 146, 60) # Orange 400
            self.rect(0, 26, 297, 2, 'F')
            
            # Header Title
            self.set_xy(15, 8)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 15)
            self.cell(0, 10, self.slide_title, align='L')

    def footer(self):
        if not self.is_title_page:
            # Footer
            self.set_y(-12)
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(148, 163, 184) # Slate 400
            self.cell(0, 10, f"Vdcap.AI - AMD Developer Hackathon: ACT II | Page {self.page_no()}/5", align='R')

def build_presentation(output_path):
    pdf = SlidePDF()
    pdf.alias_nb_pages()
    
    # ----------------------------------------------------
    # SLIDE 1: Title Page
    # ----------------------------------------------------
    pdf.is_title_page = True
    pdf.add_page()
    
    # Title Text
    pdf.set_xy(20, 60)
    pdf.set_font('helvetica', 'B', 46)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, 'Vdcap.AI', new_x="LMARGIN", new_y="NEXT")
    
    # Accent Line
    pdf.ln(5)
    pdf.set_draw_color(251, 146, 60) # Orange 400
    pdf.set_line_width(2.0)
    pdf.line(20, pdf.get_y(), 100, pdf.get_y())
    pdf.ln(8)
    
    # Subtitle Text
    pdf.set_x(20)
    pdf.set_font('helvetica', 'B', 18)
    pdf.set_text_color(226, 232, 240) # Slate 200
    pdf.cell(0, 10, '4-Style Synchronized AI Video Captioning Platform', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(15)
    pdf.set_x(20)
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(251, 146, 60) # Accent Color
    pdf.cell(0, 8, 'Track: Video-Captioning Pipeline', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(20)
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(148, 163, 184) # Slate 400
    pdf.cell(0, 8, 'Built for: AMD Developer Hackathon: ACT II', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, 'Developed by: Rishabharaj Sharma', new_x="LMARGIN", new_y="NEXT")
    
    # ----------------------------------------------------
    # SLIDE 2: Problem & Solution
    # ----------------------------------------------------
    pdf.is_title_page = False
    pdf.slide_title = "The Core Problem & Vdcap.AI Solution"
    pdf.add_page()
    
    pdf.set_xy(15, 38)
    
    # Left Column: The Problem
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_text_color(239, 68, 68) # Red 500
    pdf.cell(125, 8, "The Problem", new_x="RIGHT", new_y="TOP")
    
    # Right Column: The Solution
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_text_color(34, 197, 94) # Green 500
    pdf.cell(125, 8, "Our Solution: Vdcap.AI", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.set_x(15)
    y_start = pdf.get_y()
    
    # Left Box Text
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(51, 65, 85) # Slate 700
    problem_text = (
        "- Single-Style Limitations: Current caption generators only support a single, "
        "generic style, forcing creators to manually adapt transcripts for different audiences.\n\n"
        "- High Resource Costs: Manually styling subtitles across multiple tones (casual, tech, professional) "
        "requires extensive video editing and caption re-writing.\n\n"
        "- Engagement & Accessibility Gaps: Static or poorly-targeted captions reduce viewer engagement, "
        "failing to hook audiences on social media platforms."
    )
    pdf.multi_cell(120, 6, problem_text)
    
    # Right Box Text
    pdf.set_xy(145, y_start)
    solution_text = (
        "- Automatic 4-Style Generation: Transcribes video and uses LLMs to concurrently generate "
        "Formal, Sarcastic, Tech-Humor, and Casual-Humor captions.\n\n"
        "- Synced Multi-Player Comparison: Implements a 4-quadrant layout where all 4 streams play "
        "in frame-perfect synchronization, allowing instant subtitle evaluation.\n\n"
        "- Low-Overhead Pipeline: Automates audio extraction, speech transcription, vision analysis, "
        "and drawtext overlays in a single streamlined execution loop."
    )
    pdf.multi_cell(130, 6, solution_text)
    
    # ----------------------------------------------------
    # SLIDE 3: Technical Architecture & Pipeline
    # ----------------------------------------------------
    pdf.slide_title = "Technical Architecture & Processing Pipeline"
    pdf.add_page()
    
    pdf.set_xy(15, 38)
    
    # Flow description
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "End-to-End Pipeline Execution in the Codebase:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    steps = [
        ("Step 1: Input Ingestion & Verification", 
         "FastAPI backend accepts video files (MP4, WebM, etc.). Uses FFprobe to programmatically validate duration, format, and check for an audio track."),
        
        ("Step 2: Dual-Mode Extraction Pipeline", 
         "If audio is present: FFmpeg extracts a 16kHz mono WAV file for transcription. "
         "If video is mute: OpenCV splits keyframes at 1 FPS to extract visual representative context for captioning."),
         
        ("Step 3: Speech-To-Text Transcription", 
         "Whisper processes the extracted WAV file to generate high-accuracy transcripts complete with word-level timestamps."),
         
        ("Step 4: Fireworks AI LLM Captioning Engine", 
         "Dispatches transcript and visual frames to Fireworks AI using the GLM-5.2 (glm-5p2) model. "
         "Four custom-engineered system prompts guide the model to simultaneously generate Formal, Sarcastic, Humorous-Tech, and Humorous-NonTech subtitles.")
    ]
    
    for title, desc in steps:
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 5, f"* {title}:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(265, 5, desc)
        pdf.ln(2)

    # ----------------------------------------------------
    # SLIDE 4: Interactive UI & Burn-In Features
    # ----------------------------------------------------
    pdf.slide_title = "Synchronized Playback & Subtitle Burn-In"
    pdf.add_page()
    
    pdf.set_xy(15, 38)
    
    # Left Column: Synchronized 4-Quadrant Player
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(125, 8, "1. Synchronized 4-Quadrant Player", new_x="RIGHT", new_y="TOP")
    
    # Right Column: FFmpeg Caption Burner & Export
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(125, 8, "2. Subtitle Burn-In & Rich Exports", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.set_x(15)
    y_start = pdf.get_y()
    
    # Left content
    pdf.set_font('helvetica', '', 10.5)
    pdf.set_text_color(71, 85, 105)
    sync_content = (
        "- Native synchronized playback built using HTML5 video nodes and Vanilla JavaScript.\n\n"
        "- A centralized event controller captures play, pause, seek, and ratechange events "
        "on the primary player and mirrors them instantly to the other three quadrants.\n\n"
        "- Color-coded design maps to each specific caption style:\n"
        "  * Formal: Blue Theme\n"
        "  * Sarcastic: Pink Theme\n"
        "  * Humorous-Tech: Purple Theme\n"
        "  * Humorous-NonTech: Emerald Theme"
    )
    pdf.multi_cell(120, 5.5, sync_content)
    
    # Right content
    pdf.set_xy(145, y_start)
    export_content = (
        "- Subtitles are permanently overlayed onto separate video copies via FFmpeg's drawtext filter.\n\n"
        "- Custom font configurations (Inter-Bold), outline strokes, sizes, and padding are applied "
        "dynamically to render high-contrast subtitle blocks.\n\n"
        "- Robust export service packages results in various formats:\n"
        "  * SRT files matching each style's timestamps\n"
        "  * Formatted JSON files for programmatic reuse\n"
        "  * Captioned MP4 downloads\n"
        "  * Combined ZIP containing files and HTML report summary"
    )
    pdf.multi_cell(130, 5.5, export_content)

    # ----------------------------------------------------
    # SLIDE 5: Machine Learning Training & Future Scope
    # ----------------------------------------------------
    pdf.slide_title = "Model Fine-Tuning & Future Roadmap"
    pdf.add_page()
    
    pdf.set_xy(15, 38)
    
    # Left Column: ML Fine-Tuning Pipeline
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(125, 8, "Fine-Tuning Pipeline (LoRA)", new_x="RIGHT", new_y="TOP")
    
    # Right Column: Future Roadmap
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(125, 8, "Project Future Scope", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.set_x(15)
    y_start = pdf.get_y()
    
    # Left content
    pdf.set_font('helvetica', '', 10.5)
    pdf.set_text_color(71, 85, 105)
    tuning_content = (
        "- Codebase includes a fine-tuning module (train_captioner.py) for domain adaptation.\n\n"
        "- Configured to train on MSR-VTT (Video-to-Text) and ActivityNet Captions datasets.\n\n"
        "- Integrates Low-Rank Adaptation (LoRA) to adapt LLM layers with reduced GPU memory footprint.\n\n"
        "- Standard hyperparameters (rank=16, alpha=32, batch_size=8) allow rapid training on AMD ROCm compute instances."
    )
    pdf.multi_cell(120, 5.5, tuning_content)
    
    # Right content
    pdf.set_xy(145, y_start)
    roadmap_content = (
        "- Multi-Language Support: Broaden caption translation into multiple global languages (French, Spanish, Hindi).\n\n"
        "- Live Webcam/Stream Integration: Implement real-time audio chunk processing and streaming caption burn-in.\n\n"
        "- Enterprise Dashboard: Add user databases to save generation histories and track API consumption rates.\n\n"
        "- Mobile Companion App: Develop React Native companion app for mobile content creators."
    )
    pdf.multi_cell(130, 5.5, roadmap_content)
    
    # Save the output PDF
    pdf.output(output_path)
    print(f"Successfully generated slides PDF: {output_path}")

if __name__ == "__main__":
    build_presentation("D:/Antigravity/Vdcap/presentation_slides.pdf")
