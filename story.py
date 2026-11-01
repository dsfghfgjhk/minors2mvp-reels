import sys; sys.path.insert(0,'/home/claude/sp')
from make import *
from PIL import Image, ImageDraw

def story(name,team,out):
    b=BG.copy()
    # 상단: 감사 영역
    put(b,chip("후원 감사",44,GOLD,(20,20,30)),540,300)
    put(b,T(f"{name}님",160,WHITE,True,6,(0,0,0)),540,470)
    row=T("후원 감사합니다",84,GOLD,True,5,(0,0,0))
    put(b,row,540,640)
    put(b,heart(9),540-row.width/2-70,640); put(b,heart(9),540+row.width/2+70,640)
    put(b,sprite(team,16),540,900)
    put(b,T("보내주신 후원은\n새 기능이랑 서버비에 쓸게요",42,(205,210,230),False,0,(0,0,0),12),540,1130)
    # 하단: 유도 카드
    card=rrect(920,430,40,(244,241,232,255))
    d=ImageDraw.Draw(card)
    t1=T("1,000원 이상 후원하면",52,(30,32,48),True); card.paste(t1,((920-t1.width)//2,36),t1)
    t2=T("내 이름으로 릴스 제작!",84,RED,True); card.paste(t2,((920-t2.width)//2,112),t2)
    t3=T("후원 버튼: 게임 오른쪽 아래 '개발자 서버비 내주기'",34,(80,82,98),False); card.paste(t3,((920-t3.width)//2,238),t3)
    pill=chip("minors2mvp.pages.dev",54,GOLD,(20,20,30)); card.paste(pill,((920-pill.width)//2,310),pill)
    put(b,card,540,1450)
    b.convert('RGB').save(out)

story("이재준","green","/mnt/user-data/outputs/스토리_이재준후원감사.png")
story("박시영","red","/mnt/user-data/outputs/스토리_박시영후원감사.png")
a=Image.open("/mnt/user-data/outputs/스토리_이재준후원감사.png").resize((540,960))
c=Image.open("/mnt/user-data/outputs/스토리_박시영후원감사.png").resize((540,960))
m=Image.new('RGB',(1080,960)); m.paste(a,(0,0)); m.paste(c,(540,0)); m.save('/home/claude/sp/story_prev.png')
