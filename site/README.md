# OAuth 안내 사이트 초안

세 HTML 파일은 Dragondydals File Transfer의 공개 안내 문서입니다. 실제 운영 방식과 정책 문구를 검토한 뒤 게시합니다. Google Cloud의 앱 이름과 홈페이지 이름을 일치시키세요.

## 게시 상태
이 PR은 사이트 파일만 추가합니다. GitHub Pages 활성화, DNS 변경, Google 앱 게시 및 토큰 재발급은 수행하지 않습니다. API 키나 OAuth 토큰을 이 폴더에 넣지 마세요.

## GitHub Pages 배포
GitHub Pages를 GitHub Actions 소스로 활성화하고, pages artifact로 **site 폴더만** 업로드하는 배포 워크플로를 구성하세요. 저장소 전체 또는 기존 운영 문서가 든 docs 폴더를 배포 대상으로 선택하지 마세요.
기본 주소는 배포 성공 후 https://castle923.github.io/AutoRunpod/ 형식이 됩니다. 현재 작동하는 주소라는 뜻은 아닙니다.

## Google 설정
- 홈페이지: 실제 게시된 사이트의 /index.html
- 개인정보처리방침: 같은 사이트의 /privacy.html
- 서비스 약관: 같은 사이트의 /terms.html
- 승인된 도메인: 실제 소유권을 확인한 도메인 (스킴/경로 제외)

GitHub 저장소 소유권은 github.com 도메인 소유권과 다릅니다.
Google OAuth 도메인 검증 안내는 Search Console의 DNS 기반 Domain Property 검증을 요구합니다. github.io 기본 주소에는 사용자가 DNS TXT 레코드를 설정할 수 없으므로 기본 주소만으로 Google 검증 완료를 보장하지 않습니다. DNS를 관리하는 사용자 도메인을 GitHub Pages에 연결하는 경로가 필요할 수 있습니다.

https://support.google.com/cloud/answer/13804266?hl=en
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages

Google 앱의 프로덕션 전환 후 재인증하여 새 설정을 저장하고 자동 갱신을 확인합니다. 그 후 RunPod에서 지속적으로 보관되는 설정 파일과 별도 복호화 비밀번호를 연결해야 합니다. 웹사이트 게시만으로 토큰이 갱신되지는 않습니다.
