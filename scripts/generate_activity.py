"""Generate a 31-day contribution chart using GitHub's API; standard library only."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import time
import urllib.request

def render(days, username, dark):
    if len(days)!=31 or any(not isinstance(d['contributionCount'],int) or d['contributionCount']<0 for d in days):
        raise ValueError('Expected 31 daily contribution counts')
    bg,fg,muted,grid,line,fill=('#0b1220','#f1f5f9','#94a3b8','#233341','#5eead4','#123b39') if dark else ('#ffffff','#0f172a','#64748b','#e2e8f0','#059669','#d1fae5')
    counts=[d['contributionCount'] for d in days]
    ceiling=max(4,((max(counts)+3)//4)*4)
    points=[(64+i*28.3,268-c/ceiling*160) for i,c in enumerate(counts)]
    coords=' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="340" viewBox="0 0 1000 340" role="img" aria-labelledby="title desc">',
         f'<title id="title">{html.escape(username)} contribution activity</title>',
         f'<desc id="desc">{sum(counts)} contributions across {sum(c>0 for c in counts)} active days in the last 31 days. Counts visible to the workflow token.</desc>',
         f'<rect width="1000" height="340" rx="16" fill="{bg}"/>',
         f'<g font-family="Arial, Helvetica, sans-serif"><text x="32" y="39" fill="{fg}" font-size="22" font-weight="700">Contribution activity</text>',
         f'<text x="32" y="66" fill="{muted}" font-size="13">{html.escape(username)} · last 31 days · updated {days[-1]["date"]} UTC</text>',
         f'<text x="950" y="39" text-anchor="end" fill="{line}" font-size="22" font-weight="700">{sum(counts):,}</text>',
         f'<text x="950" y="62" text-anchor="end" fill="{muted}" font-size="13">contributions</text>']
    for i in range(5):
        y=268-i*40;value=ceiling*i//4
        out+=[f'<path d="M64 {y}H913" stroke="{grid}"/>',f'<text x="50" y="{y+4}" text-anchor="end" fill="{muted}" font-size="11">{value}</text>']
    out+=[f'<polygon points="64,268 {coords} 913,268" fill="{fill}"/>',f'<polyline points="{coords}" fill="none" stroke="{line}" stroke-width="3" stroke-linejoin="round"/>']
    for i,(x,y) in enumerate(points):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{line}"><title>{days[i]["date"]}: {counts[i]} contributions</title></circle>')
    for i in [0,5,10,15,20,25,30]:
        date=dt.date.fromisoformat(days[i]['date']).strftime('%d %b')
        out.append(f'<text x="{points[i][0]:.1f}" y="293" text-anchor="middle" fill="{muted}" font-size="11">{date}</text>')
    out.append(f'<text x="32" y="322" fill="{muted}" font-size="11">Source: GitHub contribution calendar · Today may be incomplete</text></g></svg>')
    return '\n'.join(out)

def fetch_days(username, token):
    today=dt.datetime.now(dt.timezone.utc).date()
    start=today-dt.timedelta(days=30)
    query='''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''
    body=json.dumps({'query':query,'variables':{'login':username,'from':f'{start}T00:00:00Z','to':dt.datetime.now(dt.timezone.utc).isoformat()}}).encode()
    request=urllib.request.Request('https://api.github.com/graphql',data=body,headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','User-Agent':'profile-contribution-chart'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
            if data.get('errors'):raise RuntimeError('; '.join(e['message'] for e in data['errors']))
            calendar=data['data']['user']['contributionsCollection']['contributionCalendar']
            days=sorted((d for w in calendar['weeks'] for d in w['contributionDays'] if str(start)<=d['date']<=str(today)),key=lambda d:d['date'])
            if len(days)!=31:raise ValueError('GitHub returned an incomplete date range')
            return days
        except Exception:
            if attempt==2:raise
            time.sleep(2**attempt)

if __name__=='__main__':
    username=os.environ.get('PROFILE_USERNAME') or os.environ['GITHUB_REPOSITORY_OWNER']
    days=fetch_days(username,os.environ['GITHUB_TOKEN'])
    out=Path('dist');out.mkdir(exist_ok=True)
    for dark,suffix in [(False,''),(True,'-dark')]:
        (out/f'activity{suffix}.svg').write_text(render(days,username,dark),encoding='utf-8')
    print(f'Generated contribution charts for {username}: {len(days)} days')
