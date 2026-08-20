"""Audio-led devotional renderer for AstroPratidin."""
from pathlib import Path
import asyncio
import json
import re
import subprocess
import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageFont

OUT=Path("output"); SCENES=OUT/"video_scenes"; VOICE=OUT/"daily_voice.mp3"; VIDEO=OUT/"daily_video.mp4"; SEGDIR=OUT/"audio_segments"; MANIFEST=OUT/"sync_manifest.json"; POSTER=OUT/"video_poster.png"; SCRIPT=OUT/"daily_script.md"
ASSETS=Path("assets"); DEITY_ROOT=ASSETS/"deities"; INTRO_ASSET=ASSETS/"intro_devotional.jpg"; FONT_PATH=ASSETS/"NotoSansDevanagari-Regular.ttf"
W,H,FPS=1080,1920,30; VOICE_NAME="hi-IN-SwaraNeural"
RASHIS=[("मेष","मेष राशि","हनुमान जी","hanuman.jpg"),("वृषभ","वृषभ राशि","महालक्ष्मी जी","lakshmi.jpg"),("मिथुन","मिथुन राशि","श्री गणेश जी","ganesha.jpg"),("कर्क","कर्क राशि","भगवान शिव","shiva.jpg"),("सिंह","सिंह राशि","सूर्य देव","surya.jpg"),("कन्या","कन्या राशि","श्री गणेश जी","ganesha.jpg"),("तुला","तुला राशि","महालक्ष्मी जी","lakshmi.jpg"),("वृश्चिक","वृश्चिक राशि","हनुमान जी","hanuman.jpg"),("धनु","धनु राशि","भगवान विष्णु","vishnu.jpg"),("मकर","मकर राशि","शनि देव","shani.jpg"),("कुंभ","कुंभ राशि","शनि देव","shani.jpg"),("मीन","मीन राशि","भगवान विष्णु","vishnu.jpg")]
DEITIES={d:f for _,_,d,f in RASHIS}

def run(cmd,timeout=1800):
    print("RUN:"," ".join(str(x) for x in cmd)); r=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout); print(r.stdout[-8000:]);
    if r.returncode: raise RuntimeError(r.stdout[-12000:])

def media_duration(ffmpeg,path):
    r=subprocess.run([ffmpeg,"-i",str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60); m=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",r.stderr)
    if not m: raise RuntimeError(f"Cannot read media duration: {path}")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

async def speak(text,path): await edge_tts.Communicate(text,VOICE_NAME,rate="+5%",volume="+0%").save(str(path))
def clean(text): return " ".join(x.strip() for x in text.splitlines() if x.strip())
def load_script():
    if not SCRIPT.exists(): raise RuntimeError("output/daily_script.md was not generated")
    s=SCRIPT.read_text(encoding="utf-8").strip()
    if not s: raise RuntimeError("output/daily_script.md is empty")
    return s

def split_script(script):
    lines=script.splitlines(); starts=[]
    for idx,(key,label,deity,filename) in enumerate(RASHIS):
        hits=[i for i,line in enumerate(lines) if re.match(rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)",line)]
        if len(hits)!=1: raise RuntimeError(f"Expected exactly one {key} राशि heading; found {len(hits)}")
        starts.append((hits[0],idx,key,label))
    starts.sort()
    if [x[1] for x in starts]!=list(range(12)): raise RuntimeError("Rashi narration is not in canonical order")
    seg=[]; first=starts[0][0]; intro_text=clean("\n".join(lines[:first])) or "आज के दैनिक वैदिक ज्योतिष में बारहों राशियों के लिए ग्रह गोचर के संकेत जानिए।"; seg.append(("intro","प्रस्तावना",intro_text))
    for n,(line,idx,key,label) in enumerate(starts):
        end=starts[n+1][0] if n+1<len(starts) else len(lines); text=clean("\n".join(lines[line:end]))
        if not text: raise RuntimeError(f"Empty narration segment for {key}")
        seg.append((key,label,text))
    last_key,last_label,last_text=seg[-1]; m=re.search(r"(यह सामान्य चंद्र राशि आधारित.*)$",last_text,re.S)
    if m: seg[-1]=(last_key,last_label,clean(last_text[:m.start()])); outro=clean(m.group(1))
    else: outro="यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है। वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। कल फिर मिलेंगे। नमस्कार!"
    seg.append(("outro","समापन",outro))
    if len(seg)!=14 or any(not x[2] for x in seg): raise RuntimeError("Expected 14 non-empty narration segments")
    return seg

def reset_outputs():
    OUT.mkdir(exist_ok=True); SCENES.mkdir(exist_ok=True); SEGDIR.mkdir(exist_ok=True)
    for p in list(SCENES.glob("*"))+list(SEGDIR.glob("*")):
        if p.is_file(): p.unlink()
    for p in (VIDEO,VOICE,MANIFEST,POSTER):
        if p.exists(): p.unlink()

def validate_assets():
    if not FONT_PATH.exists(): raise RuntimeError(f"Missing bundled Devanagari font: {FONT_PATH}")
    result={}
    for deity,filename in DEITIES.items():
        path=DEITY_ROOT/filename
        if not path.exists(): raise RuntimeError(f"Missing deity artwork: {path}")
        with Image.open(path) as image:
            image=ImageOps.exif_transpose(image)
            if min(image.size)<1200: raise RuntimeError(f"Artwork below 1200px: {path} -> {image.size}")
        result[deity]=path
    if not INTRO_ASSET.exists(): raise RuntimeError(f"Missing intro artwork: {INTRO_ASSET}")
    return result

def font(size): return ImageFont.truetype(str(FONT_PATH),size)
def wrap(text,limit=38):
    result=[]; current=""
    for word in text.split():
        candidate=word if not current else current+" "+word
        if len(candidate)<=limit: current=candidate
        else:
            if current: result.append(current)
            current=word
    if current: result.append(current)
    return result

def fit(draw,text,max_width,size,minimum=20):
    for n in range(size,minimum-1,-2):
        f=font(n); b=draw.textbbox((0,0),text,font=f)
        if b[2]-b[0]<=max_width: return f
    return font(minimum)

def background(): return Image.new("RGBA",(W,H),(18,5,30,255))
def crop_cover(img,width,height):
    img=ImageOps.exif_transpose(img.convert("RGB")); scale=max(width/img.width,height/img.height); resized=img.resize((int(img.width*scale),int(img.height*scale)),Image.Resampling.LANCZOS); left=max(0,(resized.width-width)//2); top=max(0,(resized.height-height)//2); return resized.crop((left,top,left+width,top+height))
def put_hero(canvas,source,box,radius=34):
    left,top,right,bottom=box; width,height=right-left,bottom-top; image=crop_cover(source,width,height); image=ImageEnhance.Color(image).enhance(1.10); image=ImageEnhance.Contrast(image).enhance(1.04); mask=Image.new("L",(width,height),0); ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1),radius=radius,fill=255); canvas.paste(image,(left,top),mask)

def intro(script):
    output=SCENES/"000_intro.jpg"; source=ImageOps.exif_transpose(Image.open(INTRO_ASSET).convert("RGB")); canvas=background(); gold=(247,202,77,255); cream=(255,244,214,255); dark=(28,5,31,238); hero=crop_cover(source,W-70,1035); canvas.alpha_composite(hero.convert("RGBA"),(35,55)); draw=ImageDraw.Draw(canvas); draw.rounded_rectangle((22,22,W-22,H-22),radius=44,outline=gold,width=4); draw.rounded_rectangle((35,55,W-35,1090),radius=34,outline=(247,202,77,190),width=2)
    title="॥ दैनिक वैदिक ज्योतिष ॥"; title_font=fit(draw,title,W-120,62,40); box=draw.textbbox((0,0),title,font=title_font); draw.text(((W-box[2]+box[0])/2,1130),title,font=title_font,fill=cream)
    date=next((line.strip() for line in script.splitlines() if line.strip().startswith("आज ")),"आज का दैनिक राशिफल"); date_font=fit(draw,date,W-140,38,24); draw.rounded_rectangle((55,1215,W-55,1300),radius=28,fill=dark,outline=gold,width=2); box=draw.textbbox((0,0),date,font=date_font); draw.text(((W-box[2]+box[0])/2,1237),date,font=date_font,fill=cream)
    transition=next((line.strip() for line in script.splitlines() if "गोचर" in line or "प्रवेश" in line),"")
    if transition:
        draw.rounded_rectangle((55,1330,W-55,1555),radius=30,fill=dark,outline=gold,width=2); y=1360
        for line in wrap("आज का प्रमुख गोचर : "+transition,42)[:4]:
            line_font=fit(draw,line,W-130,30,22); box=draw.textbbox((0,0),line,font=line_font); draw.text(((W-box[2]+box[0])/2,y),line,font=line_font,fill=cream); y+=48
    hook="ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"; hook_font=fit(draw,hook,W-100,30,20); box=draw.textbbox((0,0),hook,font=hook_font); draw.text(((W-box[2]+box[0])/2,1620),hook,font=hook_font,fill=gold); subtitle="बारहों राशियों के लिए आज के ग्रह संकेत"; subtitle_font=fit(draw,subtitle,W-100,28,20); box=draw.textbbox((0,0),subtitle,font=subtitle_font); draw.text(((W-box[2]+box[0])/2,1725),subtitle,font=subtitle_font,fill=cream); canvas.convert("RGB").save(output,"JPEG",quality=98,subsampling=0); return output

def rashi_scene(index,key,label,deity,image_path,narration):
    output=SCENES/f"{index:03d}_{key}.jpg"; canvas=background(); draw=ImageDraw.Draw(canvas); gold=(247,202,77,255); cream=(255,244,214,255); dark=(28,5,31,238)
    with Image.open(image_path) as im: deity_img=ImageOps.exif_transpose(im.convert("RGB"))
    put_hero(canvas,deity_img,(35,55,W-35,1065),radius=34); draw.rounded_rectangle((35,55,W-35,1065),radius=34,outline=gold,width=3); badge=f"{index:02d}  •  {label}"; badge_font=fit(draw,badge,W-100,46,28); box=draw.textbbox((0,0),badge,font=badge_font); draw.rounded_rectangle((55,1110,W-55,1195),radius=28,fill=dark,outline=gold,width=2); draw.text(((W-box[2]+box[0])/2,1130),badge,font=badge_font,fill=cream); divider="✦  ॐ  ✦"; df=fit(draw,divider,W-120,32,22); box=draw.textbbox((0,0),divider,font=df); draw.text(((W-box[2]+box[0])/2,1230),divider,font=df,fill=gold); y=1290
    for line in wrap(narration,40)[:9]:
        lf=fit(draw,line,W-120,28,20); box=draw.textbbox((0,0),line,font=lf); draw.text(((W-box[2]+box[0])/2,y),line,font=lf,fill=cream); y+=48
    canvas.convert("RGB").save(output,"JPEG",quality=98,subsampling=0); return output

def outro():
    output=SCENES/"013_outro.jpg"; canvas=background(); draw=ImageDraw.Draw(canvas); gold=(247,202,77,255); cream=(255,244,214,255); draw.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4); om="ॐ"; omf=font(100); box=draw.textbbox((0,0),om,font=omf); draw.text(((W-box[2]+box[0])/2,390),om,font=omf,fill=gold); title="॥ शुभम् भवतु ॥"; tf=fit(draw,title,W-150,64,42); box=draw.textbbox((0,0),title,font=tf); draw.text(((W-box[2]+box[0])/2,610),title,font=tf,fill=cream); y=800
    for line in ["आपका दिन शुभ और मंगलमय हो","ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे","कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]:
        lf=fit(draw,line,W-180,34,24); box=draw.textbbox((0,0),line,font=lf); draw.text(((W-box[2]+box[0])/2,y),line,font=lf,fill=cream); y+=75
    canvas.convert("RGB").save(output,"JPEG",quality=98,subsampling=0); return output

def motion(ffmpeg,scene,seconds,index):
    output=SCENES/f"motion_{index:02d}.mp4"; seconds=max(0.5,float(seconds)); fade=min(0.28,max(0.10,seconds/6.0)); fade_out_start=max(0.05,seconds-fade); scale_w=int(W*1.08)//2*2; scale_h=int(H*1.08)//2*2
    filtergraph=f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=disable,crop={W}:{H}:x=(iw-{W})/2:y=(ih-{H})/2,fps={FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fade_out_start:.3f}:d={fade:.3f},setsar=1"
    run([ffmpeg,"-y","-loop","1","-i",scene,"-vf",filtergraph,"-t",f"{seconds:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-threads","2",output],900); return output

def concat_video(ffmpeg,clips):
    """Normalize every segment to identical geometry, pixel format and SAR before concat.

    GitHub runners can emit MP4 segments with SAR values such as 801:800 even
    when the coded dimensions are 1080x1920. FFmpeg concat rejects mixed SAR.
    Normalization here makes the assembly boundary deterministic regardless of
    which motion encoder produced each segment.
    """
    output=SCENES/"video_no_audio_sync.mp4"; args=[ffmpeg,"-y"]
    for clip in clips: args += ["-i",clip]
    normalized=";".join(f"[{i}:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v{i}]" for i in range(len(clips)))
    concat_inputs="".join(f"[v{i}]" for i in range(len(clips)))
    filtergraph=normalized+";"+concat_inputs+f"concat=n={len(clips)}:v=1:a=0,setsar=1[v]"
    args += ["-filter_complex",filtergraph,"-map","[v]","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",output]
    run(args,1800); return output

def concat_audio(ffmpeg,files):
    args=[ffmpeg,"-y"]; labels=[]
    for index,path in enumerate(files): args += ["-i",path]; labels.append(f"[{index}:a]")
    args += ["-filter_complex","".join(labels)+f"concat=n={len(files)}:v=0:a=1[a]","-map","[a]","-c:a","libmp3lame","-b:a","160k",VOICE]; run(args,1800)

def attach_audio(ffmpeg,silent_video,total):
    run([ffmpeg,"-y","-i",silent_video,"-i",VOICE,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-t",f"{total:.3f}",VIDEO],1800)

def main():
    reset_outputs(); script=load_script(); segments=split_script(script); ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(); deity_paths=validate_assets(); audio_files=[]; durations=[]; manifest=[]; cursor=0.0
    for index,(key,label,text) in enumerate(segments):
        path=SEGDIR/f"{index:02d}_{key}.mp3"; asyncio.run(speak(text,path)); seconds=media_duration(ffmpeg,path); audio_files.append(path); durations.append(seconds); manifest.append({"index":index,"key":key,"label":label,"start_seconds":round(cursor,3),"end_seconds":round(cursor+seconds,3),"audio_seconds":round(seconds,3),"text":text}); cursor+=seconds
    concat_audio(ffmpeg,audio_files); total_audio=media_duration(ffmpeg,VOICE); scenes=[intro(script)]
    for index,(key,label,deity,filename) in enumerate(RASHIS,start=1):
        narration=next(item[2] for item in segments if item[0]==key); scenes.append(rashi_scene(index,key,label,deity,deity_paths[deity],narration))
    scenes.append(outro())
    if len(scenes)!=len(segments): raise RuntimeError(f"Scene/voice count mismatch: {len(scenes)} vs {len(segments)}")
    clips=[]
    for index,(scene,seconds) in enumerate(zip(scenes,durations)):
        manifest[index]["scene"]=str(scene); manifest[index]["scene_seconds"]=round(seconds,3); clips.append(motion(ffmpeg,scene,seconds,index))
    silent_video=concat_video(ffmpeg,clips); attach_audio(ffmpeg,silent_video,total_audio); total_video=media_duration(ffmpeg,VIDEO); delta=abs(total_video-total_audio); print(f"AUDIO-LED SYNC: video={total_video:.3f}s audio={total_audio:.3f}s delta={delta:.3f}s")
    if delta>0.20: raise RuntimeError("FINAL AUDIO/VIDEO SYNC FAILED")
    Image.open(scenes[0]).save(POSTER,"PNG"); MANIFEST.write_text(json.dumps({"renderer":"V4-AUDIO-LED-DEVOTIONAL","method":"measured-TTS-segment-duration-is-master-timeline","total_audio_seconds":round(total_audio,3),"total_video_seconds":round(total_video,3),"segments":manifest},ensure_ascii=False,indent=2),encoding="utf-8"); print("PRODUCTION VIDEO COMPLETE")

if __name__=="__main__": main()
