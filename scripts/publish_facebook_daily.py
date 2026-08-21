"""Publish AstroPratidin daily videos and scheduled major-transit alerts."""
from pathlib import Path
import datetime as dt
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request

OUT = Path("output")
UPLOADS = OUT / "youtube_uploads"
API_VERSION = os.environ.get("FB_API_VERSION", "v25.0")
GRAPH_VIDEO = f"https://graph-video.facebook.com/{API_VERSION}"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
RASHIS = [
    (1, "मेष", "मेष राशि"), (2, "वृषभ", "वृषभ राशि"),
    (3, "मिथुन", "मिथुन राशि"), (4, "कर्क", "कर्क राशि"),
    (5, "सिंह", "सिंह राशि"), (6, "कन्या", "कन्या राशि"),
    (7, "तुला", "तुला राशि"), (8, "वृश्चिक", "वृश्चिक राशि"),
    (9, "धनु", "धनु राशि"), (10, "मकर", "मकर राशि"),
    (11, "कुंभ", "कुंभ राशि"), (12, "मीन", "मीन राशि"),
]


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required GitHub Actions secret/environment variable: {name}")
    return value


def upload_video(page_id, token, path, title, description):
    url = f"{GRAPH_VIDEO}/{page_id}/videos"
    command = [
        "curl", "--fail-with-body", "--silent", "--show-error", "--location",
        "--request", "POST", url,
        "--form", f"source=@{path}",
        "--form", f"title={title}",
        "--form", f"description={description}",
        "--form", f"access_token={token}",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise RuntimeError(f"Facebook upload failed for {path.name}: {result.stdout[-4000:]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Facebook returned non-JSON for {path.name}: {result.stdout[-4000:]}") from exc
    video_id = data.get("id")
    if not video_id:
        raise RuntimeError(f"Facebook upload returned no video id for {path.name}: {data}")
    return video_id


def get_status(token, video_id):
    params = urllib.parse.urlencode({"fields": "id,status", "access_token": token})
    url = f"{GRAPH}/{video_id}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "AstroPratidin-GitHub-Actions/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def verify_video(token, video_id, timeout_seconds=900):
    deadline = time.time() + timeout_seconds
    last = None
    while time.time() < deadline:
        data = get_status(token, video_id)
        last = data
        status = data.get("status") or {}
        video_status = str(status.get("video_status") or status.get("status") or "").lower()
        print(f"FACEBOOK VERIFY {video_id}: video_status={video_status}")
        if video_status in {"error", "failed", "rejected"}:
            raise RuntimeError(f"Facebook processing failed for {video_id}: {data}")
        if video_status in {"ready", "published", "live", "complete", "completed"}:
            return
        time.sleep(15)
    raise RuntimeError(f"Facebook processing verification timed out for {video_id}: {last}")


def publication_date():
    path = OUT / "publication_date.txt"
    if not path.exists():
        raise SystemExit("publication_date.txt missing")
    return path.read_text(encoding="utf-8").strip()


def main():
    page_id = require_env("FB_PAGE_ID")
    token = require_env("FB_PAGE_ACCESS_TOKEN")
    target_date = publication_date()
    script = (OUT / "daily_script.md").read_text(encoding="utf-8")

    jobs = []
    combined = OUT / "daily_video.mp4"
    if not combined.exists():
        raise SystemExit("Combined daily video missing")
    jobs.append(("combined", None, combined,
                 f"आज का राशिफल | AstroPratidin | {target_date}",
                 "AstroPratidin — आपका दैनिक ज्योतिष साथी।\n\n" + script +
                 "\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल"))

    for index, key, label in RASHIS:
        path = UPLOADS / f"{index:02d}_{key}.mp4"
        if not path.exists():
            raise SystemExit(f"Individual Rashi video missing: {path}")
        jobs.append(("rashi", key, path,
                     f"आज का {label} राशिफल | AstroPratidin | {target_date}",
                     f"AstroPratidin — {label} के लिए {target_date} का दैनिक राशिफल।\n\n"
                     f"{key} राशि के ग्रह गोचर, संकेत और ज्योतिषीय मार्गदर्शन के लिए यह दैनिक वीडियो देखें।\n\n"
                     f"#AstroPratidin #{key}राशि #दैनिकराशिफल #ज्योतिष #राशिफल"))

    transit_manifest = OUT / "transit_video_manifest.json"
    if transit_manifest.exists():
        transit_data = json.loads(transit_manifest.read_text(encoding="utf-8"))
        for event in transit_data.get("events", []):
            path = Path(event["video_path"])
            if not path.exists():
                raise SystemExit(f"Transit video missing: {path}")
            jobs.append(("transit", event["id"], path,
                         f"7 दिन पहले: {event['description_hi']} | AstroPratidin",
                         f"AstroPratidin प्रमुख ग्रह गोचर अलर्ट।\n\n{event['description_hi']}। यह गोचर {event['occurrence_ist']} के आसपास होगा।\n\nयह विशेष वीडियो गोचर से सात दिन पहले प्रकाशित किया गया है।\n\n#AstroPratidin #ग्रहगोचर #ज्योतिष #TransitAlert"))

    results = []
    print(f"FACEBOOK PUBLISH PLAN: {len(jobs)} total = 13 daily + {len(jobs)-13} transit alert(s)")
    for kind, key, path, title, description in jobs:
        video_id = upload_video(page_id, token, path, title, description)
        print(f"FACEBOOK UPLOADED {kind} {key or 'combined'}: {video_id}")
        verify_video(token, video_id)
        results.append({"type": kind, "key": key, "video_id": video_id, "url": f"https://www.facebook.com/{video_id}"})

    manifest = OUT / "facebook_publish_manifest.json"
    manifest.write_text(json.dumps({
        "date": target_date,
        "page_id": page_id,
        "api_version": API_VERSION,
        "videos": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FACEBOOK PUBLISH: PASS — {len(results)} total videos")


if __name__ == "__main__":
    main()
