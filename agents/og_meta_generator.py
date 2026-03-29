import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(override=True)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

CATEGORY_OG = {
    "물류자동화":   "/assets/images/og/logistics.png",
    "공장자동화":   "/assets/images/og/factory.png",
    "딥러닝비전":   "/assets/images/og/vision.png",
    "스마트팩토리": "/assets/images/og/smart.png",
    "제어SW":       "/assets/images/og/control.png",
}

def generate_description(title, content, category):
    prompt = f"다음 블로그 포스트의 SEO 메타 description을 한국어 120~155자로 작성해줘. 텍스트만 출력.\n제목: {title}\n카테고리: {category}\n본문: {content[:400]}"
    try:
        return model.generate_content(prompt).text.strip()[:160]
    except:
        return f"{category} 분야 최신 기술 트렌드와 아진네트웍스 자동화 솔루션을 소개합니다."

def build_front_matter(title, content, category, tags, date_str):
    desc = generate_description(title, content, category)
    og_img = CATEGORY_OG.get(category, "/assets/images/og-default.png")
    return f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str} +0900\ncategories: [{category}]\ntags: [{', '.join(tags)}]\ndescription: \"{desc}\"\nog_image: \"{og_img}\"\n---\n"
