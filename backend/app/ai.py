import os,json,re,httpx
SYSTEM='''Return only JSON: {"changes":[{"section":"Summary|Skills|Projects|Experience|Education|Other","original_text":"exact substring from resume","proposed_text":"replacement","rationale":"reason"}]}. You are a conservative resume editor. Suggest at most 8 small, independently reviewable replacements. Every proposed claim must be supported by the supplied resume. Never invent skills, employers, dates, metrics, qualifications, or achievements. original_text must be an exact substring of the resume. Do not suggest additions or full resume rewrites. If no defensible edits exist, return an empty changes array.'''
def demo(resume,jd):
    lines=[x.strip() for x in resume.splitlines() if len(x.strip())>20]
    if not lines: return []
    return [{"section":"Manual review","original_text":lines[0],"proposed_text":lines[0],"rationale":"Demo mode: unchanged placeholder for review. Add an LLM API key to generate actual tailored suggestions."}]
async def generate(resume,jd):
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key: return demo(resume,jd),"demo"
    base=os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/")
    body={"model":os.getenv("OPENAI_MODEL","gpt-4o-mini"),"temperature":0.1,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps({"resume":resume[:24000],"job_description":jd[:18000]})}]}
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(base+"/chat/completions",headers={"Authorization":"Bearer "+key},json=body); r.raise_for_status()
    content=r.json()["choices"][0]["message"]["content"].strip()
    content=re.sub(r"^```(?:json)?\s*|\s*```$","",content,flags=re.I)
    data=json.loads(content); out=[]
    for x in data.get("changes",[])[:8]:
        old=str(x.get("original_text","")).strip(); new=str(x.get("proposed_text","")).strip()
        if old and new and old!=new and old in resume: out.append({"section":str(x.get("section","Other"))[:120],"original_text":old,"proposed_text":new,"rationale":str(x.get("rationale",""))[:1200]})
    return out,"llm"
