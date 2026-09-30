"""Render the reviewed APIx plan as a paginated, searchable PDF.
Run: python3 docs/apix-v3/build_pdf.py
Requires reportlab. Product code is not changed by this script.
"""
from pathlib import Path
from html import escape
import re
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / 'APIx_SIH2026_Architecture_Plan_v3.md'
OUTPUT = ROOT / 'APIx_SIH2026_Architecture_Plan_v3.pdf'
FONTDIR = Path('/usr/share/fonts/truetype/dejavu')
for name, filename in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Italic','DejaVuSans-Oblique.ttf'),('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTDIR / filename)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
NAVY=colors.HexColor('#112C40'); TEAL=colors.HexColor('#087F8C'); INK=colors.HexColor('#233746'); MUTED=colors.HexColor('#58707F'); PALE=colors.HexColor('#EDF5F6'); LINE=colors.HexColor('#CDDDE3'); GOLD=colors.HexColor('#D59025')
W,H=A4; LEFT=44; WIDTH=W-88; TOP=H-68; BOTTOM=49
STYLES={
'p':ParagraphStyle('p',fontName='Body',fontSize=9.25,leading=13.3,textColor=INK,spaceAfter=7),
'h1':ParagraphStyle('h1',fontName='Bold',fontSize=20,leading=25,textColor=NAVY,spaceAfter=15),
'h2':ParagraphStyle('h2',fontName='Bold',fontSize=11.2,leading=15,textColor=TEAL,spaceBefore=7,spaceAfter=6),
'td':ParagraphStyle('td',fontName='Body',fontSize=8.1,leading=11.3,textColor=INK),
'th':ParagraphStyle('th',fontName='Bold',fontSize=8.2,leading=11.3,textColor=colors.white),
'code':ParagraphStyle('code',fontName='Mono',fontSize=7.7,leading=11,textColor=NAVY,backColor=PALE,borderPadding=8,spaceAfter=10),
'bullet':ParagraphStyle('bullet',fontName='Body',fontSize=9.1,leading=13.1,textColor=INK,leftIndent=12,firstLineIndent=-10,spaceAfter=5)
}

def markup(s):
    s=escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',lambda m:'<a href="'+m.group(2)+'" color="#087F8C"><u>'+m.group(1)+'</u></a>',s)
    s=re.sub(r'`([^`]+)`',r'<font name="Mono" size="8">\1</font>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',s)
    return s

class Diagram(Flowable):
    def __init__(self,kind):
        Flowable.__init__(self); self.kind=kind; self.width=WIDTH
        self.height={'architecture':335,'lifecycle':156,'lineage':160}[kind]
    def draw(self):
        c=self.canv
        def box(x,y,w,h,title,sub='',fill=PALE):
            c.setFillColor(fill); c.setStrokeColor(LINE); c.roundRect(x,y,w,h,5,fill=1,stroke=1)
            p=Paragraph('<b>'+title+'</b>'+('<br/>'+sub if sub else ''),ParagraphStyle('diagram',fontName='Body',fontSize=8.0,leading=10.5,textColor=NAVY,alignment=1))
            _,ph=p.wrap(w-12,h-8); p.drawOn(c,x+6,y+(h-ph)/2)
        def arrow(x1,y1,x2,y2,col=TEAL):
            import math
            c.setStrokeColor(col);c.setFillColor(col);c.setLineWidth(1.2);c.line(x1,y1,x2,y2)
            a=math.atan2(y2-y1,x2-x1);l=5
            p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-l*math.cos(a-.48),y2-l*math.sin(a-.48));p.lineTo(x2-l*math.cos(a+.48),y2-l*math.sin(a+.48));p.close();c.drawPath(p,stroke=0,fill=1)
        if self.kind=='architecture':
            x=0; pw=310; sx=334; sw=WIDTH-sx
            rows=[('PERMITTED SOURCES','Airline sites • OTAs • approved feeds'),('POLICY + SAMPLING','Access decision • quotas • fixed search jobs'),('SAFAR COLLECT WORKERS','HTTP / browser • sessions • source adapters'),('NORMALIZE + QUALIFY','Price components • products • evidence checks'),('BUILD + PUBLISH RELEASE','Fixed basket • missingness • versioned manifest'),('FASTAPI → REACT CONSOLE','Index • coverage • API • protected lineage')]
            sides=[('VERSIONED INPUTS','PSD basket / method config'),('POSTGRES JOBS','Leases • retries • run audit'),('EVIDENCE STORE','Redacted HTML/JSON • hashes'),('POSTGRES QUOTES','Raw + normalized versions'),('POSTGRES RELEASES','Cells • immutable revisions'),('INDEPENDENT BENCHMARK','Verified file → comparison')]
            for i,((t,s),(rt,rs)) in enumerate(zip(rows,sides)):
                y=280-i*54
                box(0,y,pw,42,t,s);box(sx,y,sw,42,rt,rs,colors.HexColor('#F7F4ED'))
                if i<5:arrow(pw/2,y,pw/2,y-12)
                if i==0:arrow(sx,y+15,pw,y+15)
                else:arrow(pw,y+21,sx,y+21)
            c.setFont('Italic',7.3);c.setFillColor(MUTED);c.drawString(0,0,'All Postgres boxes refer to one authoritative database; evidence bytes live separately.')
        elif self.kind=='lifecycle':
            bw=112;gap=(WIDTH-bw*4)/3;xs=[i*(bw+gap) for i in range(4)]
            labels=[('PLANNED','unique logical key'),('LEASED','token + heartbeat'),('FETCHED','evidence persisted'),('COMPLETED','atomic acceptance')]
            for i,(t,s) in enumerate(labels):
                box(xs[i],97,bw,42,t,s)
                if i<3:arrow(xs[i]+bw,118,xs[i+1],118)
            box(xs[0],20,bw,43,'DENIED / EXPIRED','policy or deadline',colors.HexColor('#F7F4ED'))
            box(xs[1],20,bw,43,'RETRY_WAIT','bounded cooldown',colors.HexColor('#F7F4ED'))
            box(xs[2],20,bw,43,'QUARANTINED','drift / incomplete',colors.HexColor('#F7F4ED'))
            box(xs[3],20,bw,43,'FAILED / BLOCKED','terminal reason',colors.HexColor('#F7F4ED'))
            for i in range(4):arrow(xs[i]+bw/2,97,xs[i]+bw/2,63,GOLD)
            c.setFont('Italic',7.1);c.setFillColor(MUTED);c.drawString(0,4,'Failure classifications depend on stage; only retryable states return to the queue within deadline.')
        elif self.kind=='lineage':
            bw=112;gap=(WIDTH-bw*4)/3;xs=[i*(bw+gap) for i in range(4)]
            for i,(t,s) in enumerate([('RAW EVIDENCE','capture time + hash'),('NORMALIZED QUOTE','raw ID + rule version'),('CELL VALUE','quote IDs + weights'),('INDEX RELEASE','manifest + revision')]):
                box(xs[i],87,bw,47,t,s)
                if i<3:arrow(xs[i]+bw,110,xs[i+1],110)
            box(0,15,WIDTH,45,'REPRODUCIBLE INPUT MANIFEST','Source policy • adapter • basket • baseline • method • code commit',colors.HexColor('#F7F4ED'))
            for i in range(4):arrow(xs[i]+bw/2,60,xs[i]+bw/2,87)

def table(lines):
    rows=[[x.strip() for x in line.strip().strip('|').split('|')] for line in lines]
    rows=[r for r in rows if not all(re.fullmatch(r':?-+:?',c.replace(' ','')) for c in r)]
    n=len(rows[0]); fractions={2:[.31,.69],3:[.23,.36,.41]}[n]
    # Different tables benefit from larger implementation/acceptance columns.
    if rows[0][0] in ('Time','Priority'): fractions=[.18,.43,.39]
    data=[[Paragraph(markup(cell),STYLES['th' if j==0 else 'td']) for cell in row] for j,row in enumerate(rows)]
    t=Table(data,colWidths=[WIDTH*f for f in fractions],hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,0),(-1,0),.6,NAVY),('LINEBELOW',(0,1),(-1,-1),.35,LINE)]))
    return t

def parse(section):
    lines=section.strip().splitlines(); out=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('```'):
            i+=1;code=[]
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            out.append(Paragraph('<br/>'.join(escape(x).replace(' ','&#160;') for x in code),STYLES['code']));i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'):block.append(lines[i]);i+=1
            out.extend([table(block),Spacer(1,9)]);continue
        if line.startswith('[['):out.extend([Diagram(line[2:-2]),Spacer(1,9)]);i+=1;continue
        if line.startswith('# '):out.append(Paragraph(markup(line[2:]),STYLES['h1']));i+=1;continue
        if line.startswith('## '):out.append(Paragraph(markup(line[3:]),STYLES['h2']));i+=1;continue
        if line.startswith('- '):out.append(Paragraph('• '+markup(line[2:]),STYLES['bullet']));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','- ','[[')):
            parts.append(lines[i].strip());i+=1
        out.append(Paragraph(markup(' '.join(parts)),STYLES['p']))
    return out

def flow_height(fs):
    total=0
    for f in fs:
        _,h=f.wrap(WIDTH,H*10);total+=h+getattr(f,'spaceBefore',0)+getattr(f,'spaceAfter',0)
    return total

def draw_flows(c,fs,start_y,scale=1):
    c.saveState();c.translate(LEFT,start_y);c.scale(scale,scale);y=0
    for f in fs:
        y-=getattr(f,'spaceBefore',0);_,h=f.wrap(WIDTH,H*10);y-=h;f.drawOn(c,0,y);y-=getattr(f,'spaceAfter',0)
    c.restoreState()

def chrome(c,page,total,title):
    c.setFillColor(NAVY);c.rect(0,H-8,W,8,fill=1,stroke=0)
    c.setFont('Bold',8.2);c.setFillColor(TEAL);c.drawString(LEFT,H-36,'APIx / SAFAR')
    c.setFont('Body',7.7);c.setFillColor(MUTED);c.drawRightString(W-LEFT,H-36,'SIH 2026  ·  PS 26056  ·  ARCHITECTURE v3')
    c.setStrokeColor(LINE);c.line(LEFT,37,W-LEFT,37)
    c.setFont('Body',7);c.drawString(LEFT,24,'30 SEP 2026  •  Proposed design / evidence-aware delivery plan')
    c.drawRightString(W-LEFT,24,f'{page:02d} / {total:02d}')
    c.bookmarkPage(f'p{page}');c.addOutlineEntry(title,f'p{page}',level=0,closed=False)

def cover(c,section,total):
    c.setFillColor(NAVY);c.rect(0,H-325,W,325,fill=1,stroke=0)
    c.setFillColor(TEAL);c.rect(LEFT,H-63,55,5,fill=1,stroke=0)
    c.setFont('Bold',10);c.setFillColor(colors.HexColor('#9FDADD'));c.drawString(LEFT,H-93,'SIH 2026 / PROBLEM STATEMENT 26056')
    c.setFont('Bold',48);c.setFillColor(colors.white);c.drawString(LEFT,H-160,'APIx / SAFAR')
    st=ParagraphStyle('cover',fontName='Body',fontSize=20,leading=28,textColor=colors.white)
    p=Paragraph('A trustworthy airfare index,<br/>built on your own collection engine',st);_,h=p.wrap(WIDTH,100);p.drawOn(c,LEFT,H-185-h)
    c.setFont('Body',9);c.setFillColor(colors.HexColor('#B4C9D2'));c.drawString(LEFT,H-300,'ARCHITECTURE REVIEW + DETAILED DELIVERY PLAN  /  VERSION 3')
    ls=section.strip().splitlines(); start=next(i for i,l in enumerate(ls) if l.startswith('Build a purpose'))
    fs=parse('\n'.join(ls[start:]));height=flow_height(fs);scale=min(1,(H-365-65)/height)
    draw_flows(c,fs,H-360,scale)
    c.setStrokeColor(LINE);c.line(LEFT,37,W-LEFT,37);c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(LEFT,24,'Prepared 30 September 2026 • Editable source included');c.drawRightString(W-LEFT,24,f'01 / {total:02d}')
    c.bookmarkPage('p1');c.addOutlineEntry('APIx / SAFAR — Architecture v3','p1',0)
    return scale

def main():
    sections=SOURCE.read_text().split('---PAGE---'); total=len(sections)
    c=canvas.Canvas(str(OUTPUT),pagesize=A4,pageCompression=1)
    c.setTitle('APIx / SAFAR — SIH 2026 Architecture and Detailed Plan v3')
    c.setAuthor('APIx / SAFAR project planning review')
    c.setSubject('PS 26056: own collection engine inspired by Scrapling; statistical methodology and delivery plan')
    report=[]
    for i,section in enumerate(sections,1):
        title=section.strip().splitlines()[0].lstrip('# ')
        if i==1:scale=cover(c,section,total);height=0
        else:
            chrome(c,i,total,title);fs=parse(section);height=flow_height(fs);scale=min(1,(TOP-BOTTOM)/height)
            if scale<.80:raise ValueError(f'Page {i} needs excessive shrink {scale:.3f}; edit content/layout')
            draw_flows(c,fs,TOP,scale)
        report.append(f'{i:02d}\t{scale:.3f}\t{height:.1f}\t{title}')
        c.showPage()
    c.save();(HERE/'layout-report.txt').write_text('\n'.join(report)+'\n')
    print(f'Created {OUTPUT} ({total} pages)');print('\n'.join(report))

if __name__=='__main__':main()
