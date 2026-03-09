let currentProfile = {};
let currentRecommendations = {};
let allInternships = [];

const STEPS_NORMAL = [
  "Parsing your profile & degree...",
  "Detecting your field of study...",
  "Scanning 100+ internships...",
  "Computing AI match scores...",
  "Ranking best opportunities...",
  "Preparing your results...",
];
const STEPS_RESUME = [
  "Reading your PDF resume...",
  "Extracting skills & education...",
  "Detecting your field...",
  "Scanning 100+ internships...",
  "Computing AI match % scores...",
  "Preparing your results...",
];

function showPage(id) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  window.scrollTo(0,0);
}

function resetApp() {
  currentProfile={}; currentRecommendations={}; allInternships=[];
  document.getElementById("chat-messages").innerHTML="";
  ["f-name","f-skills","f-education","f-gpa","f-interests","f-goals"]
    .forEach(id=>{ const el=document.getElementById(id); if(el) el.value=""; });
  showPage("page-landing");
}

function startAnalysis(isResume=false) {
  const steps = isResume ? STEPS_RESUME : STEPS_NORMAL;
  const c = document.getElementById("analysis-steps");
  c.innerHTML = steps.map((s,i)=>`
    <div class="step-item" id="step-${i}">
      <div class="step-dot" id="dot-${i}"></div><span>${s}</span>
    </div>`).join("");
  let cur=0;
  function tick() {
    if(cur>0){
      document.getElementById(`step-${cur-1}`)?.classList.replace("active","done");
      const d=document.getElementById(`dot-${cur-1}`); if(d) d.textContent="✓";
    }
    if(cur<steps.length){ document.getElementById(`step-${cur}`)?.classList.add("active"); cur++; setTimeout(tick,900); }
  }
  tick();
}

// ── Resume Upload ─────────────────────────────────────────────
async function handleResume(input) {
  const file = input.files[0];
  if (!file) return;

  // Check file type
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert("Please upload a PDF file only!");
    return;
  }

  document.getElementById("analyze-title").textContent = "Reading Your Resume...";
  showPage("page-analyzing");
  startAnalysis(true);

  const formData = new FormData();
  formData.append("resume", file);

  try {
    const res = await fetch("/parse-resume", { method:"POST", body:formData });

    // Check if response is OK first
    if (!res.ok) {
      throw new Error("Server error: " + res.status + ". Make sure app.py is running!");
    }

    // Check content type — must be JSON not HTML
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      throw new Error("Server returned HTML instead of JSON. Restart app.py and try again.");
    }

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    currentProfile = data;
    // auto-fill form fields
    if(data.name)       document.getElementById("f-name").value       = data.name;
    if(data.education)  document.getElementById("f-education").value  = data.education;
    if(data.skills)     document.getElementById("f-skills").value     = data.skills;
    if(data.gpa)        document.getElementById("f-gpa").value        = data.gpa;
    if(data.interests)  document.getElementById("f-interests").value  = data.interests;
    if(data.goals)      document.getElementById("f-goals").value      = data.goals;

    // now analyze
    await runAnalysis(data);

  } catch(err) {
    console.error("Resume error:", err);
    showPage("page-form");
    // Show friendly message
    const msg = err.message.includes("HTML instead of JSON")
      ? "⚠️ Server not running properly!\n\nMake sure:\n1. PowerShell లో 'python app.py' run చేశావా?\n2. http://127.0.0.1:5000 లో open చేశావా?\n\nForm manually fill చేయి!"
      : "⚠️ Resume చదవడంలో error వచ్చింది!\n\nError: " + err.message + "\n\nForm manually fill చేయి!";
    alert(msg);
  }
}

// ── Manual Form ───────────────────────────────────────────────
function collectProfile() {
  return {
    name:       document.getElementById("f-name").value.trim(),
    education:  document.getElementById("f-education").value.trim(),
    skills:     document.getElementById("f-skills").value.trim(),
    gpa:        document.getElementById("f-gpa").value.trim(),
    interests:  document.getElementById("f-interests").value.trim(),
    goals:      document.getElementById("f-goals").value.trim(),
    experience: document.getElementById("f-experience").value,
    location:   document.getElementById("f-location").value,
  };
}

async function analyzeProfile() {
  const p = collectProfile();
  if (!p.name || !p.education) { alert("Please enter your name and education/degree."); return; }
  currentProfile = p;
  document.getElementById("analyze-title").textContent="Finding Your Best Matches...";
  showPage("page-analyzing");
  startAnalysis(false);
  await runAnalysis(p);
}

async function runAnalysis(profile) {
  try {
    const res = await fetch("/analyze", {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(profile)
    });
    const data = await res.json();
    if(data.error) throw new Error(data.error);
    currentRecommendations = data;
    allInternships = data.matchedInternships || [];
    renderResults(data, profile);
    setTimeout(()=>showPage("page-results"), 400);
  } catch(err) {
    alert("Error: "+err.message);
    showPage("page-form");
  }
}

// ── Render ────────────────────────────────────────────────────
function renderResults(data, profile) {
  document.getElementById("results-subtitle").textContent = `Results for ${profile.name}`;
  const score = data.profileScore||0;
  const color = score>=80?"#00f5a0":score>=60?"#f5c400":"#f55";
  const circle = document.getElementById("score-circle");
  circle.style.stroke=color;
  circle.style.strokeDashoffset = 251.2 - (score/100)*251.2;
  document.getElementById("score-num").textContent=score;
  document.getElementById("score-num").style.color=color;
  document.getElementById("strength-summary").textContent=data.strengthSummary||"";
  document.getElementById("career-path").textContent=data.careerPath||"";
  document.getElementById("quick-tips").innerHTML=(data.quickTips||[]).map((t,i)=>`
    <div class="tip-item"><span class="tip-num">${i+1}.</span><span>${t}</span></div>`).join("");
  document.getElementById("skill-gaps-list").innerHTML=(data.skillGaps||[]).map(s=>
    `<div class="gap-tag">📚 ${s}</div>`).join("");
  populateFilters(allInternships);
  renderCards(allInternships);
  document.getElementById("match-count").textContent=`${allInternships.length} internships matched`;
  appendMsg("bot",`Hi ${profile.name}! 👋 Found <strong>${allInternships.length} internships</strong> matching your profile!<br>Profile Score: <strong>${score}/100</strong> · Click any card to expand → then <strong>Apply Now</strong>! 🚀`);
}

// ── Filters ───────────────────────────────────────────────────
function populateFilters(list) {
  const fields    = [...new Set(list.map(i=>i.field))].sort();
  const locations = [...new Set(list.map(i=>i.location))].sort();
  setOpts("filter-field",    fields,    "All Fields");
  setOpts("filter-location", locations, "All Locations");
}
function setOpts(id, vals, label) {
  const el=document.getElementById(id); if(!el) return;
  el.innerHTML=`<option value="">${label}</option>`+vals.map(v=>`<option value="${v}">${v}</option>`).join("");
}
function applyFilters() {
  const field   = document.getElementById("filter-field")?.value;
  const loc     = document.getElementById("filter-location")?.value;
  const stipend = document.getElementById("filter-stipend")?.value;
  const search  = document.getElementById("filter-search")?.value.toLowerCase();
  const filtered = allInternships.filter(i=>{
    if(field  && i.field!==field)   return false;
    if(loc    && i.location!==loc)  return false;
    if(stipend==="free" && i.stipend>0)      return false;
    if(stipend==="10k"  && i.stipend<10000)  return false;
    if(stipend==="30k"  && i.stipend<30000)  return false;
    if(stipend==="50k"  && i.stipend<50000)  return false;
    if(search && !i.title.toLowerCase().includes(search) &&
       !i.company.toLowerCase().includes(search) &&
       !i.skills.join(" ").toLowerCase().includes(search)) return false;
    return true;
  });
  renderCards(filtered);
  document.getElementById("match-count").textContent=`${filtered.length} internships found`;
}
function clearFilters() {
  ["filter-field","filter-location","filter-stipend","filter-search"]
    .forEach(id=>{const el=document.getElementById(id);if(el)el.value="";});
  renderCards(allInternships);
  document.getElementById("match-count").textContent=`${allInternships.length} internships matched`;
}

// ── Cards ─────────────────────────────────────────────────────
function renderCards(list) {
  const el=document.getElementById("matches-list");
  if(!list.length){
    el.innerHTML=`<div style="text-align:center;padding:40px;color:#555">No internships match your filters.</div>`;
    return;
  }
  const rankColors=["#00f5a0","#f5c400","#f5a623","#a78bfa","#60a5fa","#f472b6","#34d399","#fb923c","#a3e635","#38bdf8"];
  el.innerHTML=list.map((intern,idx)=>{
    const matchScore = intern.matchScore || 0;
    const matchColor = matchScore>=80?"#00f5a0":matchScore>=60?"#f5c400":"#f5a623";
    return `
    <div class="intern-card" onclick="toggleCard(this)">
      <div class="intern-top">
        <div class="intern-logo">${intern.logo}</div>
        <div class="intern-info">
          <div class="intern-badges">
            <span class="badge-rank" style="background:${rankColors[idx]||'#555'}">#${idx+1}</span>
            <span class="badge-type">${intern.type}</span>
            <span class="badge-source">${intern.source}</span>
          </div>
          <div class="intern-title">${intern.title}</div>
          <div class="intern-company">${intern.company} · 📍 ${intern.location}</div>
        </div>
        <div class="intern-right">
          ${matchScore ? `<div class="match-score-badge" style="color:${matchColor};border-color:${matchColor}40;background:${matchColor}10">${matchScore}% Match</div>` : ""}
          <div class="intern-stipend">${intern.stipend>0?"₹"+intern.stipend.toLocaleString()+"/mo":"Unpaid"}</div>
          <div class="intern-duration">⏱ ${intern.duration}</div>
        </div>
      </div>
      <div class="intern-expanded">
        ${matchScore ? `
        <div class="match-bar-wrap">
          <div class="match-bar-label">AI Compatibility</div>
          <div class="match-bar-bg"><div class="match-bar-fill" style="width:${matchScore}%;background:${matchColor}"></div></div>
          <span style="color:${matchColor};font-weight:700;font-size:13px">${matchScore}%</span>
        </div>` : ""}
        <div class="skills-row">${intern.skills.map(s=>`<span class="skill-tag">${s}</span>`).join("")}</div>
        ${intern.reasoning?`<div class="ai-reasoning"><strong>🤖 Why this matches you:</strong> ${intern.reasoning}</div>`:""}
        <button class="btn-apply" onclick="applyNow(event,'${intern.apply_url}')">🚀 Apply Now — Opens Official Website</button>
      </div>
    </div>`}).join("");
}

function toggleCard(card){ card.querySelector(".intern-expanded").classList.toggle("open"); }
function applyNow(e,url){ e.stopPropagation(); window.open(url,"_blank"); }

// ── Tabs ──────────────────────────────────────────────────────
function switchTab(name,btn){
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c=>c.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(`tab-${name}`).classList.add("active");
}

// ── Chat ──────────────────────────────────────────────────────
function appendMsg(role,html){
  const c=document.getElementById("chat-messages");
  const d=document.createElement("div");
  d.className=`msg ${role==="user"?"user":"bot"}`;
  d.innerHTML=role==="bot"
    ?`<div class="msg-avatar">🤖</div><div class="msg-bubble">${html}</div>`
    :`<div class="msg-bubble">${esc(html)}</div>`;
  c.appendChild(d); c.scrollTop=c.scrollHeight;
}
function showTyping(){
  const c=document.getElementById("chat-messages");
  const d=document.createElement("div"); d.className="msg bot"; d.id="typing-indicator";
  d.innerHTML=`<div class="msg-avatar">🤖</div><div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  c.appendChild(d); c.scrollTop=c.scrollHeight;
}
function removeTyping(){ document.getElementById("typing-indicator")?.remove(); }
async function sendChat(){
  const input=document.getElementById("chat-input");
  const msg=input.value.trim(); if(!msg) return;
  input.value=""; appendMsg("user",msg); showTyping();
  try{
    const res=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message:msg,profile:currentProfile,recommendations:currentRecommendations})});
    const data=await res.json();
    removeTyping(); appendMsg("bot",data.reply||"Sorry, couldn't respond.");
  }catch{ removeTyping(); appendMsg("bot","⚠️ Network error. Try again."); }
}
function quickAsk(q){ document.getElementById("chat-input").value=q; sendChat(); }
function esc(s){ return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
document.addEventListener("DOMContentLoaded",()=>{
  document.getElementById("chat-input")?.addEventListener("keydown",e=>{ if(e.key==="Enter") sendChat(); });
});
