# 아진네트웍스 블로그 관리 목차 v1.0

## 1. 시스템 구조 개요

```
자동화 파이프라인
트렌드 수집 → 주제 선정 → 본문 작성 → 검수 → 이미지 삽입 → 발행 → 이메일 알림
```

### 파일 구조
```
blog_agent/
├── agents/
│   ├── trend_agent.py        # 트렌드 크롤링
│   ├── writer_agent.py       # 포스트 작성
│   ├── reviewer_agent.py     # 품질 검수
│   ├── github_publisher.py   # GitHub 발행
│   ├── image_optimizer.py    # 이미지 최적화 ← NEW
│   └── email_notifier.py     # 이메일 알림 ← NEW
├── config/
│   └── settings.yaml         # 전역 설정
├── prompts/
│   ├── writer_prompt.md      # 작성 프롬프트 (SEO 강화) ← UPDATED
│   └── reviewer_prompt.md    # 검수 프롬프트
├── scripts/
│   ├── run_agent.py          # 메인 실행
│   └── scheduler.py          # 스케줄러
└── output/
    ├── drafts/               # 초안
    ├── published/            # 발행 완료
    └── logs/                 # 실행 로그
```

---

## 2. SEO 관리 목차

### 2-1. 타겟 키워드 현황
| 구분 | 키워드 | 우선순위 |
|------|--------|---------|
| 주력 | 공장자동화, 스마트팩토리 | ★★★ |
| 주력 | 딥러닝 비전검사, 머신비전 | ★★★ |
| 주력 | CNC 자동화, 물류자동화 | ★★★ |
| 롱테일 | 공장자동화 전문기업 | ★★☆ |
| 롱테일 | 아산 자동화설비 | ★★☆ |
| 브랜드 | 아진네트웍스 | ★★★ |

### 2-2. 포스트 SEO 체크리스트
- [ ] 제목에 주력 키워드 포함 (35~60자)
- [ ] 메타 설명 120~150자 (키워드 포함)
- [ ] 첫 문단에 키워드 자연스럽게 포함
- [ ] H2/H3 소제목에 관련 키워드 분산
- [ ] 이미지 alt 태그에 키워드 포함
- [ ] 내부 링크 (ajinnetworks.co.kr 연결)
- [ ] 결론부 아진네트웍스 자연스러운 1회 언급

### 2-3. Google Search Console 관리
- 속성: https://ajinnetworks.github.io/
- 색인 확인: 주 1회
- 사이트맵: /sitemap.xml (자동 생성)
- 색인 요청: 신규 포스트 발행 시마다

### 2-4. 네이버 서치어드바이저 관리
- 사이트: https://ajinnetworks.github.io
- 사이트맵 제출: 완료 (26.03.23)
- URL 수집 요청: 신규 포스트 발행 시마다

---

## 3. 이미지 관리 목차

### 3-1. 이미지 표준 사이즈
| 용도 | 가로 | 세로 | 비율 |
|------|------|------|------|
| 대표이미지(hero) | 1200px | 630px | 16:8.4 |
| 본문 이미지 | 800px | 450px | 16:9 |
| 인라인 이미지 | 600px | 338px | 16:9 |

### 3-2. 이미지 소스
1. Unsplash API (자동) - UNSPLASH_ACCESS_KEY 필요
2. Picsum Photos (폴백) - 공장/기술 관련 기본 이미지
3. 직접 업로드 - GitHub _posts/images/ 폴더

### 3-3. 이미지 최적화 규칙
```html
<!-- 올바른 이미지 태그 형식 -->
![공장자동화 이미지](이미지URL)
{: width="800" height="450" loading="lazy" 
   style="width:100%;height:auto;border-radius:8px;"}
```

---

## 4. 포스팅 관리 목차

### 4-1. 자동 발행 스케줄
| 요일 | 시간(KST) | 상태 |
|------|-----------|------|
| 화요일 | 09:00 | ✅ 활성 |
| 목요일 | 09:00 | ✅ 활성 |
| 토요일 | 09:00 | ✅ 활성 |

### 4-2. 포스트 품질 기준
| 항목 | 기준 | 가중치 |
|------|------|--------|
| SEO | 25점 이상 | 30% |
| 가독성 | 25점 이상 | 30% |
| 구조 | 15점 이상 | 20% |
| 사실성 | 15점 이상 | 20% |
| **합계** | **75점 이상** | **통과** |

### 4-3. 카테고리 구조
- 공장자동화
- 스마트팩토리
- 딥러닝/AI
- 물류자동화
- 기술분석
- 소개

---

## 5. 이메일 알림 관리

### 5-1. 알림 설정
- 수신: wave624@gmail.com
- 발송: Gmail SMTP
- 시점: 포스팅 완료 즉시

### 5-2. 필요한 환경변수 (GitHub Secrets)
| 변수명 | 설명 |
|--------|------|
| ANTHROPIC_API_KEY | Claude API 키 |
| BLOG_GITHUB_TOKEN | GitHub 토큰 |
| BLOG_REPO | ajinnetworks/ajinnetworks.github.io |
| GMAIL_USER | 발신 Gmail 주소 |
| GMAIL_APP_PASSWORD | Gmail 앱 비밀번호 |
| UNSPLASH_ACCESS_KEY | Unsplash API 키 (선택) |
| NOTIFY_EMAIL | 수신 이메일 (기본: wave624@gmail.com) |

---

## 6. 월간 관리 체크리스트

### 매주
- [ ] GA4 방문자 수 확인
- [ ] Search Console 색인 페이지 수 확인
- [ ] 자동 포스팅 정상 실행 확인 (이메일 알림)
- [ ] 네이버 신규 포스트 URL 수집 요청

### 매월
- [ ] 상위 노출 키워드 분석
- [ ] 포스트 품질 점수 평균 확인
- [ ] API 사용량 및 비용 확인
- [ ] writer_prompt.md 키워드 업데이트
- [ ] GitHub Secrets 만료 여부 확인

---

## 7. 트러블슈팅 가이드

### 포스팅 실패 시
```
1. GitHub Actions 로그 확인
2. ANTHROPIC_API_KEY 유효성 확인
3. run_agent.py 로컬 테스트 실행
4. output/logs/ 에러 로그 확인
```

### 이메일 알림 미수신 시
```
1. GMAIL_USER, GMAIL_APP_PASSWORD 확인
2. Gmail 앱 비밀번호 재발급
   (Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호)
3. 스팸함 확인
```

### 이미지 표시 안 될 시
```
1. UNSPLASH_ACCESS_KEY 확인
2. Picsum 폴백 이미지 작동 여부 확인
3. 이미지 URL 직접 접속 테스트
```
