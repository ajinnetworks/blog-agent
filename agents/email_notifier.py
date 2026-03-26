"""
email_notifier.py — 포스팅 완료 이메일 알림
포스팅 완료 시 wave624@gmail.com으로 결과 발송
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


def send_post_notification(results: list[dict]) -> bool:
    """
    포스팅 완료 후 이메일 알림 발송.
    
    환경변수 필요:
    - NOTIFY_EMAIL: 수신 이메일 (기본: wave624@gmail.com)
    - GMAIL_USER: 발신 Gmail 주소
    - GMAIL_APP_PASSWORD: Gmail 앱 비밀번호
    """
    try:
        notify_email = os.environ.get("NOTIFY_EMAIL", "wave624@gmail.com")
        gmail_user = os.environ.get("GMAIL_USER", "")
        gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

        if not gmail_user or not gmail_password:
            logger.warning("Gmail 설정 없음 — 이메일 알림 스킵")
            return False

        now = datetime.now(KST).strftime("%Y년 %m월 %d일 %H:%M")
        success_posts = [r for r in results if not r.get("error")]
        fail_posts = [r for r in results if r.get("error")]

        # 이메일 제목
        subject = f"[아진네트웍스 블로그] {now} 자동 포스팅 완료 ({len(success_posts)}개)"

        # HTML 본문 생성
        post_rows = ""
        for post in success_posts:
            url = post.get("blog_url", "#")
            title = post.get("title", "제목 없음")
            score = post.get("review_result", {}).get("total_score", "N/A")
            post_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee;">
                    <a href="{url}" style="color:#1a73e8;text-decoration:none;">
                        {title}
                    </a>
                </td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">
                    {score}점
                </td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">
                    <span style="color:green;">✅ 성공</span>
                </td>
            </tr>"""

        for post in fail_posts:
            title = post.get("title", "제목 없음")
            error = post.get("error", "알 수 없는 오류")
            post_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee;">{title}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">-</td>
                <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">
                    <span style="color:red;">❌ 실패: {error[:50]}</span>
                </td>
            </tr>"""

        html_body = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head><meta charset="UTF-8"></head>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            
            <div style="background:#1a3a5c;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h1 style="margin:0;font-size:20px;">🤖 아진네트웍스 블로그 자동 포스팅</h1>
                <p style="margin:5px 0 0;opacity:0.8;">{now} 완료</p>
            </div>

            <div style="background:#f8f9fa;padding:20px;border:1px solid #dee2e6;">
                
                <div style="display:flex;gap:20px;margin-bottom:20px;">
                    <div style="background:white;padding:15px;border-radius:8px;flex:1;text-align:center;border:1px solid #dee2e6;">
                        <div style="font-size:32px;font-weight:bold;color:#28a745;">{len(success_posts)}</div>
                        <div style="color:#666;font-size:14px;">성공</div>
                    </div>
                    <div style="background:white;padding:15px;border-radius:8px;flex:1;text-align:center;border:1px solid #dee2e6;">
                        <div style="font-size:32px;font-weight:bold;color:#dc3545;">{len(fail_posts)}</div>
                        <div style="color:#666;font-size:14px;">실패</div>
                    </div>
                    <div style="background:white;padding:15px;border-radius:8px;flex:1;text-align:center;border:1px solid #dee2e6;">
                        <div style="font-size:32px;font-weight:bold;color:#1a73e8;">{len(results)}</div>
                        <div style="color:#666;font-size:14px;">전체</div>
                    </div>
                </div>

                <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;border:1px solid #dee2e6;">
                    <thead>
                        <tr style="background:#1a3a5c;color:white;">
                            <th style="padding:10px;text-align:left;">포스트 제목</th>
                            <th style="padding:10px;text-align:center;width:80px;">검수점수</th>
                            <th style="padding:10px;text-align:center;width:100px;">상태</th>
                        </tr>
                    </thead>
                    <tbody>
                        {post_rows}
                    </tbody>
                </table>

            </div>

            <div style="background:#1a3a5c;color:white;padding:15px;border-radius:0 0 8px 8px;text-align:center;">
                <a href="https://ajinnetworks.github.io" 
                   style="color:#90caf9;text-decoration:none;">
                    📝 블로그 바로가기
                </a>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                <a href="https://www.ajinnetworks.co.kr" 
                   style="color:#90caf9;text-decoration:none;">
                    🏭 아진네트웍스 홈페이지
                </a>
            </div>

        </body>
        </html>
        """

        # 이메일 구성
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = notify_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Gmail SMTP 발송
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, notify_email, msg.as_string())

        logger.info(f"이메일 알림 발송 완료 → {notify_email}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False
