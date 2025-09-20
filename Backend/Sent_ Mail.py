#Mail API
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(receiver_email, verification_code):
    sender_email = "tailin1125@gmail.com" #改成寄信者的Mail
    password = "ceaa fcfl wubf mjss"      #Google 二次驗證帳號後會有應用程式碼Token可以拿
    message = MIMEMultipart("alternative")
    subject = "注册帐号验证"
    text = f"""
    用户您好,
    以下是您的验证码: {verification_code}
    透过此验证码来建立帐户，谢谢。
    """
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    part1 = MIMEText(text, "plain")
    message.attach(part1)
    smtp_server = "smtp.gmail.com"
    port = 465
    try:
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    receiver_email = "wensmallyi@gmail.com"
    verification_code = "56789"
    send_email(receiver_email, verification_code)