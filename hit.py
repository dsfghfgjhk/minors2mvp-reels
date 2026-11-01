import sys; sys.path.insert(0,'/home/claude/sp')
from make import *
import numpy as np, math, wave, subprocess
from PIL import Image, ImageDraw, ImageChops
FPS=30
SEG=[(1,"프로 투수 직구급","정상적인 안타",'field',1.6),
(2,"KTX보다 빠름","외야수 못 잡음",'field',1.5),
(3,"비행기급 속도","담장 넘어 주차장 직행",'field',1.5),
(4,"거의 음속","쾅! 소리가 공보다 늦게 도착",'field',1.6),
(5,"음속의 2배 (마하 2)","소닉붐으로 유리창 전부 깨짐",'field',1.6),
(6,"마하 4 · 전투기보다 빠름","공이 지나간 자리에 불이 붙음",'field',1.6),
(7,"마하 8 · 극초음속","하늘로 솟구침",'sky',1.2),
(8,"마하 16","구름 뚫고 대기권 돌파",'sky',1.2),
(9,"지구 탈출 속도 직전","이제 못 돌아옴",'sky',1.2),
(10,"지구 탈출 성공","야구공이 우주로 나감",'earth',1.6),
(11,"달까지 2시간 30분","달 옆을 스쳐감",'moon',1.0),
(14,"지구 한 바퀴 2분","지구 둘레 4만km를 2분에 돎",'earth',1.0),
(20,"태양까지 2시간","태양 직행 중",'sun',1.0),
(23,"빛 속도의 58%","시간이 느려지기 시작함",'none',1.0),
(24,"빛보다 빠름","공이 안 보임… 관중: 어디 갔어?",'vanish',1.8)]
INTRO=2.4; PROMO=3.2
T0=[];t=INTRO
for s in SEG: T0.append(t); t+=s[4]
PT=t; DUR=PT+PROMO
def speed(n):
    v=150*2**(n-1)
    if v>=1e8: return f"{v/1e8:.1f}억km/h"
    if v>=1e6: return f"{v/1e4:,.0f}만km/h"
    if v>=1e4: return f"{v/1e4:.1f}만km/h"
    return f"{v:,}km/h"

# ---------- 배경(픽셀 구장)
def make_field():
    lw,lh=270,480; a=np.zeros((lh,lw,3),np.uint8); rng=np.random.default_rng(7)
    for y in range(lh):
        if y<170: c=np.array([6,10,32])+np.array([8,10,20])*y/170
        elif y<272:
            c=np.array([40,40,92])
        elif y<284: c=np.array([22,92,60])
        else: c=np.array([28,110,52])+(0 if (y//10)%2 else np.array([-8,-10,-6]))
        a[y,:]=c
    # 관중석 노이즈
    for y in range(170,272,2):
        for x in range(0,lw,2):
            v=rng.integers(-35,45); col=np.array([60,55,110])+v+ (np.array([60,20,0]) if rng.random()<0.08 else 0)
            a[y:y+2,x:x+2]=np.clip(col,0,255)
    # 광고판
    for x in range(0,lw,18): a[272:284,x:x+16]=[(220,60,60),(60,120,220),(240,200,60),(80,200,140)][(x//18)%4]
    # 흙길
    a[372:392,:]=[150,105,60]; a[372:374,:]=[170,125,75]
    # 조명 점
    for x in (40,130,220):
        a[150:154,x:x+6]=[255,250,200]
    img=Image.fromarray(a).resize((1080,1920),Image.NEAREST).convert('RGBA')
    return img
FIELD=make_field()
def dim(img,f):
    d=Image.new('RGBA',img.size,(0,0,0,int(255*f))); o=img.copy(); o.alpha_composite(d); return o
SKY=None
def make_sky():
    y=np.linspace(0,1,H)[:,None]; top=np.array([3,6,24]); bot=np.array([40,90,170])
    g=top*(1-y[...,None])+bot*y[...,None]; g=g*np.ones((H,W,3))
    return Image.fromarray(g.astype(np.uint8)).convert('RGBA')
SKY=make_sky()
@lru_cache(None)
def ballimg(r):
    s=r*2+6; im=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([3,3,s-4,s-4],fill=(250,250,250,255),outline=(60,60,70,255),width=max(1,r//10))
    w=max(2,r//6)
    d.arc([3-r//2,3,3+r+r//2,s-4],-60,60,fill=(220,50,50,255),width=w)
    d.arc([s-4-r-r//2,3,s-4+r//2,s-4],120,240,fill=(220,50,50,255),width=w)
    return im
def star(size,col):
    im=Image.new('RGBA',(size,size),(0,0,0,0)); d=ImageDraw.Draw(im); c=size/2; pts=[]
    for i in range(16):
        r=c if i%2==0 else c*0.5; ang=i*math.pi/8; pts.append((c+r*math.cos(ang),c+r*math.sin(ang)))
    d.polygon(pts,fill=col+(255,),outline=(255,255,255,255)); return im
def batimg(ang):
    h=250;cv=Image.new('RGBA',(h*2,h*2),(0,0,0,0)); d=ImageDraw.Draw(cv)
    d.rounded_rectangle([h-14,h-h,h+14,h],10,fill=(190,140,70,255),outline=(90,60,30,255),width=3)
    d.rectangle([h-9,h-30,h+9,h],fill=(120,80,40,255))
    return cv.rotate(ang,resample=Image.BICUBIC)
def lerp(a,b,x): return a+(b-a)*max(0,min(1,x))

def shake(b,t,amp):
    if t<0 or t>0.4 or amp<=0: return b
    k=amp*(1-t/0.4); dx=int(k*math.sin(t*90)); dy=int(k*math.cos(t*77))
    return ImageChops.offset(b,dx,dy)

def hud(b,n,lt,label,cap):
    a,s=pop(lt,0.0,0.25); put(b,T(f"{n}번째 타격",42,(215,220,240),True,3,(0,0,0)),540,170,a)
    put(b,T(speed(n),132,WHITE,True,7,(0,0,0)),540,300,a,s)
    put(b,T(label,52,GOLD,True,4,(0,0,0)),540,430,a)
    put(b,chip("힘 x2",36,RED,WHITE),540,505,a)
    ca=fade(lt,0.7,0.25); put(b,T(cap,60,WHITE,True,6,(0,0,0)),540,1650,ca)

def ball_field(b,n,lt):
    hit=0.55; thx,thy=360,1390
    if lt<hit:
        x=lerp(820,thx,lt/hit); y=lerp(1330,thy,lt/hit); put(b,ballimg(18),x,y)
    else:
        v=620*1.45**n; dt=lt-hit; th=math.radians(26+n*3)
        x=thx+math.cos(th)*v*dt; y=thy-math.sin(th)*v*dt
        L=min(60+n*70,520)
        for k in range(8):
            f=k/8; px=x-math.cos(th)*L*f; py=y+math.sin(th)*L*f
            col=(255,170,40) if n>=6 else (255,255,255)
            rr=max(3,int(16*(1-f))); 
            g=Image.new('RGBA',(rr*2,rr*2),col+(int(200*(1-f)),)); 
            gd=ImageDraw.Draw(g); 
            sm=Image.new('RGBA',(rr*2,rr*2),(0,0,0,0)); ImageDraw.Draw(sm).ellipse([0,0,rr*2-1,rr*2-1],fill=col+(int(190*(1-f)),)); b.paste(sm,(int(px-rr),int(py-rr)),sm)
        put(b,ballimg(18),x,y)
        if n>=4:
            ph=min(1,dt/0.5); ring=Image.new('RGBA',(700,700),(0,0,0,0)); ImageDraw.Draw(ring).ellipse([350-ph*330,350-ph*330,350+ph*330,350+ph*330],outline=(255,255,255,int(220*(1-ph))),width=8)
            put(b,ring,thx,thy)
        if n>=5:
            for i in range(10):
                ang=-0.6+i*0.35; d=dt*(300+i*40)
                if dt<0.9: put(b,rrect(14,14,3,(200,230,255,255)),700+i*30+math.cos(ang)*d*0.3,820+(i%3)*60+d*0.6*(1+i%2),1-dt/0.9)
    if hit<=lt<hit+0.3:
        x=(lt-hit)/0.3; put(b,star(int(150+n*14),(255,210,60)),thx,thy,1-x,0.6+x*0.7)
        put(b,T("쾅!",70,WHITE,True,6,(200,40,40)),thx+30,thy-130,1-x)

def batter(b,lt,pose='swing'):
    put(b,sprite('green',16),300,1340)
    if pose=='swing':
        if lt<0.30: ang=70
        elif lt<0.55: ang=lerp(70,-20,(lt-0.30)/0.25)
        else: ang=lerp(-20,-80,(lt-0.55)/0.25)
        bi=batimg(ang); put(b,bi,350,1330)

def scene_field(b,n,lt):
    batter(b,lt); ball_field(b,n,lt)
def scene_sky(b,n,lt):
    hit=0.2
    put(b,sprite('green',8),210,1700)
    if lt<hit: put(b,ballimg(18),300,1560)
    else:
        dt=lt-hit; v=900*1.2**n; x=300+dt*v*0.35; y=1560-dt*v
        for k in range(10):
            f=k/10; put(b,rrect(24,24,12,(255,160+int(60*f),40,255)),x-f*0.35*400,y+f*400,0.9*(1-f),1-0.4*f)
        put(b,ballimg(18),x,y)
    # 구름 / 별
    for i in range(6):
        cy=(500+i*260+lt*900)%2100-100; put(b,rrect(220,40,20,(235,240,250,120)),150+i*170,cy,1)
    if lt<0.45: put(b,star(200,(255,210,60)),300,1560,1-lt/0.45)
def space_bg(b):
    b.paste(Image.new('RGBA',(W,H),(2,4,16,255)),(0,0))
    rng=np.random.default_rng(5)
    for _ in range(90):
        x,y=int(rng.integers(0,W)),int(rng.integers(0,H)); b.paste(Image.new('RGBA',(4,4),(200,210,255,255)),(x,y))
def planet(b,kind,cx,cy,sc=1):
    if kind=='earth':
        r=int(150*sc); im=Image.new('RGBA',(r*2+60,r*2+60),(0,0,0,0)); d=ImageDraw.Draw(im); c=r+30
        d.ellipse([c-r-14,c-r-14,c+r+14,c+r+14],fill=(60,120,255,60)); d.ellipse([c-r,c-r,c+r,c+r],fill=(40,100,220,255))
        for bx,by,bw in ((-50,-60,90),(30,10,100),(-70,50,60)): d.ellipse([c+bx*sc-bw*sc/2,c+by*sc-bw*sc/3,c+bx*sc+bw*sc/2,c+by*sc+bw*sc/3],fill=(60,170,80,255))
        put(b,im,cx,cy)
    elif kind=='moon':
        r=int(100*sc); im=Image.new('RGBA',(r*2+10,r*2+10),(0,0,0,0)); d=ImageDraw.Draw(im); d.ellipse([5,5,r*2+5,r*2+5],fill=(200,200,205,255))
        for bx,by,bw in ((-30,-30,30),(25,20,40),(-10,40,20)): d.ellipse([r+5+bx-bw/2,r+5+by-bw/2,r+5+bx+bw/2,r+5+by+bw/2],fill=(160,160,170,255))
        put(b,im,cx,cy)
    elif kind=='sun':
        r=int(170*sc); im=Image.new('RGBA',(r*2+120,r*2+120),(0,0,0,0)); d=ImageDraw.Draw(im); c=r+60
        for k,al in ((60,40),(35,70),(15,110)): d.ellipse([c-r-k,c-r-k,c+r+k,c+r+k],fill=(255,170,40,al))
        d.ellipse([c-r,c-r,c+r,c+r],fill=(255,210,60,255)); put(b,im,cx,cy)
def scene_space(b,n,lt,kind):
    space_bg(b)
    if kind in ('earth','moon','sun'): planet(b,kind,820 if kind!='sun' else 880,1120,1)
    if lt<0.2: put(b,star(220,(255,210,60)),160,1100,1-lt/0.2,0.7+lt*2)
    x=lerp(120,1250,lt/0.9); y=1100-math.sin(min(1,lt/0.9)*math.pi)*30
    if lt<0.9:
        for k in range(8):
            f=k/8; put(b,rrect(40,16,8,(255,255,255,255)),x-f*260,y,0.8*(1-f))
        put(b,ballimg(16),x,y)
def scene_vanish(b,n,lt):
    FIELDDIM=dim(FIELD,0.35); b.paste(FIELDDIM,(0,0))
    put(b,sprite('green',16),300,1340)
    if lt<0.35: 
        put(b,Image.new('RGBA',(W,H),(255,255,255,int(230*(1-lt/0.35)))),540,960)
    if lt>0.6: 
        a,s=pop(lt,0.6); put(b,T("?",150,WHITE,True,8,(0,0,0)),360,1110,a,s)
        put(b,T("??",120,GOLD,True,6,(0,0,0)),760,1250,a,s)
    put(b,sprite('red',8),840,1420,fade(lt,0.6,0.2)); put(b,sprite('navy',8),960,1440,fade(lt,0.7,0.2))

def intro(b,t):
    b.paste(dim(FIELD,0.45),(0,0)); put(b,sprite('green',16),300,1340)
    put(b,batimg(70),350,1330)
    a,s=pop(t,0.1,0.35); put(b,T("타자가 공을 칠 때마다",76,WHITE,True,6,(0,0,0)),540,560,a,s)
    pa,ps=pop(t,0.5,0.35)
    p1=T("힘이 ",110,WHITE,True,7,(0,0,0)); p2=T("2배",140,RED,True,7,(0,0,0)); p3=T("가 된다면?",110,WHITE,True,7,(0,0,0))
    tw=p1.width+p2.width+p3.width-30; x=540-tw/2
    for p in (p1,p2,p3):
        put(b,p,x+p.width/2,760,pa,ps); x+=p.width-10
    a,s=pop(t,1.5); put(b,T("지금 타구 속도 150km/h",58,GOLD,True,5,(0,0,0)),540,990,a,s)
def promo(b,t):
    b.paste(dim(FIELD,0.65),(0,0))
    a,s=pop(t,0.1); put(b,T("우리 게임 타구는",84,WHITE,True,6,(0,0,0)),540,620,a,s)
    a,s=pop(t,0.5,0.35); put(b,T("정상 속도임 ㅋㅋ",120,GOLD,True,7,(0,0,0)),540,790,a,s)
    a,s=pop(t,0.9); put(b,T("고1부터 은퇴까지 야구선수 키우기",46,(215,220,240),False),540,930,a,s)
    a,s=pop(t,1.3,0.35); put(b,chip("minors2mvp.pages.dev",64,GOLD,(20,20,30)),540,1080,a,s)
    a,s=pop(t,1.8); put(b,T("2군에서 MVP까지 · 무료 · 설치 X · 회원가입 X",42,WHITE,False),540,1200,a,s)
    for i,tm in enumerate(['green','red','navy','black','orange']):
        put(b,sprite(tm,10),180+i*180,1420+math.sin(t*5+i)*12,fade(t,0.5+i*0.12,0.3))

def frame(t):
    b=Image.new('RGBA',(W,H),(0,0,0,255))
    if t<INTRO: intro(b,t); return b.convert('RGB')
    if t>=PT: promo(b,t-PT); return b.convert('RGB')
    i=max(k for k in range(len(SEG)) if T0[k]<=t); n,label,cap,kind,dur=SEG[i]; lt=t-T0[i]
    if kind=='field':
        b.paste(FIELD,(0,0)); scene_field(b,n,lt); b=shake(b,lt-0.55,6+n*6)
    elif kind=='sky': b.paste(SKY,(0,0)); scene_sky(b,n,lt)
    elif kind=='vanish': scene_vanish(b,n,lt)
    else: scene_space(b,n,lt,kind)
    hud(b,n,lt,label,cap)
    return b.convert('RGB')

def audio():
    out=np.zeros(int(SR*DUR))
    def add(t0,x):
        i=int(t0*SR); j=min(len(out),i+len(x)); 
        if i<len(out): out[i:j]+=x[:j-i]
    ch=[(262,330,392,523),(220,262,330,440),(175,220,262,349),(196,247,294,392)]
    t=0.0;k=0
    while t<DUR-0.3:
        c=ch[int(t/2.0)%4]; add(t,sq(c[k%4]*(2 if k%8>=4 else 1),0.2,0.05,0.25))
        if k%4==0: add(t,sq(c[0]/2,0.45,0.06,0.5))
        t+=0.25;k+=1
    rng=np.random.default_rng(2)
    for j,(s,t0) in enumerate(zip(SEG,T0)):
        ht=t0+(0.55 if s[3]=='field' else 0.2)
        n=int(SR*0.12); nz=rng.standard_normal(n)*np.exp(-np.arange(n)/(SR*0.03))*0.5
        add(ht,nz); add(ht,sq(220+s[0]*30,0.15,0.3))
    add(T0[-1],sq(1568,0.3,0.25)); add(PT+0.1,sq(523,0.2,0.22)); add(PT+0.3,sq(784,0.2,0.22)); add(PT+0.5,sq(1047,0.3,0.22))
    out/=max(1,np.abs(out).max()/0.85)
    return (np.stack([out,out],1)*32767).astype(np.int16)

if __name__=='__main__':
    if sys.argv[1]=='test':
        ts=[0.5,2.0,T0[0]+0.45,T0[0]+0.9,T0[3]+0.8,T0[4]+0.8,T0[5]+0.9,T0[6]+0.7,T0[9]+0.6,T0[10]+0.5,T0[12]+0.5,T0[14]+1.0,PT+1.8,T0[2]+0.9]
        ims=[frame(t).resize((300,533)) for t in ts]
        m=Image.new('RGB',(300*7,533*2))
        for i,im in enumerate(ims): m.paste(im,((i%7)*300,(i//7)*533))
        m.save('/home/claude/sp/hit_test.png'); print(DUR)
    else:
        with wave.open('/home/claude/sp/h.wav','wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(audio().tobytes())
        p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-i','/home/claude/sp/h.wav',
            '-c:v','libx264','-crf','16','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',sys.argv[2]],stdin=subprocess.PIPE)
        for i in range(int(DUR*FPS)): p.stdin.write(frame(i/FPS).tobytes())
        p.stdin.close(); p.wait()
