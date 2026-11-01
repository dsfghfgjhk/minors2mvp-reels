import subprocess, base64, json, os
O='/mnt/user-data/outputs/'; U='/mnt/user-data/uploads/'
def thumb(path,ss=None):
    out='/tmp/t.jpg'
    if path.endswith('.png'):
        subprocess.run(['ffmpeg','-y','-v','error','-i',path,'-vf','scale=270:-1','-q:v','5',out])
    else:
        d=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',path],capture_output=True,text=True).stdout)
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(d*(ss or 0.4)),'-i',path,'-frames:v','1','-vf','scale=270:-1','-q:v','5',out])
    return 'data:image/jpeg;base64,'+base64.b64encode(open(out,'rb').read()).decode()
DON="{n}님 후원 감사합니다 💛\n1,000원 이상 후원하면 너의 이름으로도 릴스 만들어 드려요!\n🔗 minors2mvp.pages.dev"
def don(n,tag,key,t2,f,ss=0.4):
    return dict(g='후원 감사',file=f,thumb=O+f,ss=ss,titles=[f"후원자 {n}님의 {key}",t2],cap=DON.format(n=n),tags=f"#야구 #{tag} #후원감사 #야구게임 #2군에서MVP까지")
C=[
 dict(g='후원 장려',file='릴스_후원장려.mp4',thumb=O+'릴스_후원장려.mp4',ss=0.3,titles=["이 게임 무료인데 서버비는 누가 낼까?","개발자 영수증 뽑아봤더니 서버비가 내 몫이었다"],cap="광고 없는 무료 야구 게임, 서버비는 개발자가 내는 중 🥲\n1,000원 이상 후원하면 내 이름으로 릴스 제작!\n후원은 게임 오른쪽 아래 '개발자 서버비 내주기'\n🔗 minors2mvp.pages.dev",tags="#야구 #야구게임 #2군에서MVP까지 #후원 #인디게임"),
 don("박시영","진화","야구선수 진화 과정","고교 유망주가 메이저리그 MVP까지 가는 과정","릴스_선수진화_박시영.mp4",0.5),
 don("이재준","주식","선수 주식 차트 📈","공모가 0.3억 선수가 412억 찍고 상장폐지됨","릴스_선수주식_이재준.mp4",0.35),
 don("김민준","진화","야구선수 진화 과정","고교 유망주가 메이저리그 MVP까지 가는 과정","릴스_선수진화_김민준.mp4",0.5),
 don("유동주","주식","선수 주식 차트 📈","공모가 0.3억 선수가 412억 찍고 상장폐지됨","릴스_선수주식_유동주.mp4",0.35),
 don("김현서","연봉","인생, 1초에 1살","연봉 1등 김현서의 21년, 1초에 1살로 압축함","릴스_1초에1살_연봉1등_김현서.mp4",0.35),
 don("해녀 이정숙","저점매수","저점매수 수익률","해녀 이정숙을 3천만원에 샀더니 수익률이 이렇게 나옴","릴스_저점매수_해녀이정숙.mp4",0.4),
 dict(g='일반 릴스',file='릴스_타격힘2배.mp4 (픽셀 임시본)',thumb=O+'릴스_타격힘2배.mp4',ss=0.4,titles=["타자가 공 칠 때마다 힘이 2배가 된다면?","24번 치면 공이 빛보다 빨라져서 안 보임"],cap="150km/h에서 시작해서 24번 치면… 🌍\n우리 게임 타구는 정상 속도임 ㅋㅋ\n🔗 minors2mvp.pages.dev",tags="#야구 #만약에 #상상 #야구게임 #2군에서MVP까지"),
 dict(g='일반 릴스',file='변화구 영상 (.mov)',thumb=U+'db8a54a233c34e4aa9e20481c403d315.mov',ss=0.5,titles=["이 변화구, 칠 수 있겠어?","145km/h 직구, 커브, 스위퍼. 타이밍 못 맞추면 삼진"],cap="직구는 빠르게 꽂히고, 커브는 끝에서 떨어지고, 스위퍼는 옆으로 휘어져 ⚾\n던지는 것도 치는 것도 직접! 타이밍 맞춰서 쳐봐\n🔗 minors2mvp.pages.dev",tags="#야구 #야구게임 #변화구 #스위퍼 #커브 #2군에서MVP까지"),
 dict(g='일반 릴스',file='9회말 영상 (.mov)',thumb=U+'8688a5bf8ce2421eb175b155a59885e8.mov',ss=0.3,titles=["9회말 2아웃, 2:3. 끝낼 사람은 너","9회말 2아웃 역전 끝내기 홈런을 직접 쳐봤다"],cap="2:3으로 지고 있는 9회말 2아웃 1, 2루… 딱 한 번 타이밍만 맞으면 끝내기 홈런 5:3 역전승 🔥\n너라면 칠 수 있어?\n🔗 minors2mvp.pages.dev",tags="#야구 #야구게임 #끝내기홈런 #역전승 #9회말 #2군에서MVP까지"),
 dict(g='일반 릴스',file='고1 OVR 45 영상 (.mov)',thumb=U+'b0194e2f01d24040b901a8f9ba03cb0a.mov',ss=0.2,titles=["고1, OVR 45. 여기서 MVP까지?","OVR 45 고1 선수가 KBO MVP까지 가는 과정"],cap="성장 방향은 네가 정해 💪\n고교 유망주에서 드래프트, 그리고 KBO MVP까지. 너의 야구 인생은 어디까지 갈까?\n🔗 minors2mvp.pages.dev",tags="#야구 #야구게임 #KBO #MVP #성장게임 #2군에서MVP까지"),
 dict(g='스토리',file='스토리_이재준후원감사.png',thumb=O+'스토리_이재준후원감사.png',titles=[],cap="이재준님 후원 감사합니다 💛\n(사이트 주소에 링크 스티커 붙이기)",tags=""),
 dict(g='스토리',file='스토리_박시영후원감사.png',thumb=O+'스토리_박시영후원감사.png',titles=[],cap="박시영님 후원 감사합니다 💛\n(사이트 주소에 링크 스티커 붙이기)",tags=""),
]
for c in C: c['img']=thumb(c.pop('thumb'),c.pop('ss',None))
html=open('tpl.html').read().replace('__DATA__',json.dumps(C,ensure_ascii=False))
open(O+'릴스_업로드보드.html','w').write(html); print(len(html)//1024,'KB')
