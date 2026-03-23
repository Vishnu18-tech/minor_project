from flask import Flask, request, jsonify, render_template # type: ignore
from groq import Groq # type: ignore
from pypdf import PdfReader # type: ignore
from serp_api import fetch_live_internships # type: ignore
import json, io, traceback, os
from dotenv import load_dotenv # type: ignore

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_pdf_text(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            try: text += page.extract_text() or ""
            except: pass
        return text[:3000] # type: ignore
    except Exception as e:
        print(f"PDF error: {e}")
        return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/parse-resume", methods=["POST"])
def parse_resume():
    try:
        print("\n=== RESUME UPLOAD ===")
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files["resume"]
        file_bytes = file.read()
        print(f"File: {file.filename} | Size: {len(file_bytes)} bytes")
        text = extract_pdf_text(file_bytes)
        print(f"Text extracted: {len(text)} chars")
        if not text.strip():
            return jsonify({"error": "Could not read PDF. Try a different resume."}), 400

        resume_text = text[:2000] # type: ignore
        prompt = f"""Extract from this resume: name, education, skills, GPA, interests, goals.
Resume: {resume_text}
Return ONLY JSON (no markdown):
{{"name":"","education":"","skills":"","gpa":"","interests":"","goals":"","experience":"Beginner"}}"""

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":"Extract resume info. Return ONLY valid JSON. No markdown."},
                {"role":"user","content":prompt}
            ],
            max_tokens=500, temperature=0.2
        )
        raw = res.choices[0].message.content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        start = raw.find("{"); end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        parsed = json.loads(raw)
        print(f"✅ Resume parsed: {parsed.get('name')}")
        return jsonify(parsed)

    except Exception as e:
        print(f"❌ RESUME ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        print("\n=== ANALYZE ===")
        profile = request.json
        print(f"Profile: {profile.get('name')} | {profile.get('education')} | {profile.get('skills')}")

        # SerpApi — Google Jobs
        print("🔍 Calling SerpApi (Google Jobs)...")
        live_results = fetch_live_internships(profile, top_n=12)
        print(f"✅ Got {len(live_results)} internships from Google Jobs")

        # Groq AI insights
        print("🤖 Calling Groq AI...")
        internship_list = "\n".join([
            f"{i['title']} @ {i['company']} | {i['location']}"
            for i in live_results[:6]
        ])
        prompt = f"""You are an elite career counselor and internship advisor. Your goal is to critically analyze the student's profile and provide actionable, highly relevant advice aligned with current market data.

### Context
- Evaluate the student's education, skills, and goals against typical industry expectations for their desired roles.
- Tailor your recommendations specifically toward the provided live internships.
- Provide objective, highly specific, and constructive feedback.

### Student Profile
- Name: {profile.get('name', 'Student')}
- Education: {profile.get('education', 'Unknown')}
- Skills: {profile.get('skills', 'None provided')}
- GPA: {profile.get('gpa', 'Not provided')}
- Goals: {profile.get('goals', 'General career growth')}

### Live Internship Opportunities
{internship_list if internship_list else 'No specific live internships provided; offer general industry-standard advice.'}

### Analysis Instructions
1. profileScore: Evaluate profile strength as an integer (0-100) based on how well they match the live opportunities.
2. strengthSummary: Write exactly 2 concise, impactful sentences highlighting their core marketable strengths.
3. careerPath: Write exactly 2 concise sentences suggesting the most viable immediate internship roles and long-term trajectory.
4. skillGaps: List exactly 3 critical missing skills or tools they must learn to be competitive for the listed internships.
5. quickTips: List exactly 3 highly actionable, immediate steps the student should take right now to improve their profile.

### Output Format Specification
You MUST return ONLY a strictly valid JSON object. Do NOT wrap the JSON in markdown blocks (no ```json). Do NOT add any conversational text before or after the JSON.

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
                    {"role":"system","content":"Internship advisor. Return ONLY valid JSON. No markdown."},
                    {"role":"user","content":prompt}
                ],
                max_tokens=600, temperature=0.5
            )
            raw = res.choices[0].message.content.strip()
            raw = raw.replace("```json","").replace("```","").strip()
            start = raw.find("{"); end = raw.rfind("}") + 1
            if start != -1: raw = raw[start:end]
            ai_data = json.loads(raw)
            print("✅ Groq AI done")
        except Exception as e:
            print(f"⚠️ Groq fallback used: {e}")
            ai_data = {
                "profileScore": 70,
                "strengthSummary": f"{profile.get('name','Student')} has solid skills and good potential.",
                "careerPath": "Great foundation for internship opportunities in your field.",
                "skillGaps": ["Portfolio Projects", "Communication", "Industry Tools"],
                "quickTips": ["Apply to 5+ internships", "Build projects on GitHub", "Update LinkedIn"]
            }

        return jsonify({
            "matchedInternships": live_results,
            "profileScore":       ai_data.get("profileScore", 70),
            "strengthSummary":    ai_data.get("strengthSummary", ""),
            "careerPath":         ai_data.get("careerPath", ""),
            "skillGaps":          ai_data.get("skillGaps", []),
            "quickTips":          ai_data.get("quickTips", []),
            "totalLive":          len(live_results),
            "source":             "Google Jobs via SerpApi"
        })

    except Exception as e:
        print(f"❌ ANALYZE ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":f"Expert internship advisor. Student: {json.dumps(data.get('profile',{}))}"},
                {"role":"user","content":data.get("message","")}
            ],
            max_tokens=500, temperature=0.7
        )
        return jsonify({"reply": res.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 InternMatch AI — Powered by Google Jobs (SerpApi)")
    print("📍 Open: http://127.0.0.1:5000")
    app.run(debug=True)