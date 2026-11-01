import numpy as np, math, sys, wave, subprocess
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageChops

W,H=1080,1920; FPS=30; DUR=23.4
GOLD=(255,201,51); WHITE=(255,255,255); NAVY=(10,16,40); RED=(232,60,60)
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
def kri(p):
    for i in range(8):
        try:
            if 'KR' in ''.join(ImageFont.truetype(p,20,index=i).getname()): return i
        except Exception: pass
    return 0
KB,KD=kri(FB),kri(FD)
@lru_cache(None)
def font(size,bold):
    return ImageFont.truetype(FB if bold else FD,size,index=KB if bold else KD)

@lru_cache(None)
def T(text,size,color=WHITE,bold=True,stroke=0,sc=(0,0,0),spacing=10):
    f=font(size,bold); pad=stroke+6
    tmp=Image.new('L',(10,10)); d=ImageDraw.Draw(tmp)
    bb=d.multiline_textbbox((0,0),text,font=f,spacing=spacing,align='center',stroke_width=stroke)
    w,h=int(bb[2]-bb[0])+pad*2,int(bb[3]-bb[1])+pad*2
    im=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.multiline_text((int(pad-bb[0]),int(pad-bb[1])),text,font=f,fill=color,spacing=spacing,align='center',stroke_width=stroke,stroke_fill=sc)
    return im

def put(base,layer,cx,cy,a=1.0,s=1.0,rot=0):
    if a<=0.01 or s<=0.01: return
    im=layer
    if s!=1.0: im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.BILINEAR)
    if rot: im=im.rotate(rot,expand=True,resample=Image.BICUBIC)
    if a<1.0:
        im=im.copy(); al=im.getchannel('A').point(lambda v:int(v*a)); im.putalpha(al)
    base.paste(im,(int(cx-im.width/2),int(cy-im.height/2)),im)

def eob(x):
    c1=1.70158;c3=c1+1
    return 1+c3*(x-1)**3+c1*(x-1)**2
def pop(t,t0,dur=0.3):
    if t<t0: return 0,0
    x=min(1,(t-t0)/dur); return min(1,x*3), 0.5+0.5*eob(x)
def fade(t,t0,dur=0.25):
    return 0 if t<t0 else min(1,(t-t0)/dur)

# ---------- background
def make_bg():
    y=np.linspace(0,1,H)[:,None]; x=np.linspace(-1,1,W)[None,:]
    top=np.array([2,5,18]);bot=np.array([20,26,52])
    g=(top[None,None,:]*(1-y[...,None])+bot[None,None,:]*y[...,None])*np.ones((H,W,3))
    # 희미한 야구장 느낌: 아래쪽 잔디빛 + 비네트
    glow=np.exp(-((y-0.78)**2)/0.02)*np.exp(-(x**2)/1.2)
    g+=glow[...,None]*np.array([18,26,14])
    v=1-0.35*(x**2)
    g*=v[...,None]
    rng=np.random.default_rng(3)
    for _ in range(70):
        sx,sy=rng.integers(0,W),rng.integers(0,int(H*0.55))
        g[sy:sy+3,sx:sx+3]=np.maximum(g[sy:sy+3,sx:sx+3],rng.integers(90,200))
    return Image.fromarray(np.clip(g,0,255).astype(np.uint8)).convert('RGBA')
BG=make_bg()

# ---------- sprites
SPR=["...CCCCCC...","..CCCCCCCC..","..CCCCCCCCBB","..SSSSSSSS..","..SESSSSES..","..SSSSSSSS..",
     "...SSSSSS...","..TTTTTTTT..",".STTTWWTTTS.",".STTTWWTTTS.",".STTTTTTTTS.","..TTTTTTTT..",
     "..PPPPPPPP..","..PPP..PPP..","..PPP..PPP..","..DDD..DDD.."]
TEAMS={'green':((46,125,70),(240,240,240),(60,60,70)),'red':((220,50,50),(240,240,240),(60,60,70)),
       'navy':((30,36,70),(240,240,240),(30,30,40)),'black':((30,30,34),(240,240,240),(40,40,50)),
       'orange':((240,120,30),(240,240,240),(60,60,70))}
@lru_cache(None)
def sprite(team,scale=14):
    c,shirt,pants=TEAMS[team]
    pal={'C':c,'B':tuple(max(0,v-40) for v in c),'S':(245,200,160),'E':(30,30,40),'T':shirt,'W':c,'P':pants,'D':(20,20,25)}
    im=Image.new('RGBA',(12*scale,16*scale),(0,0,0,0)); d=ImageDraw.Draw(im)
    for yy,row in enumerate(SPR):
        for xx,ch in enumerate(row):
            if ch!='.': d.rectangle([xx*scale,yy*scale,(xx+1)*scale-1,(yy+1)*scale-1],fill=pal[ch]+(255,))
    return im
HEART=[".XX.XX.","XXXXXXX","XXXXXXX",".XXXXX.","..XXX..","...X..."]
@lru_cache(None)
def heart(scale=10,color=(255,205,60)):
    im=Image.new('RGBA',(7*scale,6*scale),(0,0,0,0)); d=ImageDraw.Draw(im)
    for yy,r in enumerate(HEART):
        for xx,ch in enumerate(r):
            if ch=='X': d.rectangle([xx*scale,yy*scale,(xx+1)*scale-1,(yy+1)*scale-1],fill=color+(255,))
    return im

def rrect(w,h,r,fill,outline=None,ow=0):
    im=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rounded_rectangle([0,0,w-1,h-1],r,fill=fill,outline=outline,width=ow); return im
@lru_cache(None)
def chip(text,size,fill,tc):
    t=T(text,size,tc); w,h=t.width+60,t.height+26
    im=rrect(w,h,h//2,fill); im.paste(t,((w-t.width)//2,(h-t.height)//2),t); return im

# ---------- receipt
LINES=[("이용료","0원",None),("설치","0원",None),("회원가입","0원",None),("광고","0개",None),
       ("개발 기간","3일",None),("커밋","67번",None),("새벽 3시 34분 작업","1회",None),("서버비","개발자 부담",RED)]
R0=3.9; RS=0.55
def receipt(t):
    n=min(len(LINES),max(0,int((t-R0)/RS)+1)) if t>=R0 else 0
    tot=t>=R0+len(LINES)*RS+0.2
    LH=78; head=150; h=head+n*LH+(170 if tot else 0)+50
    w=860; im=Image.new('RGBA',(w,h+24),(0,0,0,0)); d=ImageDraw.Draw(im)
    paper=(244,241,232)
    d.rectangle([0,0,w,h],fill=paper+(255,))
    for i in range(0,w,24): d.polygon([(i,h),(i+12,h+20),(i+24,h)],fill=paper+(255,))
    hd=T("2군에서MVP까지",34,(110,110,120),False); im.paste(hd,((w-hd.width)//2,38),hd)
    for i in range(0,w-80,26): d.line([(40+i,112),(54+i,112)],fill=(150,150,160),width=3)
    for i in range(n):
        lab,val,col=LINES[i]; y=head+i*LH
        a=fade(t,R0+i*RS,0.18)
        l=T(lab,42,(40,40,52),False); v=T(val,46,col or (20,22,36),True)
        if a<1:
            l=l.copy(); l.putalpha(l.getchannel('A').point(lambda p:int(p*a)))
            v=v.copy(); v.putalpha(v.getchannel('A').point(lambda p:int(p*a)))
        im.paste(l,(44,y),l); im.paste(v,(w-44-v.width,y-2),v)
        x0=44+l.width+14; x1=w-44-v.width-14; yy=y+l.height-14
        for xx in range(x0,x1,16): d.ellipse([xx,yy,xx+4,yy+4],fill=(150,150,160))
    if tot:
        y=head+n*LH+10
        for i in range(0,w-80,26): d.line([(40+i,y),(54+i,y)],fill=(150,150,160),width=3)
        a=T("합계",54,(40,40,52),True); b=T("0원",96,(20,22,36),True)
        im.paste(a,(44,y+40),a); im.paste(b,(w-44-b.width,y+16),b)
    return im

# ---------- scenes
def scene1(b,t):
    a,s=pop(t,0.2); put(b,T("이 야구 게임",100,WHITE,True,5,(0,0,0)),540,520,a,s)
    xs=[(("무료"),0.7),(("광고 0개"),1.0),(("설치 X"),1.3)]
    chips=[chip(x,60,GOLD,(20,20,30)) for x,_ in xs]
    tw=sum(c.width for c in chips)+40*2; x=540-tw/2
    for (name,t0),c in zip(xs,chips):
        a,s=pop(t,t0); put(b,c,x+c.width/2,700,a,s); x+=c.width+40
    a,s=pop(t,1.9); put(b,T("근데",64,(200,205,225),False),540,930,a,s)
    a,s=pop(t,2.15,0.35); put(b,T("서버비는\n누가 냄?",120,GOLD,True,6,(0,0,0),14),540,1150,a,s)
    bob=math.sin(t*6)*10
    put(b,sprite('green',16),540,1560+bob,fade(t,0.3,0.3))
    if t>2.4:
        a,s=pop(t,2.4); put(b,T("?",90,WHITE,True,5,(0,0,0)),680,1430+bob,a,s)

def scene2(b,t):
    t=t+3.2
    a,s=pop(t,3.3); put(b,T("개발자 영수증",92,WHITE,True,5,(0,0,0)),540,250,a,s)
    r=receipt(t)
    if t>=R0: put(b,r,540,330+r.height/2,1,1)
    ts=R0+len(LINES)*RS+1.1
    if t>=ts:
        x=min(1,(t-ts)/0.18); sc=2.4-1.4*x; a=min(1,x*2)
        st=T("서버비는\n내 몫",96,RED,True,0,(0,0,0),6)
        box=Image.new('RGBA',(st.width+70,st.height+50),(0,0,0,0)); d=ImageDraw.Draw(box)
        d.rounded_rectangle([0,0,box.width-1,box.height-1],24,outline=RED+(255,),width=10)
        box.paste(st,(35,22),st)
        sh=int(8*max(0,1-(t-ts)/0.3)*math.sin(t*90))
        put(b,box,720+sh,1380,a,sc,-10)

def scene3(b,t):
    t=t+9.6
    a,s=pop(t,9.7); put(b,T("1,000원 이상 후원하면",72,WHITE,True,4,(0,0,0)),540,400,a,s)
    a,s=pop(t,10.4,0.35); put(b,T("내 이름으로",110,WHITE,True,5,(0,0,0)),540,590,a,s)
    a,s=pop(t,11.0,0.35); put(b,T("릴스 제작!",150,GOLD,True,7,(0,0,0)),540,800,a,s)
    if t>=11.8:
        y=min(1,(t-11.8)/0.4); y=1-(1-y)**3
        card=rrect(860,520,36,(244,241,232,255))
        d=ImageDraw.Draw(card)
        tag=chip("예시",34,RED,WHITE); card.paste(tag,(40,32),tag)
        tl=T("[네 이름]님의",64,(20,22,36),True); card.paste(tl,(430-tl.width//2,120),tl)
        tl2=T("24년 야구 인생 영수증 뽑아봄",44,(60,60,72),False); card.paste(tl2,(430-tl2.width//2,215),tl2)
        for i in range(0,780,26): d.line([(40+i,300),(54+i,300)],fill=(150,150,160),width=3)
        sp=sprite('red',9); card.paste(sp,(60,330),sp)
        tl3=T("○○○님\n후원 감사합니다",52,(20,22,36),True,0,(0,0,0),8); card.paste(tl3,(300,350),tl3)
        hb=heart(8,(235,150,20)); card.paste(hb,(740,380),hb)
        put(b,card,540,1330+(1-y)*500,y,1)
        for i in range(4):
            ph=(t*0.6+i*0.25)%1.0
            put(b,heart(7),230+i*210+math.sin(t*3+i)*20,1090-ph*180,(1-ph)*fade(t,12.2),1)

def scene4(b,t):
    t=t+15.4
    a,s=pop(t,15.5); put(b,T("후원은 여기서!",100,GOLD,True,6,(0,0,0)),540,230,a,s)
    if t>=15.8:
        y=min(1,(t-15.8)/0.4); y=1-(1-y)**3
        ph=rrect(640,1060,48,(8,16,40,255),(200,205,225,255),6)
        d=ImageDraw.Draw(ph)
        for i,wd in enumerate([420,300,380]):
            d.rounded_rectangle([40,50+i*54,40+wd,84+i*54],14,fill=(40,52,92,255))
        sp=sprite('green',16); ph.paste(sp,(224,300),sp)
        for i in range(3):
            d.rounded_rectangle([40,600+i*92,600,670+i*92],18,fill=(30,42,78,255))
        btn=chip("개발자 서버비 내주기",34,GOLD,(20,20,30))
        ph.paste(btn,(640-btn.width-24,1060-btn.height-26),btn)
        cx,cy=540+(640-btn.width-24+btn.width/2)-320,420+(1060-btn.height-26+btn.height/2)+(1-y)*400
        put(b,ph,540,420+530+(1-y)*400,y,1)
        if t>=16.4:
            pr=((t-16.4)*0.9)%1.0
            ring=Image.new('RGBA',(btn.width+260,btn.height+260),(0,0,0,0)); dd=ImageDraw.Draw(ring)
            e=int(20+pr*110)
            dd.rounded_rectangle([130-e,130-e,ring.width-130+e,ring.height-130+e],btn.height//2+e,outline=GOLD+(255,),width=6)
            put(b,ring,cx,cy,(1-pr)*0.9)
            bob=math.sin(t*7)*14
            tri=Image.new('RGBA',(150,150),(0,0,0,0)); dd=ImageDraw.Draw(tri)
            dd.polygon([(20,75),(90,20),(90,60),(140,60),(140,90),(90,90),(90,130)],fill=RED+(255,),outline=(255,255,255,255))
            put(b,tri,cx-btn.width/2-110+bob,cy+10,1,1)
            a,s=pop(t,16.5); put(b,T("게임 오른쪽 아래",52,WHITE,True,4,(0,0,0)),540,1590,a,s)
            put(b,T("누르면 끝",52,GOLD,True,4,(0,0,0)),540,1670,a,s)

def scene5(b,t):
    t=t+19.6
    a,s=pop(t,19.7); put(b,T("2군에서 MVP까지",96,WHITE,True,5,(0,0,0)),540,560,a,s)
    a,s=pop(t,20.1); put(b,T("고1부터 MVP까지, 내 선수 키우기",46,(215,220,240),False),540,690,a,s)
    a,s=pop(t,20.5,0.35); put(b,chip("minors2mvp.pages.dev",64,GOLD,(20,20,30)),540,860,a,s)
    a,s=pop(t,21.0); put(b,T("무료 · 설치 X · 회원가입 X",48,WHITE,False),540,1000,a,s)
    a,s=pop(t,21.5); put(b,T("1,000원 이상 후원 → 내 이름 릴스",48,GOLD,True,3,(0,0,0)),540,1100,a,s)
    for i,tm in enumerate(['green','red','navy','black','orange']):
        bob=math.sin(t*5+i)*12
        put(b,sprite(tm,10),180+i*180,1360+bob,fade(t,19.9+i*0.15,0.3))

def frame(t):
    b=BG.copy()
    if t<3.2: scene1(b,t)
    elif t<10.4: scene2(b,t-3.2)
    elif t<16.0: scene3(b,t-10.4)
    elif t<20.0: scene4(b,t-16.0)
    else: scene5(b,t-20.0)
    return b.convert('RGB')

# ---------- audio
SR=44100
def sq(f,d,v=0.2,duty=0.5):
    n=int(SR*d); tt=np.arange(n)/SR
    w=np.where((tt*f)%1<duty,1,-1).astype(float)
    env=np.minimum(1,np.arange(n)/200)*np.exp(-tt*(3.0/max(d,0.05)))
    return w*env*v
def audio():
    out=np.zeros(int(SR*DUR))
    def add(t0,x):
        i=int(t0*SR); j=min(len(out),i+len(x)); out[i:j]+=x[:j-i]
    ch=[(262,330,392,523),(220,262,330,440),(175,220,262,349),(196,247,294,392)]
    bt=0.25; k=0
    t=0.0
    while t<DUR-0.3:
        c=ch[int(t/2.0)%4]; add(t,sq(c[k%4]*(2 if k%8>=4 else 1),0.2,0.05,0.25))
        if k%4==0: add(t,sq(c[0]/2,0.45,0.07,0.5))
        t+=bt;k+=1
    for t0 in (0.2,0.7,1.0,1.3,1.9,2.15,2.4): add(t0,sq(880,0.12,0.2))
    for i in range(8): add(3.9+i*0.55,sq(1320,0.07,0.18))
    add(R0+8*0.55+0.2,sq(1568,0.2,0.2)); 
    ts=R0+len(LINES)*RS+1.1-3.2+3.2
    add(ts,sq(110,0.35,0.5,0.5)+sq(80,0.35,0.4))
    for t0,f in ((10.5,988),(11.2,1175),(11.8,1319),(12.0,1760)): add(t0,sq(f,0.18,0.2))
    for t0,f in ((16.1,784),(17.0,988),(17.15,1319)): add(t0,sq(f,0.15,0.2))
    for t0,f in ((20.1,523),(20.25,659),(20.4,784),(20.55,1047),(20.9,1319)): add(t0,sq(f,0.2,0.22))
    out/=max(1,np.abs(out).max()/0.85)
    st=np.stack([out,out],1)
    return (st*32767).astype(np.int16)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='test':
        ts=[1.0,2.8,5.2,8.2,9.3,11.0,13.5,17.5,21.5]
        ims=[frame(t).resize((360,640)) for t in ts]
        m=Image.new('RGB',(360*5,640*2))
        for i,im in enumerate(ims): m.paste(im,((i%5)*360,(i//5)*640))
        m.save('/home/claude/sp/test.png')
    else:
        with wave.open('/home/claude/sp/a.wav','wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(audio().tobytes())
        out=sys.argv[2]
        p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
            '-i','/home/claude/sp/a.wav','-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
            '-movflags','+faststart','-shortest',out],stdin=subprocess.PIPE)
        for i in range(int(DUR*FPS)):
            p.stdin.write(frame(i/FPS).tobytes())
        p.stdin.close(); p.wait()
