import numpy as np, cv2, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
SRC='/mnt/user-data/uploads/릴스_선수주식.mp4'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
def kri():
    for i in range(8):
        try:
            if 'KR' in ''.join(ImageFont.truetype(FONT,20,index=i).getname()): return i
        except Exception: pass
    return 0
KRI=kri()
# 기준 프레임(240)에서 템플릿/글자 위치 추출
def get_frame(n):
    p=subprocess.run(['ffmpeg','-v','error','-i',SRC,'-vf',f'select=eq(n\\,{n})','-vframes','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
    return np.frombuffer(p.stdout,np.uint8).reshape(H,W,3)
ref=get_frame(240)
RX0,RX1,RY0,RY1=245,427,203,272
Lr=ref.astype(float).mean(axis=2)
reg=Lr[RY0:RY1,RX0:RX1]
tm=(reg>0.5*reg.max())
ys,xs=np.where(tm)
BX0,BX1,BY0,BY1=xs.min()+RX0,xs.max()+RX0,ys.min()+RY0,ys.max()+RY0
TPL=cv2.cvtColor(ref[RY0:RY1,RX0:RX1],cv2.COLOR_RGB2GRAY).astype(np.float32)
# 글리프 슬롯(3칸 균등)
GW=(BX1-BX0+1); GH=(BY1-BY0+1); GAP=7; SLOT=(GW-2*GAP)//3
def glyph(ch):
    size=80; f=ImageFont.truetype(FONT,size,index=KRI)
    im=Image.new('L',(size*3,size*3),0); ImageDraw.Draw(im).text((size,size//2),ch,font=f,fill=255)
    g=im.crop(im.getbbox()).resize((SLOT,GH),Image.LANCZOS)
    a=np.array(g).astype(np.float32)/255
    return np.clip(a*1.1,0,1)
NEW=np.zeros((GH,GW),np.float32)
for k,c in enumerate('유동주'):
    x=k*(SLOT+GAP); NEW[:,x:x+SLOT]=glyph(c)
NEW=np.pad(NEW,((0,0),(0,GW-NEW.shape[1])))[:,:GW] if NEW.shape[1]<GW else NEW

def process(a):
    g=cv2.cvtColor(a[RY0-16:RY1+16,RX0-16:RX1+16],cv2.COLOR_RGB2GRAY).astype(np.float32)
    if g.std()<3: return a
    res=cv2.matchTemplate(g,TPL,cv2.TM_CCOEFF_NORMED)
    _,mx,_,loc=cv2.minMaxLoc(res)
    if mx<0.55: return a
    dx=loc[0]-16; dy=loc[1]-16
    x0,x1,y0,y1=BX0+dx,BX1+dx,BY0+dy,BY1+dy
    pad=6
    ry0,ry1,rx0,rx1=y0-pad,y1+pad+1,x0-pad,x1+pad+1
    sub=a[ry0:ry1,rx0:rx1].copy()
    L=sub.astype(np.float32).mean(axis=2)
    sat=sub.max(axis=2).astype(int)-sub.min(axis=2).astype(int)
    mx_=np.percentile(L,99.5)
    m=((L>0.35*mx_)&(sat<60)).astype(np.uint8)
    if m.sum()<100: return a
    col=sub[(L>0.8*mx_)&(sat<60)].mean(axis=0) if ((L>0.8*mx_)&(sat<60)).sum()>20 else np.array([255,255,255.])
    md=cv2.dilate(m,np.ones((5,5),np.uint8))
    inp=cv2.inpaint(np.ascontiguousarray(sub),md*255,3,cv2.INPAINT_TELEA).astype(np.float32)
    al=np.zeros(L.shape,np.float32)
    al[pad:pad+GH,pad:pad+GW]=NEW
    out=inp*(1-al[...,None])+col[None,None,:]*al[...,None]
    o=a.copy(); o[ry0:ry1,rx0:rx1]=np.clip(out,0,255).astype(np.uint8)
    return o

if __name__=='__main__':
    print('bbox',BX0,BX1,BY0,BY1,'slot',SLOT,flush=True)
    if sys.argv[1]=='test':
        want=[0,20,60,150,234,335,484,520]
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',SRC,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        i=0; outs=[]
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            if i in want:
                a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
                outs.append(Image.fromarray(process(a)[170:330,0:700]))
            i+=1
            if i>max(want): break
        dec.kill()
        m=Image.new('RGB',(700*2,160*4))
        for k,im in enumerate(outs): m.paste(im,((k%2)*700,(k//2)*160))
        m.save('/home/claude/test2.png')
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
