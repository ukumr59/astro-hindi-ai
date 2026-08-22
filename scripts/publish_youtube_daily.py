"""Publish the AstroPratidin daily set and scheduled major-transit alerts reliably."""
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
    privacy=response.get("status",{}).get("privacyStatus")
    if not video_id: raise RuntimeError(f"YouTube upload returned no video ID for {path.name}")
    if privacy!="public": raise RuntimeError(f"YouTube upload {video_id} returned privacy={privacy}")
    return video_id


def upload(youtube,path,title,description,tags,attempts=3):
    last=None
    for attempt in range(1,attempts+1):
        try:
            video_id=upload_once(youtube,path,title,description,tags)
            print(f"UPLOAD CONFIRMED attempt={attempt} file={path.name} id={video_id} privacy=public")
            return video_id
        except HttpError as exc:
            # Retry only transient server/rate-limit failures. Authentication and
            # validation errors must surface immediately rather than duplicate posts.
            last=exc
            if exc.resp.status not in {408,429,500,502,503,504} or attempt==attempts: raise
        except (OSError,TimeoutError,ConnectionError) as exc:
            last=exc
            if attempt==attempts: raise
        delay=20*attempt
        print(f"YOUTUBE UPLOAD RETRY attempt={attempt}/{attempts} file={path.name} error={last}; sleeping {delay}s")
        time.sleep(delay)
    raise RuntimeError(f"YouTube upload exhausted retries for {path.name}: {last}")


def publication_date():
    path=OUT/"publication_date.txt"
    if not path.exists(): raise SystemExit("publication_date.txt missing")
    return path.read_text(encoding="utf-8").strip()


def main():
    raw=os.environ.get("YOUTUBE_TOKEN_JSON","")
    if not raw: raise SystemExit("Missing ASTROPRATIDIN_YOUTUBE_TOKEN_JSON repository secret")
    creds=Credentials.from_authorized_user_info(json.loads(raw),scopes=["https://www.googleapis.com/auth/youtube.upload"])
    youtube=build("youtube","v3",credentials=creds)
    target_date=publication_date()
    script=(OUT/"daily_script.md").read_text(encoding="utf-8")
    jobs=[]
    combined=OUT/"daily_video.mp4"
    if not combined.exists(): raise SystemExit("Combined daily video missing")
    jobs.append(("combined",None,combined,f"आज का राशिफल | AstroPratidin | {target_date}","AstroPratidin — आपका दैनिक ज्योतिष साथी।\n\n"+script+"\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल",["AstroPratidin","दैनिक राशिफल","राशिफल","ज्योतिष","आज का राशिफल"]))
    for index,key,label in RASHIS:
        path=UPLOADS/f"{index:02d}_{key}.mp4"
        if not path.exists(): raise SystemExit(f"Individual Rashi video missing: {path}")
        description=f"AstroPratidin — {label} के लिए {target_date} का दैनिक राशिफल।\n\n{key} राशि के ग्रह गोचर, संकेत और ज्योतिषीय मार्गदर्शन के लिए यह दैनिक वीडियो देखें।\n\n#AstroPratidin #{key}राशि #दैनिकराशिफल #ज्योतिष #राशिफल"
        jobs.append(("rashi",key,path,f"आज का {label} राशिफल | AstroPratidin | {target_date}",description,["AstroPratidin",label,f"{key} राशि","दैनिक राशिफल","ज्योतिष"]))
    transit_manifest=OUT/"transit_video_manifest.json"
    if transit_manifest.exists():
        for event in json.loads(transit_manifest.read_text(encoding="utf-8")).get("events",[]):
            path=Path(event["video_path"])
            if not path.exists(): raise SystemExit(f"Transit video missing: {path}")
            occurrence=dt.datetime.fromisoformat(event["occurrence_ist"]).astimezone(dt.timezone.utc)
            jobs.append(("transit",event["id"],path,f"7 दिन पहले: {event['description_hi']} | AstroPratidin",f"AstroPratidin प्रमुख ग्रह गोचर अलर्ट।\n\n{event['description_hi']}। यह गोचर {occurrence.strftime('%d-%m-%Y %H:%M UTC')} के आसपास होगा।\n\nयह विशेष वीडियो गोचर से सात दिन पहले प्रकाशित किया गया है।\n\n#AstroPratidin #ग्रहगोचर #ज्योतिष #TransitAlert",["AstroPratidin","ग्रह गोचर","ज्योतिष","Transit Alert",event["planet_hi"]]))
    results=[]
    print(f"YOUTUBE UPLOAD PLAN: {len(jobs)} total = 13 daily + {len(jobs)-13} transit alert(s)")
    for kind,key,path,title,description,tags in jobs:
        vid=upload(youtube,path,title,description,tags)
        results.append({"type":kind,"key":key,"video_id":vid,"url":f"https://www.youtube.com/watch?v={vid}"})
    (OUT/"youtube_publish_manifest.json").write_text(json.dumps({"date":target_date,"videos":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"YOUTUBE PUBLISH: PASS — {len(results)} total videos")

if __name__=="__main__": main()
