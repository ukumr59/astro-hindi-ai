"""Publish the AstroPratidin daily set and scheduled major-transit alerts.

Daily output: 1 combined 12-Rashi video + 12 individual Rashi videos.
Additionally, one advance-alert video is published for each major transit
whose occurrence is exactly seven calendar days after the current IST date.
"""
from pathlib import Path
import datetime as dt
import json
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

OUT = Path("output")
UPLOADS = OUT / "youtube_uploads"
TRANSIT_OUT = OUT / "transit_uploads"
RASHIS = [
    (1, "मेष", "मेष राशि"), (2, "वृषभ", "वृषभ राशि"),
    (3, "मिथुन", "मिथुन राशि"), (4, "कर्क", "कर्क राशि"),
    (5, "सिंह", "सिंह राशि"), (6, "कन्या", "कन्या राशि"),
    (7, "तुला", "तुला राशि"), (8, "वृश्चिक", "वृश्चिक राशि"),
    (9, "धनु", "धनु राशि"), (10, "मकर", "मकर राशि"),
    (11, "कुंभ", "कुंभ राशि"), (12, "मीन", "मीन राशि"),
]


def upload(youtube, path, title, description, tags):
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "categoryId": "22", "tags": tags},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"YouTube upload {path.name}: {int(status.progress() * 100)}%")
    return response["id"]


def verify_processing(youtube, video_id, timeout_seconds=900):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        item = youtube.videos().list(part="status,processingDetails", id=video_id).execute().get("items", [])
        if not item:
            raise RuntimeError(f"YouTube video disappeared after upload: {video_id}")
        video = item[0]
        status = video.get("status", {})
        processing = video.get("processingDetails", {})
        upload_status = status.get("uploadStatus")
        processing_status = processing.get("processingStatus")
        print(f"VERIFY {video_id}: uploadStatus={upload_status} processingStatus={processing_status} privacy={status.get('privacyStatus')}")
        if upload_status in {"failed", "rejected"}:
            raise RuntimeError(f"YouTube upload failed for {video_id}: {status.get('failureReason') or status.get('rejectionReason')}")
        if processing_status == "failed":
            raise RuntimeError(f"YouTube processing failed for {video_id}: {processing.get('processingFailureReason')}")
        if upload_status == "processed" and processing_status == "succeeded":
            if status.get("privacyStatus") != "public":
                raise RuntimeError(f"YouTube privacy status is {status.get('privacyStatus')}, expected public")
            return
        time.sleep(15)
    raise RuntimeError(f"YouTube processing verification timed out for {video_id}")


def publication_date():
    path = OUT / "publication_date.txt"
    if not path.exists():
        raise SystemExit("publication_date.txt missing")
    return path.read_text(encoding="utf-8").strip()


def main():
    raw = os.environ.get("YOUTUBE_TOKEN_JSON", "")
    if not raw:
        raise SystemExit("Missing ASTROPRATIDIN_YOUTUBE_TOKEN_JSON repository secret")
    token = json.loads(raw)
    creds = Credentials.from_authorized_user_info(token, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)
    target_date = publication_date()
    script = (OUT / "daily_script.md").read_text(encoding="utf-8")
    base_description = "AstroPratidin — आपका दैनिक ज्योतिष साथी।\n\n"
    jobs = []

    combined = OUT / "daily_video.mp4"
    if not combined.exists():
        raise SystemExit("Combined daily video missing")
    jobs.append(("combined", None, combined,
                 f"आज का राशिफल | AstroPratidin | {target_date}",
                 base_description + script + "\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल",
                 ["AstroPratidin", "दैनिक राशिफल", "राशिफल", "ज्योतिष", "आज का राशिफल"]))

    for index, key, label in RASHIS:
        path = UPLOADS / f"{index:02d}_{key}.mp4"
        if not path.exists():
            raise SystemExit(f"Individual Rashi video missing: {path}")
        description = (
            f"AstroPratidin — {label} के लिए {target_date} का दैनिक राशिफल।\n\n"
            f"{key} राशि के ग्रह गोचर, संकेत और ज्योतिषीय मार्गदर्शन के लिए यह दैनिक वीडियो देखें।\n\n"
            f"#AstroPratidin #{key}राशि #दैनिकराशिफल #ज्योतिष #राशिफल"
        )
        jobs.append(("rashi", key, path, f"आज का {label} राशिफल | AstroPratidin | {target_date}", description,
                     ["AstroPratidin", label, f"{key} राशि", "दैनिक राशिफल", "ज्योतिष"]))

    transit_manifest = OUT / "transit_video_manifest.json"
    if transit_manifest.exists():
        transit_data = json.loads(transit_manifest.read_text(encoding="utf-8"))
        for event in transit_data.get("events", []):
            path = Path(event["video_path"])
            if not path.exists():
                raise SystemExit(f"Transit video missing: {path}")
            occurrence = dt.datetime.fromisoformat(event["occurrence_ist"]).astimezone(dt.timezone.utc)
            jobs.append(("transit", event["id"], path,
                         f"7 दिन पहले: {event['description_hi']} | AstroPratidin",
                         f"AstroPratidin प्रमुख ग्रह गोचर अलर्ट।\n\n{event['description_hi']}। यह गोचर {occurrence.strftime('%d-%m-%Y %H:%M UTC')} के आसपास होगा।\n\nयह विशेष वीडियो गोचर से सात दिन पहले प्रकाशित किया गया है।\n\n#AstroPratidin #ग्रहगोचर #ज्योतिष #TransitAlert",
                         ["AstroPratidin", "ग्रह गोचर", "ज्योतिष", "Transit Alert", event["planet_hi"]]))

    results = []
    print(f"YOUTUBE UPLOAD PLAN: {len(jobs)} total = 13 daily + {len(jobs)-13} transit alert(s)")
    for kind, key, path, title, description, tags in jobs:
        vid = upload(youtube, path, title, description, tags)
        print(f"UPLOADED {kind} {key or 'combined'}: {vid}")
        results.append({"type": kind, "key": key, "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}"})

    print(f"VERIFYING {len(results)} YOUTUBE UPLOADS")
    for result in results:
        verify_processing(youtube, result["video_id"])

    manifest = OUT / "youtube_publish_manifest.json"
    manifest.write_text(json.dumps({"date": target_date, "videos": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"YOUTUBE PUBLISH: PASS — {len(results)} total videos")


if __name__ == "__main__":
    main()
