import requests
from bs4 import BeautifulSoup
import smtplib
import schedule
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================================
# 只需要改这里
# ============================================================

import os

ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
EMAIL_FROM     = os.environ.get("EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO       = os.environ.get("EMAIL_TO")

print(f"APP_ID读取结果: {ADZUNA_APP_ID}") #加这行代码用来输出读取结果

SEND_TIME      = "09:00"

JOB_KEYWORDS = [
    "Solutions Engineer",
    "Implementation Consultant",
    "Business Analyst Logistics",
    "Technical Consultant Supply Chain",
    "Pre-Sales Engineer",
]

# ============================================================
# 脚本逻辑，不需要修改
# ============================================================

IND_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"

def load_ind_companies():
    """直接从IND网页抓取认证公司名单"""
    print("正在从IND官网加载认证公司名单...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(IND_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        companies = set()
        for row in soup.find_all("tr"):
           th = row.find("th")
           if th:
            name = th.get_text(strip=True).lower()
            if name:
             companies.add(name)
             
        print(f"✅ 已加载 {len(companies)} 家IND认证公司")
        return companies
    except Exception as e:
        print(f"❌ 加载IND名单失败: {e}")
        return set()

def fetch_jobs(keyword):
    """从Adzuna抓取荷兰职位"""
    url = "https://api.adzuna.com/v1/api/jobs/nl/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": keyword,
        "results_per_page": 10,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            print(f"⚠️  Adzuna错误 [{keyword}]: {response.status_code}")
    except Exception as e:
        print(f"⚠️  抓取失败 [{keyword}]: {e}")
    return []

def is_ind_certified(company_name, ind_companies):
    """模糊匹配公司名"""
    name = company_name.lower().strip()
    # 去掉常见后缀再比较
    for suffix in [" b.v.", " n.v.", " bv", " nv", " b.v", " holding"]:
        name = name.replace(suffix, "")
    for ind in ind_companies:
        clean_ind = ind
        for suffix in [" b.v.", " n.v.", " bv", " nv", " b.v", " holding"]:
            clean_ind = clean_ind.replace(suffix, "")
        if clean_ind and (clean_ind in name or name in clean_ind):
            return True
    return False

def build_email_html(jobs):
    date_str = datetime.now().strftime("%Y-%m-%d")
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
        <h2 style="color:#2c3e50;">📋 每日职位推送 — {date_str}</h2>
        <p style="color:#666;">以下 {len(jobs)} 个职位来自IND认证公司，符合KM签证续签要求</p>
        <hr/>
    """
    for i, job in enumerate(jobs, 1):
        title    = job.get("title", "N/A")
        company  = job.get("company", {}).get("display_name", "N/A")
        location = job.get("location", {}).get("display_name", "N/A")
        url      = job.get("redirect_url", "#")
        desc     = job.get("description", "")[:250].strip()

        html += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;
                    padding:16px;margin:12px 0;background:#fafafa;">
            <h3 style="margin:0 0 6px 0;">
                {i}. <a href="{url}" style="color:#1a73e8;">{title}</a>
            </h3>
            <p style="margin:4px 0;"><strong>🏢 公司：</strong>{company}
               <span style="color:green;font-size:12px;">✔ IND认证</span></p>
            <p style="margin:4px 0;"><strong>📍 地点：</strong>{location}</p>
            <p style="margin:8px 0;color:#555;font-size:14px;">{desc}...</p>
            <a href="{url}" style="background:#1a73e8;color:white;padding:8px 16px;
               border-radius:4px;text-decoration:none;font-size:13px;">查看职位</a>
        </div>
        """
    html += "</div>"
    return html


def send_email(jobs): #为了用sendgrid免费发邮件的端口修改的
    if not jobs:
        print("今天没有找到符合条件的职位")
        return

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    html = build_email_html(jobs)
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=EMAIL_TO,
        subject=f"每日职位推送 {datetime.now().strftime('%Y-%m-%d')} — {len(jobs)}个职位",
        html_content=html
    )
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sg.send(message)
        print(f"✅ 邮件已发送，包含 {len(jobs)} 个职位")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")



#这是之前的 def send_email(jobs):
  #  if not jobs:
   #     print("今天没有找到符合条件的职位")
   #     return

   # html = build_email_html(jobs)
   # msg = MIMEMultipart("alternative")
   # msg["Subject"] = f"每日职位推送 {datetime.now().strftime('%Y-%m-%d')} — {len(jobs)}个职位"
   # msg["From"]    = EMAIL_FROM
   # msg["To"]      = EMAIL_TO
   # msg.attach(MIMEText(html, "html"))

  #  try:
  #      with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
  #          server.login(EMAIL_FROM, EMAIL_PASSWORD)
  #          server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
   #     print(f"✅ 邮件已发送，包含 {len(jobs)} 个职位")
  #  except Exception as e:
  #      print(f"❌ 邮件发送失败: {e}")

def daily_job():
    print(f"\n{'='*50}")
    print(f"开始抓取职位 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    ind_companies = load_ind_companies()
    if not ind_companies:
        return

    all_jobs = []
    seen_ids = set()

    for keyword in JOB_KEYWORDS:
        print(f"  搜索: {keyword}")
        jobs = fetch_jobs(keyword)
        for job in jobs:
            job_id = job.get("id")
            if job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(job)

    print(f"共抓取 {len(all_jobs)} 个职位，正在过滤IND认证公司...")
    filtered = [j for j in all_jobs
                if is_ind_certified(j.get("company", {}).get("display_name", ""), ind_companies)]
    filtered = filtered[:15]
    print(f"过滤后剩余 {len(filtered)} 个职位")

    send_email(filtered)

if __name__ == "__main__":
    print("🚀 Job Tracker 启动")
    print(f"每天 {SEND_TIME} 自动推送职位到 {EMAIL_TO}\n")

    daily_job()  # 立刻运行一次测试

    schedule.every().day.at(SEND_TIME).do(daily_job)
    while True:
        schedule.run_pending()
        time.sleep(60)
