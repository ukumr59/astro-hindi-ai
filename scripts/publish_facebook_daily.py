"""Publish AstroPratidin videos reliably with a conservative daily cap."""
from pathlib import Path
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
import urllib.error

OUT=Path("output"); UPLOADS=OUT/"youtube_uploads"
API_VERSION=os.environ.get("FB_API_VERSION","v25.0")
GRAPH_VIDEO=f"https://graph-video.facebook.com/{API_VERSION}"; GRAPH_API=f"https://graph.facebook.com/{API_VERSION}"
RASHIS=[(1,"मेष","मेष राशि"),(2,"वृषभ","वृषभ राशि"),(3,"मिथुन","मिथुन राशि"),(4,"कर्क","कर्क राशि"),(5,"सिंह","सिंह राशि"),(6,"कन्या","कन्या राशि"),(7,"तुला","तुला राशि"),(8,"वृश्चिक","वृश्चिक राशि"),(9,"धनु","धनु राशि"),(10,"मकर","मकर राशि"),(11,"कुंभ","कुंभ राशि"),(12,"मीन","मीन राशि")]

def require_env(name):
    value=os.environ.get(name,"").strip()
    if not value: raise SystemExit(f"Missing required GitHub Actions secret/environment variable: {name}")
    return value

def api_json(url):
    try:
        with urllib.request.urlopen(url,timeout=30) as response: return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body=exc.read().decode("utf-8",errors="replace")
        if '"code":190' in body or '"error_subcode":463' in body:
            raise SystemExit("Facebook access token is expired or invalid. Update META_ACCESS_TOKEN with a valid Page/System User token and rerun.") from exc
        raise SystemExit(f"Facebook API validation failed: HTTP {exc.code}: {body[-1500:]}") from exc

def validate_page_access(page_id,token):
    data=api_json(f"{GRAPH_API}/{page_id}?fields=id,name&access_token={urllib.parse.quote(token,safe='')}")
    if str(data.get("id",""))!=str(page_id): raise SystemExit(f"Facebook token/page mismatch: expected page {page_id}, got {data}")
    print("FACEBOOK TOKEN VALIDATION: PASS")

def resolve_page_id(token):
    configured=os.environ.get("FB_PAGE_ID","").strip()
    if configured: return configured
    data=api_json(f"{GRAPH_API}/me?fields=id&access_token={urllib.parse.quote(token,safe='')}")
    page_id=str(data.get("id","")).strip()
    if not page_id: raise SystemExit(f"Facebook /me returned no page id: {data}")
    return page_id

def upload_once(page_id,token,path,title,description):
    command=["curl","--fail-with-body","--silent","--show-error","--location","--connect-timeout","30","--max-time","1800","--request","POST",f"{GRAPH_VIDEO}/{page_id}/videos","--form",f"source=@{path}","--form",f"title={title}","--form",f"description={description}","--form","published=true","--form",f"access_token={token}"]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if result.returncode: raise RuntimeError(f"Facebook upload failed for {path.name}: {result.stdout[-4000:]}")
    data=json.loads(result.stdout); video_id=data.get("id")
    if not video_id: raise RuntimeError(f"Facebook upload returned no video id for {path.name}: {data}")
    return video_id

def verify_discoverable(video_id,token,attempts=12):
    last=None
    for attempt in range(1,attempts+1):
        try:
            data=api_json(f"{GRAPH_API}/{video_id}?fields=id,permalink_url&access_token={urllib.parse.quote(token,safe='')}")
            if data.get("permalink_url"): return data["permalink_url"]
            last=str(data)
        except Exception as exc: last=str(exc)
        if attempt<attempts: time.sleep(10)
    raise RuntimeError(f"Facebook video {video_id} was uploaded but did not become discoverable: {last}")

def upload_video(page_id,token,path,title,description,attempts=3):
    last=None
    for attempt in range(1,attempts+1):
        try:
            video_id=upload_once(page_id,token,path,title,description); permalink=verify_discoverable(video_id,token)
            print(f"FACEBOOK UPLOAD SUCCESS attempt={attempt} file={path.name} id={video_id}"); return video_id,permalink
        except Exception as exc:
            last=exc
            if "code\":190" in str(exc) or "error_subcode\":463" in str(exc): raise
            if attempt<attempts: time.sleep(20*attempt)
    raise RuntimeError(f"Facebook upload exhausted retries for {path.name}: {last}")

def publication_date():
    path=OUT/"publication_date.txt"
    if not path.exists(): raise SystemExit("publication_date.txt missing")
    return path.read_text(encoding="utf-8").strip()

def main():
    token=require_env("FB_PAGE_ACCESS_TOKEN"); page_id=resolve_page_id(token); validate_page_access(page_id,token)
    try: max_uploads=max(1,int(os.environ.get("FACEBOOK_MAX_DAILY_UPLOADS","1")))
    except ValueError: raise SystemExit("FACEBOOK_MAX_DAILY_UPLOADS must be a positive integer")
    target_date=publication_date(); script=(OUT/"daily_script.md").read_text(encoding="utf-8"); jobs=[]
    combined=OUT/"daily_video.mp4"
    if not combined.exists(): raise SystemExit("Combined daily video missing")
    jobs.append(("combined",None,combined,f"आज का राशिफल | AstroPratidin | {target_date}","AstroPratidin — आपका दैनिक ज्योतिष साथी。\n\n"+script+"\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल"))
    for index,key,label in RASHIS:
        path=UPLOADS/f"{index:02d}_{key}.mp4"
        if path.exists(): jobs.append(("rashi",key,path,f"आज का {label} राशिफल | AstroPratidin | {target_date}",f"AstroPratidin — {label} के लिए {target_date} का दैनिक राशिफल।"))
    planned=jobs[:max_uploads]
    results=[]; print(f"FACEBOOK PUBLISH PLAN: publishing {len(planned)} of {len(jobs)} available videos; daily cap={max_uploads}")
    for kind,key,path,title,description in planned:
        video_id,permalink=upload_video(page_id,token,path,title,description); results.append({"type":kind,"key":key,"video_id":video_id,"url":permalink})
    (OUT/"facebook_publish_manifest.json").write_text(json.dumps({"date":target_date,"page_id":page_id,"api_version":API_VERSION,"planned_total":len(jobs),"daily_cap":max_uploads,"videos":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"FACEBOOK PUBLISH: PASS — {len(results)} video(s) published within configured daily cap")
if __name__=="__main__": main()
