"""
InternMatch AI - Intelligent Internship Matching Platform
Powered by Google Jobs (SerpApi) & Groq AI
"""

import json
import io
import os
import traceback
from flask import Flask, request, jsonify, render_template  # type: ignore
from groq import Groq  # type: ignore
from pypdf import PdfReader  # type: ignore
from serp_api import fetch_live_internships  # type: ignore
from dotenv import load_dotenv  # type: ignore


# Load environment variables
load_dotenv()

# Initialize Flask app and Groq client
app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ==================== UTILITY FUNCTIONS ====================

def extract_pdf_text(file_bytes):
    """
    Extract text from PDF file bytes.
    
    Args:
        file_bytes: Raw PDF file bytes
        
    Returns:
        str: Extracted text (max 3000 chars) or empty string if extraction fails
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        
        for page in reader.pages:
            try:
                text += page.extract_text() or ""
            except Exception:
                pass
                
        return text[:3000]  # type: ignore
        
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        return ""


# ==================== ROUTE HANDLERS ====================

@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@app.route("/parse-resume", methods=["POST"])
def parse_resume():
    """
    Parse uploaded resume PDF and extract student profile information.
    
    Returns:
        JSON: Extracted profile (name, education, skills, GPA, interests, goals, experience)
    """
    try:
        print("\n" + "="*50)
        print("📄 RESUME UPLOAD")
        print("="*50)
        
        # Validate file upload
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files["resume"]
        file_bytes = file.read()
        print(f"📎 File: {file.filename}")
        print(f"📊 Size: {len(file_bytes)} bytes")
        
        # Extract PDF text
        text = extract_pdf_text(file_bytes)
        print(f"📝 Text extracted: {len(text)} characters")
        
        if not text.strip():
            return jsonify({"error": "Could not read PDF. Try a different resume."}), 400

        # Prepare AI prompt for resume parsing
        resume_text = text[:2000]  # type: ignore
        prompt = f"""Extract from this resume: name, education, skills, GPA, interests, goals.
Resume: {resume_text}
Return ONLY JSON (no markdown):
{{"name":"","education":"","skills":"","gpa":"","interests":"","goals":"","experience":"Beginner"}}"""

        # Call Groq API
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Extract resume info. Return ONLY valid JSON. No markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.2
        )
        
        # Parse JSON response
        raw = res.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        
        if start != -1 and end > start:
            raw = raw[start:end]
            
        parsed = json.loads(raw)
        print(f"✅ Resume parsed successfully: {parsed.get('name')}")
        return jsonify(parsed)

    except Exception as e:
        print(f"❌ RESUME ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyze student profile and match with live internship opportunities.
    Uses SerpApi for job listings and Groq AI for career insights.
    
    Returns:
        JSON: Matched internships, profile score, career insights, skill gaps, and tips
    """
    try:
        print("\n" + "="*50)
        print("🔍 PROFILE ANALYSIS")
        print("="*50)
        
        profile = request.json
        print(f"👤 Student: {profile.get('name')}")
        print(f"🎓 Education: {profile.get('education')}")
        print(f"💼 Skills: {profile.get('skills')}")

        # Fetch live internship opportunities from Google Jobs
        print("\n🌐 Fetching live internships from Google Jobs...")
        live_results = fetch_live_internships(profile, top_n=12)
        print(f"✅ Found {len(live_results)} internship opportunities")

        # Generate AI-powered career insights
        print("\n🤖 Generating career insights with Groq AI...")
        internship_list = "\n".join([
            f"• {i['title']} @ {i['company']} ({i['location']})"
            for i in live_results[:6]
        ])
        
        prompt = f"""You are an elite career counselor and internship advisor. Analyze this student's profile against current market data and provide actionable advice.

### Student Profile
- Name: {profile.get('name', 'Student')}
- Education: {profile.get('education', 'Unknown')}
- Skills: {profile.get('skills', 'None provided')}
- GPA: {profile.get('gpa', 'Not provided')}
- Goals: {profile.get('goals', 'General career growth')}

### Live Internship Opportunities
{internship_list if internship_list else 'No specific live internships provided; offer general industry-standard advice.'}

### Analysis Requirements
1. profileScore: Integer (0-100) - How well does their profile match current opportunities?
2. strengthSummary: Exactly 2 sentences - Highlight core marketable strengths
3. careerPath: Exactly 2 sentences - Suggest immediate internship roles and long-term trajectory
4. skillGaps: Exactly 3 items - Critical missing skills needed to be competitive
5. quickTips: Exactly 3 items - Immediate actionable steps to improve profile

### Output Format
Return ONLY valid JSON (no markdown, no code blocks):
{{
  "profileScore": 85,
  "strengthSummary": "Your string here",
  "careerPath": "Your string here",
  "skillGaps": ["Skill 1", "Skill 2", "Skill 3"],
  "quickTips": ["Tip 1", "Tip 2", "Tip 3"]
}}"""

        try:
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Internship advisor. Return ONLY valid JSON. No markdown."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=600,
                temperature=0.5
            )
            
            # Parse AI response
            raw = res.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            
            if start != -1:
                raw = raw[start:end]
                
            ai_data = json.loads(raw)
            print("✅ Career insights generated successfully")
            
        except Exception as e:
            print(f"⚠️ Using fallback insights: {e}")
            ai_data = {
                "profileScore": 70,
                "strengthSummary": f"{profile.get('name','Student')} has solid skills and good potential. Ready to start exploring internship opportunities.",
                "careerPath": "Great foundation for internship opportunities in your field. Focus on building practical experience.",
                "skillGaps": ["Portfolio Projects", "Communication", "Industry Tools"],
                "quickTips": ["Apply to 5+ internships", "Build projects on GitHub", "Update LinkedIn profile"]
            }

        # Compile response
        response = {
            "matchedInternships": live_results,
            "profileScore": ai_data.get("profileScore", 70),
            "strengthSummary": ai_data.get("strengthSummary", ""),
            "careerPath": ai_data.get("careerPath", ""),
            "skillGaps": ai_data.get("skillGaps", []),
            "quickTips": ai_data.get("quickTips", []),
            "totalLive": len(live_results),
            "source": "Google Jobs via SerpApi"
        }
        
        print(f"📊 Profile Score: {response['profileScore']}/100")
        print("="*50)
        return jsonify(response)

    except Exception as e:
        print(f"❌ ANALYSIS ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """
    Interactive chat endpoint for personalized career advice.
    Uses student profile context for relevant responses.
    
    Returns:
        JSON: AI-generated response to student query
    """
    data = request.json
    
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": f"Expert internship advisor. Student: {json.dumps(data.get('profile', {}))}"
                },
                {
                    "role": "user",
                    "content": data.get("message", "")
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({"reply": res.choices[0].message.content})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== APPLICATION ENTRY POINT ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 InternMatch AI - Internship Matching Platform")
    print("🔗 Powered by Google Jobs (SerpApi) & Groq AI")
    print("="*60)
    print("📍 Open: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True)