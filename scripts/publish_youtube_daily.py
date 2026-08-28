"""Publish AstroPratidin videos without exceeding the channel's daily upload allowance."""
from pathlib import Path
import datetime as dt
import json
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

OUT = Path("output")
UPLOADS = OUT / "youtube_uploads"
RASHIS = [(1,"मेष","मेष राशि"),(2,"वृषभ","वृषभ राशि"),(3,"मिथुन","मिथुन राशि"),(4,"कर्क","कर्क राशि"),(5,"सिंह","सिंह राशि"),(6,"कन्या","कन्या राशि"),(7,"तुला","तुला राशि"),(8,"वृश्चिक","वृश्चिक राशि"),(9,"धनु","धनु राशि"),(10,"मकर","मकर राशि"),(11,"कुंभ","कुंभ राशि"),(12,"मीन","मीन राशि")]


def upload_once(youtube, path, title, description, tags):
    body={"snippet":{"title":title[:100],"description":description[:4900],"categoryId":"22","tags":tags},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(str(path),mimetype="video/mp4",chunksize=8*1024*1024,resumable=True)
    request=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    response=None
    while response is None:
        status,response=request.next_chunk()
        if status: print(f"YouTube upload {path.name}: {int(status.progress()*100)}%")
    video_id=response.get("id")
    if not video_id: raise RuntimeError(f"YouTube upload returned no video ID for {path.name}")
    if response.get("status",{}).get("privacyStatus")!="public": raise RuntimeError(f"YouTube upload {video_id} was not public")
    return video_id


def upload(youtube,path,title,description,tags,attempts=3):
    for attempt in range(1,attempts+1):
        try:
            video_id=upload_once(youtube,path,title,description,tags)
            print(f"UPLOAD CONFIRMED attempt={attempt} file={path.name} id={video_id} privacy=public")
            return video_id
        except HttpError as exc:
            reason=""
            try: reason=exc.content.decode("utf-8",errors="replace")
            except Exception: pass
            if "uploadLimitExceeded" in reason:
                raise RuntimeError("YouTube daily upload limit reached; publication was intentionally stopped without retries") from exc
            if exc.resp.status not in {408,429,500,502,503,504} or attempt==attempts: raise
            print(f"YOUTUBE TRANSIENT RETRY attempt={attempt}/{attempts} file={path.name}; sleeping {20*attempt}s")
            time.sleep(20*attempt)
        except (OSError,TimeoutError,ConnectionError):
            if attempt==attempts: raise
            time.sleep(20*attempt)


def publication_date():
    path=OUT/"publication_date.txt"
    if not path.exists(): raise SystemExit("publication_date.txt missing")
    return path.read_text(encoding="utf-8").strip()


def load_youtube_credentials(raw):
    """Accept either Google OAuth authorized-user JSON or credentials.json-style {installed:{...}}."""
    try:
        data=json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ASTROPRATIDIN_YOUTUBE_TOKEN_JSON is not valid JSON: {exc}") from exc
    if isinstance(data,dict) and isinstance(data.get("installed"),dict):
        data=data["installed"]
    required=("client_id","client_secret","refresh_token")
    missing=[key for key in required if not data.get(key)]
    if missing:
        raise SystemExit("ASTROPRATIDIN_YOUTUBE_TOKEN_JSON missing required fields: " + ", ".join(missing))
    return Credentials.from_authorized_user_info(data,scopes=["https://www.googleapis.com/auth/youtube.upload"])


def main():
    raw=os.environ.get("YOUTUBE_TOKEN_JSON","")
    if not raw: raise SystemExit("Missing ASTROPRATIDIN_YOUTUBE_TOKEN_JSON repository secret")
    try: max_uploads=max(1,int(os.environ.get("YOUTUBE_MAX_DAILY_UPLOADS","1")))
    except ValueError: raise SystemExit("YOUTUBE_MAX_DAILY_UPLOADS must be a positive integer")
    creds=load_youtube_credentials(raw)
    youtube=build("youtube","v3",credentials=creds)
    target_date=publication_date(); script=(OUT/"daily_script.md").read_text(encoding="utf-8")
    jobs=[]; combined=OUT/"daily_video.mp4"
    if not combined.exists(): raise SystemExit("Combined daily video missing")
    jobs.append(("combined",None,combined,f"आज का राशिफल | AstroPratidin | {target_date}","AstroPratidin — आपका दैनिक ज्योतिष साथी।\n\n"+script+"\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल",["AstroPratidin","दैनिक राशिफल","राशिफल","ज्योतिष","आज का राशिफल"]))
    for index,key,label in RASHIS:
        path=UPLOADS/f"{index:02d}_{key}.mp4"
        if not path.exists(): raise SystemExit(f"Individual Rashi video missing: {path}")
        jobs.append(("rashi",key,path,f"आज का {label} राशिफल | AstroPratidin | {target_date}",f"AstroPratidin — {label} के लिए {target_date} का दैनिक राशिफल।",["AstroPratidin",label,f"{key} राशि","दैनिक राशिफल","ज्योतिष"]))
    transit_manifest=OUT/"transit_video_manifest.json"
    if transit_manifest.exists():
        for event in json.loads(transit_manifest.read_text(encoding="utf-8")).get("events",[]):
            path=Path(event["video_path"])
            if path.exists(): jobs.append(("transit",event["id"],path,f"7 दिन पहले: {event['description_hi']} | AstroPratidin",f"AstroPratidin प्रमुख ग्रह गोचर अलर्ट।\n\n{event['description_hi']}।",["AstroPratidin","ग्रह गोचर","ज्योतिष","Transit Alert",event["planet_hi"]]))
    planned=jobs[:max_uploads]
    print(f"YOUTUBE UPLOAD PLAN: publishing {len(planned)} of {len(jobs)} available videos; daily cap={max_uploads}")
    results=[]
    for kind,key,path,title,description,tags in planned:
        vid=upload(youtube,path,title,description,tags)
        results.append({"type":kind,"key":key,"video_id":vid,"url":f"https://www.youtube.com/watch?v={vid}"})
    (OUT/"youtube_publish_manifest.json").write_text(json.dumps({"date":target_date,"planned_total":len(jobs),"daily_cap":max_uploads,"videos":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"YOUTUBE PUBLISH: PASS — {len(results)} video(s) published within configured daily cap")

if __name__=="__main__": main()
