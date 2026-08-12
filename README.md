# 춤추전국시대 LIVE 12강 — GitHub + Render 배포용

이 폴더는 **Render Free Web Service**에 바로 배포할 수 있도록 정리한 패키지입니다.

## 배포 후 주소
Render 서비스 주소가 예를 들어 `https://oatd-live-bracket.onrender.com`이라면:

- TV/PPT 송출: `https://oatd-live-bracket.onrender.com/display`
- 스마트폰 운영자: `https://oatd-live-bracket.onrender.com/admin`
- 상태 확인: `https://oatd-live-bracket.onrender.com/health`
- 기본 운영 PIN: `0919`

## 1. GitHub
1. GitHub에서 새 저장소를 만듭니다. 예: `oatd-live-bracket`
2. **이 폴더 안의 파일과 폴더 전체**를 저장소 최상단(root)에 업로드합니다.
3. 저장소 첫 화면에 `server.py`, `render.yaml`, `templates`, `static`이 보이면 정상입니다.

## 2. Render — 가장 쉬운 Blueprint 방식
1. Render Dashboard → **New → Blueprint**
2. 위 GitHub 저장소를 연결합니다.
3. 저장소 루트의 `render.yaml`이 자동 인식됩니다.
4. Web Service가 생성되고 Deploy가 끝날 때까지 기다립니다.
5. Render가 발급한 `https://...onrender.com` 주소를 확인합니다.

## Render에서 수동 Web Service로 만들 경우
- Runtime: `Python 3`
- Build Command: `echo "No build step required"`
- Start Command: `python server.py`
- Instance Type: `Free`
- Region: `Singapore`
- Environment Variable: `ADMIN_PIN=0919`

## 현장 운영
1. 행사 **5~10분 전** `/display`를 먼저 열어 서버를 깨워둡니다.
2. 스마트폰에서 `/admin` → PIN 로그인.
3. 테스트 대진 2개 정도를 확정해 보고 → `전체 초기화` 후 본 진행.
4. 송출 화면은 대진표 → 랜덤 제비카드 → 대진 확정 후 대진표 순으로 자동 전환됩니다.
5. 운영자 브라우저에는 최신 상태가 자동 백업됩니다. Render가 재시작되어 서버 대진이 초기화된 경우 `브라우저 백업으로 서버 상태 복구`를 사용합니다.

## 주의
Render Free Web Service는 오랫동안 요청이 없으면 스핀다운될 수 있고, Free 서비스의 로컬 파일은 재시작/스핀다운 시 유지되지 않습니다. **실제 진행 중에는 `/display`가 계속 상태 요청을 보내므로 세션은 지속적으로 트래픽을 받습니다.** 그래도 본 행사 전에는 반드시 한 번 전체 리허설을 해주세요.

## PPT 링크
최종 Render 주소가 나오면 PPT의 LIVE 버튼 링크를 아래처럼 바꿉니다.

`https://YOUR-SERVICE.onrender.com/display`
