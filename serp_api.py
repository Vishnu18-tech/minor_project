import json, re, os
from dotenv import load_dotenv # type: ignore

load_dotenv()

try:
    import requests as _req # type: ignore
    USE_REQUESTS = True
except ImportError:
    import urllib.request, urllib.parse
    USE_REQUESTS = False

SERP_API_KEY = os.getenv("SERP_API_KEY")

FIELD_KEYWORDS = {
    "CSE/IT/Software":           ["software developer intern", "web development intern", "python developer intern"],
    "AI/ML/Data Science":        ["machine learning intern", "data science intern", "AI intern"],
    "Civil/Mechanical/EEE":      ["civil engineering intern", "mechanical engineering intern", "electrical intern"],
    "MBA/Marketing/Finance":     ["marketing intern", "business development intern", "finance intern"],
    "Design/UI-UX/Creative":     ["UI UX design intern", "graphic design intern", "creative intern"],
    "Medical/Pharma/Healthcare": ["pharma intern", "healthcare intern", "clinical research intern"],
}

def detect_field(text):
    t = text.lower()
    if any(x in t for x in ['cse','computer','software','web','backend','frontend','java','python','react','node']):
        return 'CSE/IT/Software'
    if any(x in t for x in ['machine learning','ml','data science','ai ','nlp','deep learning','data analyst']):
        return 'AI/ML/Data Science'
    if any(x in t for x in ['civil','mechanical','eee','electrical','electronics','structural','autocad']):
        return 'Civil/Mechanical/EEE'
    if any(x in t for x in ['mba','marketing','finance','business','sales','hr ','human resource']):
        return 'MBA/Marketing/Finance'
    if any(x in t for x in ['design','ui','ux','graphic','figma','creative','animation']):
        return 'Design/UI-UX/Creative'
    if any(x in t for x in ['medical','pharma','health','biotech','clinical','mbbs','bpharma']):
        return 'Medical/Pharma/Healthcare'
    return 'CSE/IT/Software'

def get_logo(field):
    return {
        'CSE/IT/Software': '💻',
        'AI/ML/Data Science': '🧠',
        'Civil/Mechanical/EEE': '⚙️',
        'MBA/Marketing/Finance': '📊',
        'Design/UI-UX/Creative': '🎨',
        'Medical/Pharma/Healthcare': '🏥',
    }.get(field, '🏢')

def serp_search(query):
    """Call SerpApi Google Jobs"""
    params = {
        "engine":   "google_jobs",
        "q":        query,
        "location": "India",
        "hl":       "en",
        "gl":       "in",
        "api_key":  SERP_API_KEY,
    }
    if USE_REQUESTS:
        r = _req.get("https://serpapi.com/search", params=params, timeout=15)
        print(f"  SerpApi status: {r.status_code}")
        return r.json()
    else:
        import urllib.parse, urllib.request
        url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = urllib.request.urlopen(req, timeout=15)
        return json.loads(res.read())

def fetch_live_internships(profile, top_n=15):
    education = profile.get('education', '')
    skills    = profile.get('skills', '')
    field     = detect_field(education + ' ' + skills)

    # Build queries
    skill_list = [s.strip() for s in skills.split(',') if s.strip()][:2] # type: ignore
    queries = []
    if skill_list:
        queries.append(' '.join(skill_list) + ' internship India 2025')
    queries.append(FIELD_KEYWORDS[field][0] + ' India 2025')
    queries.append(FIELD_KEYWORDS[field][1] + ' India')

    results  = []
    seen     = set()

    for query in queries:
        if len(results) >= top_n:
            break
        try:
            print(f"  🔍 Searching: '{query}'")
            data = serp_search(query)

            # Check for API errors
            if "error" in data:
                print(f"  ⚠️ SerpApi error: {data['error']}")
                continue

            jobs = data.get("jobs_results", [])
            print(f"  Found {len(jobs)} jobs")

            for job in jobs:
                title   = job.get("title", "")
                company = job.get("company_name", "Company")

                # Dedup
                key = f"{title}_{company}".lower().strip()
                if key in seen:
                    continue
                seen.add(key)

                loc  = job.get("location", "India")
                loc_lower = loc.lower()

                # Filter out foreign locations explicitly
                if re.search(r'\b(usa|us|uk|united states|united kingdom|canada|europe|australia|new york|california|london)\b', loc_lower) and 'india' not in loc_lower:
                    continue
                
                # Must contain 'india', a major Indian city, or be 'remote'
                indian_terms = ['india', 'bengaluru', 'bangalore', 'mumbai', 'pune', 'hyderabad', 'chennai', 'delhi', 'ncr', 'noida', 'gurgaon', 'gurugram', 'kolkata', 'remote']
                if not any(it in loc_lower for it in indian_terms):
                    continue

                desc = job.get("description", "")
                via  = job.get("via", "")

                # Only internship roles
                combined = (title + " " + desc[:300]).lower()
                if not any(x in combined for x in ['intern','trainee','fresher','entry level','graduate trainee']):
                    continue

                # Get best apply link
                apply_url = ""
                # Try related_links first — these are direct platform links
                for link_obj in job.get("related_links", []):
                    link = link_obj.get("link", "")
                    if any(x in link for x in ['internshala','linkedin','naukri','indeed','glassdoor','shine','unstop']):
                        apply_url = link
                        break
                # Fallback to job_highlights link or Google search
                if not apply_url:
                    apply_url = f"https://www.google.com/search?q={title.replace(' ','+')}+{company.replace(' ','+')}+internship+apply"

                # Stipend
                stipend = 0
                ext = job.get("detected_extensions", {})
                sal = ext.get("salary", "") or ""
                if sal:
                    nums = re.findall(r'\d[\d,]*', sal)
                    if nums:
                        stipend = int(nums[0].replace(',',''))

                results.append({
                    "id":          str(len(results) + 1),
                    "title":       title,
                    "company":     company,
                    "field":       field,
                    "location":    loc,
                    "stipend":     stipend,
                    "duration":    "3-6 months",
                    "skills":      extract_skills(desc),
                    "type":        "Industry",
                    "source":      f"Google Jobs" + (f" via {via}" if via else ""),
                    "logo":        get_logo(field),
                    "apply_url":   apply_url,
                    "matchScore":  calculate_match(profile, title, desc),
                    "reasoning":   f"Found on Google Jobs — {field}",
                    "description": desc[:250] + "..." if len(desc) > 250 else desc,
                })

        except Exception as e:
            print(f"  ❌ Search error: {e}")
            continue

    results.sort(key=lambda x: x['matchScore'], reverse=True)
    print(f"  ✅ Total internships returned: {len(results)}")
    return results[:top_n] # type: ignore

def calculate_match(profile, title, description):
    score     = 45
    skills    = profile.get('skills', '').lower()
    education = profile.get('education', '').lower()
    text      = (title + ' ' + description).lower()
    for skill in skills.split(','):
        s = skill.strip()
        if s and len(s) > 2 and s in text:
            score += 10
    if any(x in education for x in ['cse','computer']) and any(x in text for x in ['software','developer','python','web']):
        score += 15
    if any(x in education for x in ['mba','bba']) and any(x in text for x in ['marketing','business','finance']):
        score += 15
    if 'intern' in title.lower():
        score += 10
    return min(score, 97)

def extract_skills(description):
    common = ['Python','Java','JavaScript','React','Node.js','SQL','AWS','Excel',
              'Figma','AutoCAD','MATLAB','Marketing','Communication','Git',
              'TypeScript','C++','Docker','TensorFlow','Photoshop','Power BI',
              'R','Django','Flask','MongoDB','MySQL','HTML','CSS','Angular','Kotlin']
    found = [s for s in common if s.lower() in description.lower()]
    return found[:5] if found else ['Communication', 'Problem Solving'] # type: ignore