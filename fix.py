import numpy as np, cv2, sys
from PIL import Image, ImageDraw, ImageFont

Y0=1380
S1=(28,100); S2=(104,176)       # strip rows (relative to Y0)
XL,XR=100,985
LIMIT=965
LINE_DY=76
TXT=np.array([25,24,29],float)
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

def kr_index():
    for i in range(8):
        try:
            f=ImageFont.truetype(FONT,44,index=i)
            if 'KR' in ''.join(f.getname()): return i
        except Exception: pass
    return 0
KRI=kr_index()

def glyph_alpha(ch,w=36,h=41):
    size=60
    f=ImageFont.truetype(FONT,size,index=KRI)
    im=Image.new('L',(size*3,size*3),0)
    ImageDraw.Draw(im).text((size,size//2),ch,font=f,fill=255)
    bb=im.getbbox(); g=im.crop(bb).resize((w,h),Image.LANCZOS)
    a=np.array(g).astype(np.float32)/255
    a=cv2.dilate(a,np.ones((2,2),np.uint8))   # 살짝 굵게(원본이 더 두꺼움)
    return np.clip(a*1.15,0,1)
GL={c:glyph_alpha(c) for c in '김민준'}

def name_block(n):                # n=1 -> 김, n=3 -> 김민준
    chs='김민준'[:n]
    W=36*n+7*(n-1); blk=np.zeros((41,W),np.float32)
    for k,c in enumerate(chs):
        x=k*43; blk[:,x:x+36]=GL[c]
    return blk

# --- 서 template (frame 125 of A sentence)
tm=np.array(Image.open('all/d_125.png').convert('RGB')).astype(np.float32)
def alpha_strip(rgb,bg):
    L=rgb.mean(axis=2)
    return np.clip((bg-L)/(bg-25.0),0,1)
t_l1=alpha_strip(tm[S1[0]:S1[1],XL:XR],244.0)
SEO=t_l1[8:64,269-XL-2:304-XL+3].copy()   # 서 템플릿

def runs_of(alpha,thr=0.35):
    cols=(alpha>thr).any(axis=0)
    r=[];s=None
    for x,c in enumerate(cols):
        if c and s is None: s=x
        if (not c) and s is not None: r.append((s,x-1)); s=None
    if s is not None: r.append((s,len(cols)-1))
    return [(a+XL,b+XL) for a,b in r]

def group_words(rs,gapthr=14):
    ws=[]
    for r in rs:
        if ws and r[0]-ws[-1][-1][1]-1<=gapthr: ws[-1].append(r)
        else: ws.append([r])
    return ws

def process(arr):
    box=arr[Y0+22:Y0+200,95:985]
    L=box.mean(axis=2)
    if L.mean()<190: return arr
    bg=float(np.median(L[L>150]))
    if bg<180: return arr
    s1=arr[Y0+S1[0]:Y0+S1[1],XL:XR]; s2=arr[Y0+S2[0]:Y0+S2[1],XL:XR]
    a1=alpha_strip(s1.astype(np.float32),bg); a2=alpha_strip(s2.astype(np.float32),bg)
    if (a1>0.5).sum()<30: return arr
    res=cv2.matchTemplate(a1,SEO,cv2.TM_CCOEFF_NORMED)
    _,mx,_,loc=cv2.minMaxLoc(res)
    if mx<0.80: return arr
    mleft=loc[0]+XL+2
    r1=runs_of(a1); r2=runs_of(a2)
    cand=[r for r in r1 if abs(r[0]-mleft)<=5]
    if not cand: return arr
    nl=cand[0][0]
    after=[r for r in r1 if r[0]>=nl]
    words=group_words(after)
    name_word=words[0]
    rest=[(w,1) for w in words[1:]]
    # 이전 단어 사이 간격 보존용
    words2=group_words(r2)
    rest+= [(w,2) for w in words2]
    out=arr.copy()
    # 1) 지우기(inpaint)
    def erase(strip_rows,a,xmin):
        y0,y1=strip_rows
        sub=out[Y0+y0:Y0+y1,XL:XR].astype(np.float32)
        Ls=sub.mean(axis=2)
        bgc=np.median(sub[Ls>150],axis=0)
        sat=sub[...,0]-sub[...,2]
        m=((np.abs(Ls-bg)>2.5)&(sat<30)).astype(np.uint8)
        m[:, :max(xmin-XL-4,0)]=0
        # 박스 안쪽 가장자리(테두리) 보호
        m[:, :8]=0; m[:, -12:]=0
        if m.sum()==0: return
        m=cv2.dilate(m,np.ones((5,5),np.uint8))
        m[:, :max(xmin-XL-4,0)]=0
        sub[m>0]=bgc
        out[Y0+y0:Y0+y1,XL:XR]=np.clip(sub,0,255).astype(np.uint8)
    erase(S1,a1,nl); erase(S2,a2,XL)
    def patch(line,run):
        (y0,y1)=S1 if line==1 else S2
        return arr[Y0+y0:Y0+y1,run[0]-1:run[1]+2].copy()
    def put(line,x,p):
        (y0,y1)=S1 if line==1 else S2
        h,w=p.shape[:2]
        out[Y0+y0:Y0+y1,x-1:x-1+w]=p
    # 2) 이름 블록
    has_ik = len(name_word)>=2
    nblk=name_block(3 if has_ik else 1)
    def paint_name(x,blk):
        y=Y0+41; h,w=blk.shape
        reg=out[y:y+h,x:x+w].astype(np.float32)
        out[y:y+h,x:x+w]=(reg*(1-blk[...,None])+TXT*blk[...,None]).astype(np.uint8)
    paint_name(nl,nblk)
    cursor=nl+nblk.shape[1]; line=1
    # 이름 단어의 조사(은/의/이..)
    if has_ik and len(name_word)>2:
        base=name_word[1]; first=name_word[2]
        dx=(cursor+(first[0]-base[1]-1)) - first[0]
        for r in name_word[2:]:
            put(1,r[0]+dx,patch(1,r))
        cursor=name_word[-1][1]+dx
    elif not has_ik:
        cursor=nl+36
    # 3) 나머지 단어 재배치(줄바꿈 포함)
    prev_right_orig=name_word[-1][1]; prev_line=1
    for w,ln in rest:
        wl,wr=w[0][0],w[-1][1]; width=wr-wl+1
        if ln==prev_line and ln==line:
            gap=wl-prev_right_orig-1
        else:
            gap=21
        x=cursor+gap+1
        if line==1 and (x+width>LIMIT or ln==2):
            line=2; x=113
        dx=x-wl
        for r in w: put(line,r[0]+dx,patch(ln,r)) if False else None
        # 패치는 원래 줄에서 가져와서 새 줄에 붙임
        for r in w:
            p=patch(ln,r); put(line,r[0]+dx,p)
        cursor=wr+dx; prev_right_orig=wr; prev_line=ln
    return out

if __name__=='__main__':
    import subprocess
    src='/mnt/user-data/uploads/릴스_선수진화.mp4'
    dst=sys.argv[1]; test=len(sys.argv)>2
    W,H=1080,1920
    dec=subprocess.Popen(['ffmpeg','-v','error','-i',src,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    if test:
        want=set(int(x) for x in sys.argv[2].split(','))
        i=0
        while True:
            b=dec.stdout.read(W*H*3)
            if len(b)<W*H*3: break
            if i in want:
                a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
                o=process(a)
                Image.fromarray(o[Y0:Y0+260]).save(f'test_{i}.png')
            i+=1
        sys.exit()
    enc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-i',src,
        '-map','0:v','-map','1:a','-c:v','libx264','-crf','15','-preset','medium','-pix_fmt','yuv420p','-c:a','copy','-shortest',dst],stdin=subprocess.PIPE)
    while True:
        b=dec.stdout.read(W*H*3)
        if len(b)<W*H*3: break
        a=np.frombuffer(b,np.uint8).reshape(H,W,3).copy()
        enc.stdin.write(process(a).tobytes())
    enc.stdin.close(); enc.wait()
