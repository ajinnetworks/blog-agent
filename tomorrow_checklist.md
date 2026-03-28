# 내일 실행 체크리스트

## 실행 전 확인
- [ ] Gemini RPD 리셋 확인 (KST 09:00 이후)
- [ ] .env BLOG_GITHUB_TOKEN 신규 토큰인지 확인

## 실행 순서
1. dry-run 먼저 실행
   ```
   cd "e:\아진네트웍스\Claude Code\블로그 제작\blog_agent"
   python scripts/run_agent.py --mode dry-run
   ```
2. dry-run 성공 확인 후 실제 발행
   ```
   python scripts/run_agent.py --mode once
   ```
3. GitHub Actions 빌드 1회 확인
   - https://github.com/ajinnetworks/ajinnetworks.github.io/actions

## 성공 기준
- [ ] STAGE 1: 트렌드 3개 선정
- [ ] STAGE 2: 포스트 3개 작성 (오류 없음)
- [ ] STAGE 3: 배치 검수 통과
- [ ] STAGE 4: GitHub 일괄 커밋 1회 발행
- [ ] GitHub Actions 빌드 green
