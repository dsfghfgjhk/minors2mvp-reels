import numpy as np, cv2, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
SRC='/mnt/user-data/uploads/릴스_저점매수.mp4'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
NEWTXT='해녀 이정숙'
def kri():
    for i in range(8):
        try:
            if 'KR' in ''.join(ImageFont.truetype(FONT,20,index=i).getname()): return i
        except Exception: pass
    return 0
KRI=kri()
def get_frame(n):
    p=subprocess.run(['ffmpeg','-v','error','-i',SRC,'-vf',f'select=eq(n\\,{n})','-vframes','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
    return np.frombuffer(p.stdout,np.uint8).reshape(H,W,3)
ref=get_frame(180)
RX0,RX1,RY0,RY1=170,320,190,285
Lr=ref.astype(float).mean(axis=2); reg=Lr[RY0:RY1,RX0:RX1]
tm=reg>0.5*reg.max(); ys,xs=np.where(tm)
BX0,BX1,BY0,BY1=xs.min()+RX0,xs.max()+RX0,ys.min()+RY0,ys.max()+RY0
GH=BY1-BY0+1
TX0,TX1,TY0,TY1=BX0-8,BX1+8,BY0-8,BY1+8
TPL=cv2.cvtColor(ref[TY0:TY1,TX0:TX1],cv2.COLOR_RGB2GRAY).astype(np.float32)
def build_new():
    size=100; f=ImageFont.truetype(FONT,size,index=KRI)
    gw=int(GH*0.86); gap=max(1,int(GH*0.08)); sp=int(GH*0.32)
    glyphs=[]
    for ch in NEWTXT:
        if ch==' ': glyphs.append(None); continue
        im=Image.new('L',(size*3,size*3),0); ImageDraw.Draw(im).text((size,size//2),ch,font=f,fill=255)
        glyphs.append(im.crop(im.getbbox()).resize((gw,GH),Image.LANCZOS))
    Wt=sum((gw+gap) if g is not None else sp for g in glyphs)
    out=np.zeros((GH,Wt),np.float32); x=0
    for g in glyphs:
        if g is None: x+=sp; continue
        out[:,x:x+gw]=np.clip(np.array(g).astype(np.float32)/255*1.08,0,1); x+=gw+gap
    return out
NEW=build_new(); NW=NEW.shape[1]
def process(a):
    g=cv2.cvtColor(a[TY0-20:TY1+20,TX0-20:TX1+20],cv2.COLOR_RGB2GRAY).astype(np.float32)
    if g.std()<2: return a
    res=cv2.matchTemplate(g,TPL,cv2.TM_CCOEFF_NORMED)
    _,mx,_,loc=cv2.minMaxLoc(res)
    if mx<0.6: return a
    dx=loc[0]-20; dy=loc[1]-20
    x0,y0=BX0+dx,BY0+dy
    pad=6
    ry0,ry1,rx0,rx1=y0-pad,y0+GH+pad,x0-pad,x0+max(NW,BX1-BX0+1)+pad
    sub=a[ry0:ry1,rx0:rx1].copy()
    L=sub.astype(np.float32).mean(axis=2); sat=sub.max(axis=2).astype(int)-sub.min(axis=2).astype(int)
    ow=BX1-BX0+1
    mm=np.zeros(L.shape,bool); mm[:, :pad+ow+pad]=True  # 원래 글자 폭 범위만 지움
    mx_=np.percentile(L[mm],99.5)
    m=((L>0.35*mx_)&(sat<60)&mm).astype(np.uint8)
    if m.sum()<60: return a
    sel=(L>0.8*mx_)&(sat<60)&mm
    col=sub[sel].mean(axis=0) if sel.sum()>20 else np.array([255,255,255.])
    md=cv2.dilate(m,np.ones((5,5),np.uint8))
    inp=cv2.inpaint(np.ascontiguousarray(sub),md*255,3,cv2.INPAINT_TELEA).astype(np.float32)
    al=np.zeros(L.shape,np.float32); al[pad:pad+GH,pad:pad+NW]=NEW
    out=inp*(1-al[...,None])+col[None,None,:]*al[...,None]
    o=a.copy(); o[ry0:ry1,rx0:rx1]=np.clip(out,0,255).astype(np.uint8)
    return o
if __name__=='__main__':
    print('bbox',BX0,BX1,BY0,BY1,'GH',GH,'NW',NW,flush=True)
    if sys.argv[1]=='test':
        want=[int(x) for x in sys.argv[2].split(',')]
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',SRC,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        i=0; outs=[]
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            if i in want:
                a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy(); o=process(a)
                print(i,'changed',(o!=a).any(),flush=True)
                outs.append(Image.fromarray(o[150:330,60:760]))
            i+=1
            if i>max(want): break
        dec.kill()
        m=Image.new('RGB',(700*2,180*((len(outs)+1)//2)))
        for k,im in enumerate(outs): m.paste(im,((k%2)*700,(k//2)*180))
        m.save('/home/claude/test4.png')
    else:
        dst=sys.argv[2]
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',SRC,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        enc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-i',SRC,
            '-map','0:v','-map','1:a','-c:v','libx264','-crf','15','-preset','medium','-pix_fmt','yuv420p','-c:a','copy','-shortest',dst],stdin=subprocess.PIPE)
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
            enc.stdin.write(process(a).tobytes())
        enc.stdin.close(); enc.wait()
