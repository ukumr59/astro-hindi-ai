"""V4 production renderer: audio is the master timeline."""
from pathlib import Path
import asyncio,json,re,subprocess
import edge_tts,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageEnhance,ImageFilter,ImageOps
from . import render as base

VERSION="V4-AUDIO-LED-DEVOTIONAL"
OUT,SCENES,VOICE,VIDEO=base.OUTPUT,base.SCENES,base.VOICE,base.VIDEO
SEGDIR=OUT/"audio_segments"; MANIFEST=OUT/"sync_manifest.json"
W,H,FPS=base.WIDTH,base.HEIGHT,base.FPS
DEITIES={"हनुमान जी":"hanuman.jpg","महालक्ष्मी जी":"lakshmi.jpg","श्री गणेश जी":"ganesha.jpg","भगवान शिव":"shiva.jpg","सूर्य देव":"surya.jpg","भगवान विष्णु":"vishnu.jpg","शनि देव":"shani.jpg"}

def run(cmd,timeout=1800):
 r=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout); print(r.stdout[-5000:])
 if r.returncode: raise RuntimeError(r.stdout[-12000:])

def dur(ff,p):
 r=subprocess.run([ff,"-i",str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60); m=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",r.stderr)
 if not m: raise RuntimeError(f"Cannot read duration: {p}")
 return int(m[1])*3600+int(m[2])*60+float(m[3])

async def speak(text,path): await edge_tts.Communicate(text,base.VOICE_NAME,rate="+5%",volume="+0%").save(str(path))
def clean(t): return " ".join(x.strip() for x in t.splitlines() if x.strip())
def font(n): return base.get_font(n)
def fit(d,t,mw,n,mn=20):
 while n>=mn:
  f=font(n); b=d.textbbox((0,0),t,font=f)
  if b[2]-b[0]<=mw:return f
  n-=2
 return font(mn)
def wrap(t,n=38):
 a=[];c=""
 for w in t.split():
  q=w if not c else c+" "+w
  if len(q)<=n:c=q
  else:
   if c:a.append(c)
   c=w
 if c:a.append(c)
 return a

def split_script(s):
 lines=s.splitlines(); starts=[]
 for i,(k,l,d,q) in enumerate(base.RASHIS):
  hits=[n for n,x in enumerate(lines) if re.search(rf"^\s*{re.escape(k)}\s+राशि(?:[।:]|\s)",x)]
  if len(hits)!=1: raise RuntimeError(f"Expected one {k} heading; found {len(hits)}")
  starts.append((hits[0],i,k,l))
 starts.sort();
 if [x[1] for x in starts]!=list(range(12)): raise RuntimeError("Rashi headings are not in canonical order")
 seg=[("intro","प्रस्तावना",clean("\n".join(lines[:starts[0][0])))]
 for n,(line,idx,k,l) in enumerate(starts): seg.append((k,l,clean("\n".join(lines[line:(starts[n+1][0] if n+1<len(starts) else len(lines))]))))
 k,l,last=seg[-1]; m=re.search(r"(यह सामान्य चंद्र राशि आधारित.*)$",last,re.S)
 if m: seg[-1]=(k,l,clean(last[:m.start()])); outro=clean(m.group(1))
 else: outro="यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए जन्म कुंडली का अध्ययन आवश्यक होता है। वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। कल फिर मिलेंगे। नमस्कार!"
 seg.append(("outro","समापन",outro))
 if len(seg)!=14 or any(not x[2] for x in seg): raise RuntimeError("Expected 14 non-empty narration segments")
 return seg

def background():
 return Image.new("RGB",(W,H),(18,5,30)).convert("RGBA")
def put_hero(c,src,box):
 l,t,r,b=box; w,h=r-l,b-t; src=ImageOps.exif_transpose(src.convert("RGB")); im=base.crop_cover(src,w,h); im=ImageEnhance.Color(im).enhance(1.12); im=ImageEnhance.Contrast(im).enhance(1.05); mask=Image.new("L",(w,h)); d=ImageDraw.Draw(mask); d.rounded_rectangle((0,0,w-1,h-1),radius=40,fill=255); c.paste(im,(l,t),mask)

def intro(script):
 out=SCENES/"000_intro.jpg"; src=ImageOps.exif_transpose(Image.open(base.INTRO_ASSET).convert("RGB")); crop=src.crop((0,0,src.width,int(src.height*.52))); c=background(); d=ImageDraw.Draw(c); gold=(247,202,77,255); cream=(255,244,214,255); dark=(28,5,31,240)
 # ONE copy only: clean upper crop, no mirrored lower copy.
 hero=base.crop_cover(crop,W-100,1030); blur=hero.filter(ImageFilter.GaussianBlur(26)).convert("RGBA"); blur.putalpha(100); c.alpha_composite(blur,(50,90)); c.alpha_composite(hero.convert("RGBA"),(50,90))
 d=ImageDraw.Draw(c); d.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4)
 title="॥ दैनिक वैदिक ज्योतिष ॥"; f=fit(d,title,W-120,64,40); b=d.textbbox((0,0),title,font=f); d.text(((W-b[2]+b[0])/2,1185),title,font=f,fill=cream)
 date=next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")),"आज का दैनिक राशिफल"); f=fit(d,date,W-140,38,24); d.rounded_rectangle((65,1275,W-65,1360),radius=28,fill=dark,outline=gold,width=2); b=d.textbbox((0,0),date,font=f); d.text(((W-b[2]+b[0])/2,1298),date,font=f,fill=cream)
 tr=next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x),"")
 if tr:
  d.rounded_rectangle((55,1395,W-55,1615),radius=30,fill=dark,outline=gold,width=2); y=1420
  for line in wrap("आज का प्रमुख गोचर : "+tr,42)[:4]: f=fit(d,line,W-130,30,22); b=d.textbbox((0,0),line,font=f); d.text(((W-b[2]+b[0])/2,y),line,font=f,fill=cream); y+=48
 hook="ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"; f=fit(d,hook,W-100,30,20); b=d.textbbox((0,0),hook,font=f); d.text(((W-b[2]+b[0])/2,1660),hook,font=f,fill=gold)
 sub="बारहों राशियों के लिए आज के ग्रह संकेत"; f=fit(d,sub,W-100,28,20); b=d.textbbox((0,0),sub,font=f); d.text(((W-b[2]+b[0])/2,1770),sub,font=f,fill=cream); c.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out

def rashi(i,k,label,deity,path,text):
 out=SCENES/f"{i:03d}_{k}.jpg"; c=background(); d=ImageDraw.Draw(c); gold=(247,202,77,255); cream=(255,244,214,255); white=(255,250,242,255); panel=(12,4,24,242)
 d.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4); d.text((62,62),"ॐ",font=font(56),fill=gold); f=fit(d,label,W-250,62,40); b=d.textbbox((0,0),label,font=f); d.text(((W-b[2]+b[0])/2,70),label,font=f,fill=cream); d.text((W-120,62),"ॐ",font=font(56),fill=gold)
 put_hero(c,Image.open(path),(50,180,W-50,1030)); d=ImageDraw.Draw(c); d.rounded_rectangle((50,180,W-50,1030),radius=40,outline=gold,width=4)
 # Deliberately NO deity name under the photograph.
 d.rounded_rectangle((50,1090,W-50,1785),radius=32,fill=panel,outline=(208,164,62,230),width=2); head="आज के ग्रह संकेत"; f=fit(d,head,W-160,34,24); b=d.textbbox((0,0),head,font=f); d.text(((W-b[2]+b[0])/2,1130),head,font=f,fill=gold)
 body=re.sub(rf"^\s*{re.escape(k)}\s+राशि[।:\s]*","",text).strip(); y=1190
 for line in wrap(body,38)[:15]: d.text((90,y),line,font=font(29),fill=white); y+=39
 foot="आज के लिए धैर्य • कर्म • विश्वास • सकारात्मक सोच"; f=fit(d,foot,W-120,24,18); b=d.textbbox((0,0),foot,font=f); d.text(((W-b[2]+b[0])/2,1840),foot,font=f,fill=gold); c.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out

def outro():
 out=SCENES/"999_outro.jpg"; c=background(); d=ImageDraw.Draw(c); gold=(247,202,77,255); cream=(255,244,214,255); d.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4); d.text((W//2-55,410),"ॐ",font=font(100),fill=gold); t="॥ शुभम् भवतु ॥"; f=fit(d,t,W-150,64,42); b=d.textbbox((0,0),t,font=f); d.text(((W-b[2]+b[0])/2,610),t,font=f,fill=cream); y=800
 for line in ["आपका दिन शुभ और मंगलमय हो","ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे","कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]: f=fit(d,line,W-180,34,24); b=d.textbbox((0,0),line,font=f); d.text(((W-b[2]+b[0])/2,y),line,font=f,fill=cream); y+=75
 c.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out

def motion(ff,scene,sec,i):
 out=SCENES/f"motion_{i:02d}.mp4"; frames=max(2,round(sec*FPS)); z="min(1.13,1+0.00010*on)"; x=f"(iw-iw/zoom)*({'on' if i%2==0 else f'({frames}-on)'}/{frames})"; y="(ih-ih/zoom)/2"; fi=min(.28,max(.10,sec/6)); fo=max(.05,sec-fi); vf=f"zoompan=z={z}:x={x}:y={y}:d={frames}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d={fi:.3f},fade=t=out:st={fo:.3f}:d={fi:.3f}"; run([ff,"-y","-loop","1","-i",scene,"-vf",vf,"-t",f"{sec:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",out],900); return out

def concatv(ff,clips):
 out=SCENES/"video_no_audio_sync.mp4"; a=[ff,"-y"]; labs=[]
 for i,p in enumerate(clips): a += ["-i",p]; labs.append(f"[{i}:v]")
 a += ["-filter_complex","".join(labs)+f"concat=n={len(clips)}:v=1:a=0[v]","-map","[v]","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",out]; run(a,1800); return out

def concata(ff,files):
 a=[ff,"-y"]; labs=[]
 for i,p in enumerate(files): a += ["-i",p]; labs.append(f"[{i}:a]")
 a += ["-filter_complex","".join(labs)+f"concat=n={len(files)}:v=0:a=1[a]","-map","[a]","-c:a","libmp3lame","-b:a","160k",VOICE]; run(a,1800)

def attach(ff,silent,total): run([ff,"-y","-i",silent,"-i",VOICE,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-t",f"{total:.3f}",VIDEO],1800)

def assets():
 root=Path("assets/deities"); out={}
 for deity,file in DEITIES.items():
  p=root/file
  if not p.exists(): raise RuntimeError(f"Missing deity artwork: {p}")
  with Image.open(p) as im:
   im=ImageOps.exif_transpose(im); print(f"HD deity asset {deity}: {im.size}")
   if min(im.size)<1200: raise RuntimeError(f"Deity artwork too small: {p} -> {im.size}")
  out[deity]=p
 return out

def main():
 OUT.mkdir(exist_ok=True); SCENES.mkdir(exist_ok=True); SEGDIR.mkdir(exist_ok=True)
 # Hard-clean every generated video/audio scene so no previous renderer output survives.
 for p in list(SCENES.glob("*"))+list(SEGDIR.glob("*")):
  if p.is_file():
   try:p.unlink()
   except:pass
 for p in [VIDEO,VOICE,MANIFEST,OUT/"video_poster.png"]:
  if p.exists(): p.unlink()
 script=base.load_script(); seg=split_script(script); ff=imageio_ffmpeg.get_ffmpeg_exe(); paths=assets(); aud=[]; seconds=[]; manifest=[]; cursor=0.0
 for i,(k,label,text) in enumerate(seg):
  p=SEGDIR/f"{i:02d}_{k}.mp3"; print(f"TTS {i+1}/14 {label}"); asyncio.run(speak(text,p)); s=dur(ff,p); aud.append(p); seconds.append(s); manifest.append({"index":i,"key":k,"label":label,"start_seconds":round(cursor,3),"end_seconds":round(cursor+s,3),"audio_seconds":round(s,3),"text":text}); cursor+=s
 concata(ff,aud); total=dur(ff,VOICE)
 scenes=[intro(script)]
 for i,(k,label,deity,q) in enumerate(base.RASHIS,1): scenes.append(rashi(i,k,label,deity,paths[deity],next(x[2] for x in seg if x[0]==k)))
 scenes.append(outro())
 if len(scenes)!=14: raise RuntimeError("Renderer must produce exactly 14 scenes")
 clips=[]
 for i,(scene,s) in enumerate(zip(scenes,seconds)): manifest[i]["scene"]=str(scene); manifest[i]["scene_seconds"]=round(s,3); clips.append(motion(ff,scene,s,i))
 silent=concatv(ff,clips); attach(ff,silent,total); vtotal=dur(ff,VIDEO); delta=abs(vtotal-total); print(f"{VERSION}: video={vtotal:.3f}s audio={total:.3f}s delta={delta:.3f}s")
 if delta>.20: raise RuntimeError("FINAL AUDIO/VIDEO SYNC FAILED")
 Image.open(scenes[0]).save(OUT/"video_poster.png","PNG")
 MANIFEST.write_text(json.dumps({"renderer":VERSION,"method":"exact-audio-segment-boundaries","transition":"fade-in/out inside each segment; zero overlap","total_audio_seconds":round(total,3),"total_video_seconds":round(vtotal,3),"segments":manifest},ensure_ascii=False,indent=2),encoding="utf-8")
 print("PRODUCTION VIDEO COMPLETE")

if __name__=="__main__": main()
