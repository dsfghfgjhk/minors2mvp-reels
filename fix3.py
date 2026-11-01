import numpy as np, cv2, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
SRC='/mnt/user-data/uploads/릴스_1초에1살_연봉1등.mp4'
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
NAME='김현서'
def kri():
    for i in range(8):
        try:
            if 'KR' in ''.join(ImageFont.truetype(FONT,20,index=i).getname()): return i
        except Exception: pass
    return 0
KRI=kri()
from functools import lru_cache
@lru_cache(None)
def name_alpha(h):
    size=100; f=ImageFont.truetype(FONT,size,index=KRI)
    gl=[]
    for ch in NAME:
        im=Image.new('L',(size*3,size*3),0); ImageDraw.Draw(im).text((size,size//2),ch,font=f,fill=255)
        g=im.crop(im.getbbox()); gl.append(g)
    gw=int(h*0.86); gap=max(1,int(h*0.08))
    Wt=gw*3+gap*2
    out=np.zeros((h,Wt),np.float32)
    for k,g in enumerate(gl):
        a=np.array(g.resize((gw,h),Image.LANCZOS)).astype(np.float32)/255
        out[:,k*(gw+gap):k*(gw+gap)+gw]=np.clip(a*1.08,0,1)
    return out
@lru_cache(None)
def text_alpha(txt,h):
    size=100; f=ImageFont.truetype(FONT,size,index=KRI)
    im=Image.new('L',(size*len(txt)*2,size*3),0); ImageDraw.Draw(im).text((size//2,size//2),txt,font=f,fill=255)
    g=im.crop(im.getbbox()); sc=h/g.height
    g=g.resize((max(1,int(g.width*sc)),h),Image.LANCZOS)
    return np.array(g).astype(np.float32)/255

EXCL=False
CACHE={}
def words_in(a,band,xr,gapk=0.30):
    y0,y1=band;x0,x1=xr
    sub=a[y0:y1,x0:x1].astype(np.float32)
    L=sub.mean(axis=2); sat=sub.max(axis=2)-sub.min(axis=2)
    mx=np.percentile(L,99.8)
    if mx<90: return None
    m=(L>0.55*mx)&(sat<80)
    spr=((sat>=70)&(L>50)).astype(np.uint8)
    if EXCL and spr.sum()>20:
        spr=cv2.dilate(cv2.morphologyEx(spr,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8)),np.ones((11,11),np.uint8))
        m=m&(spr==0)
        words_in.spr=spr
    else: words_in.spr=None
    if m.sum()<200: return None
    ys=np.where(m.any(axis=1))[0]; hh=ys.max()-ys.min()+1
    cols=m.any(axis=0); runs=[];s=None
    for x in range(len(cols)):
        if cols[x] and s is None: s=x
        if (not cols[x]) and s is not None: runs.append([s,x-1]); s=None
    if s is not None: runs.append([s,len(cols)-1])
    ws=[]
    for r in runs:
        if ws and r[0]-ws[-1][1]-1<=gapk*hh: ws[-1][1]=r[1]
        else: ws.append(r[:])
    out=[]
    for r in ws:
        mm=m[:,r[0]:r[1]+1]; yy=np.where(mm.any(axis=1))[0]
        out.append((r[0]+x0,r[1]+x0,yy.min()+y0,yy.max()+y0))
    col=sub[(L>0.8*mx)&(sat<80)].mean(axis=0)
    return out,m,(x0,y0),col,hh

def rebuild(a,band,xr,op,expect):
    res=words_in(a,band,xr)
    if res is None: return a
    ws,m,(x0,y0),col,hh=res
    key=(band,op)
    if len(ws)==expect: CACHE[key]=ws
    elif key in CACHE and band==(570,670):
        ws=CACHE[key]
        bm=np.zeros(m.shape,bool)
        for w in ws: bm[max(0,w[2]-y0-2):w[3]-y0+3, max(0,w[0]-x0-2):w[1]-x0+3]=True
        m=m&bm
    else: return a
    # 마스크 지우기
    o=a.copy()
    md=cv2.dilate(m.astype(np.uint8),np.ones((7,7),np.uint8))
    sub=np.ascontiguousarray(o[y0:band[1],x0:xr[1]])
    inp=cv2.inpaint(sub,md*255,4,cv2.INPAINT_TELEA).astype(np.float32)
    canvas=inp.copy()
    top=min(w[2] for w in ws); bot=max(w[3] for w in ws); lh=bot-top+1
    gaps=[ws[i+1][0]-ws[i][1]-1 for i in range(len(ws)-1)]
    sp=int(np.median(gaps)) if gaps else int(lh*0.35)
    left=ws[0][0]; right=ws[-1][1]; cx=(left+right)/2
    items=[]  # (kind, data, width)
    for i,w in enumerate(ws):
        items.append(('orig',i,w[1]-w[0]+1))
    if op=='replace_last':
        ti=len(ws)-1; th=ws[ti][3]-ws[ti][2]+1
        na=name_alpha(th); items[ti]=('name',na,na.shape[1]); ty=ws[ti][2]
    elif op.startswith('replace'):
        ti=int(op.split(':')[1]); th=ws[ti][3]-ws[ti][2]+1
        na=name_alpha(th); items[ti]=('name',na,na.shape[1]); ty=ws[ti][2]
    elif op=='prepend':
        na=name_alpha(lh); items.insert(0,('name',na,na.shape[1])); ty=top
    total=sum(i[2] for i in items)+sp*(len(items)-1)
    x=int(round(cx-total/2))
    for kind,d,wd in items:
        if kind=='orig':
            w=ws[d]; patch=a[y0:band[1],w[0]-1:w[1]+2].astype(np.float32)
            ml=m[:,w[0]-x0-1:w[1]-x0+2] if w[0]-1>=x0 else m[:,0:w[1]-x0+2]
            # 알파 = 원래 글자 마스크를 부드럽게
            al=cv2.GaussianBlur(cv2.dilate(ml.astype(np.uint8),np.ones((3,3),np.uint8)).astype(np.float32),(3,3),0)
            xs=x-1; xe=xs+patch.shape[1]
            if xs-x0<0 or xe-x0>canvas.shape[1]: x+=wd+sp; continue
            reg=canvas[:,xs-x0:xe-x0]
            reg[:]=reg*(1-al[...,None])+patch*al[...,None]
        else:
            na=d; hh_,ww_=na.shape
            yy=ty-y0; xs=x-x0
            if xs<0 or xs+ww_>canvas.shape[1]: x+=wd+sp; continue
            reg=canvas[yy:yy+hh_,xs:xs+ww_]
            reg[:]=reg*(1-na[...,None])+col[None,None,:]*na[...,None]
        x+=wd+sp
    res_img=np.clip(canvas,0,255).astype(np.uint8)
    spr=getattr(words_in,'spr',None)
    if spr is not None:
        sm=spr>0
        res_img[sm]=a[y0:band[1],x0:xr[1]][sm]
    o[y0:band[1],x0:xr[1]]=res_img
    return o

def process(a,i):
    global EXCL
    EXCL=(i<57)
    if i<57: return rebuild(a,(570,670),(150,930),'replace_last',3)
    if i<=493: return rebuild(a,(165,235),(300,780),'replace:2',6)
    return rebuild(a,(270,390),(250,830),'prepend',2)

if __name__=='__main__':
    if sys.argv[1]=='test':
        want=[int(x) for x in sys.argv[2].split(',')]
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',SRC,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        i=0; outs=[]
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            if i in want:
                a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
                o=process(a,i); changed=(o!=a).any()
                print(i,'changed',changed,flush=True)
                if i<57: crop=o[520:740]
                elif i<=493: crop=o[150:330]
                else: crop=o[250:430]
                outs.append(Image.fromarray(crop[:, :]).resize((540,int(crop.shape[0]*0.5))))
            i+=1
            if i>max(want): break
        dec.kill()
        hh=max(im.height for im in outs)
        m=Image.new('RGB',(540*2,hh*((len(outs)+1)//2)))
        for k,im in enumerate(outs): m.paste(im,((k%2)*540,(k//2)*hh))
        m.save('/home/claude/test3.png')
    else:
        dst=sys.argv[2]
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',SRC,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        enc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-i',SRC,
            '-map','0:v','-map','1:a','-c:v','libx264','-crf','15','-preset','medium','-pix_fmt','yuv420p','-c:a','copy','-shortest',dst],stdin=subprocess.PIPE)
        i=0
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
            enc.stdin.write(process(a,i).tobytes()); i+=1
        enc.stdin.close(); enc.wait()
