# 숭실 Seat · RFID 좌석 안내

로블록스 `Soongsil_Central_Library.rbxlx` 최신 v2에서 추출한 좌석배치도입니다. 공식 숭실대 도서관 서비스가 아닙니다.

## 들어 있는 것

- `dist/`: GitHub Pages에 올릴 웹페이지. 사각형 좌석, 상태 색상, 층 선택, 검색, 상세 정보, 시연 카드 A/B.
- `dist/seats.json`: 원본 모델명·좌석 ID·X/Z 좌표. B1 30석, 1F 학습 6석 + 로비 시연 1석, 2F 30석, 3F~6F 각 4석. 학습 82석 + 시연 1석.
- `firmware/seat_reader/seat_reader.ino`: UNO Q MCU에서 RC522 읽기, 카드 제거 감지, Bridge 전달.
- `backend/`: UNO Q Linux에서 실행할 Bridge 수신·SQLite 저장·HTTP API·웹서버.
- `tests/`: 중복/동시 요청, 한 카드 한 좌석, 재시작 저장, 미연결 상태, API 인증 검증.
- `.github/workflows/pages.yml`: GitHub Pages 배포.

현재 배포된 웹페이지는 시연 모드로 시작합니다. 실제 장비가 연결된 상태라고 주장하지 않습니다. 물리적인 RC522/UNO Q와 현재 작업 환경은 연결되지 않았으므로 펌웨어의 보드 컴파일·업로드·실물 인식 시험은 사용자 장비에서 해야 합니다. 웹과 Python 상태 처리는 별도로 검증했습니다.

## 전체 흐름

RC522 → UNO Q의 MCU(스케치) → Arduino Router Bridge → UNO Q의 Linux(Python+SQLite) → 좌석 웹페이지(2초 갱신)

UNO Q는 Linux도 실행하므로 첫 시제품에서는 별도 클라우드 DB 없이 보드 자체가 좌석 서버가 됩니다. 전원과 Wi-Fi가 유지되고 Python 프로그램이 실행 중이면 노트북을 분리해도 동작합니다. 실제 좌석별 상태를 읽으려면 해당 좌석별로 리더와 배선/제어 장치가 필요합니다. 이 패키지는 리더 1개를 `B1_001`에 연결하는 첫 실제 구성이며, 나머지 82개를 실제 연결된 좌석처럼 표시하지 않습니다.

## 1. RC522 배선 (전원을 끄고 연결)

| RC522 | Arduino UNO Q |
|---|---|
| 3.3V | 3.3V |
| GND | GND |
| SDA / SS | D10 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |
| RST | D9 |
| IRQ | 연결하지 않음 |

RC522의 SDA 표시는 SPI에서 SS 역할입니다. I²C SDA에 연결하지 마세요. RC522에는 5V를 넣지 않습니다. UNO Q의 MCU GPIO는 3.3V입니다. 다른 UNO 모델용 전압 가정을 적용하지 마세요. 짧은 점퍼선을 사용하고 핀 헤더가 제대로 납땜되어 있는지 확인합니다.

## 2. UNO Q MCU에 스케치 올리기

1. Arduino App Lab/IDE에서 UNO Q 보드 지원을 설치하고 실제 보드를 선택합니다.
2. `Arduino_RouterBridge`와 `MFRC522`(miguelbalboa/GithubCommunity) 라이브러리를 설치합니다.
3. `firmware/seat_reader/seat_reader.ino`를 열고 UNO Q의 MCU에 업로드합니다.
4. `READER_ID`의 기본값은 `reader-01`입니다. Python 설정의 키와 일치해야 합니다.
5. `Monitor`에 `Reader ready`가 나오는지 확인합니다. `RC522 not detected`는 전원/배선 문제입니다.

이 코드는 Arduino UNO R3용 Serial 코드가 아니라 UNO Q용 Router Bridge 코드입니다. 사용 중인 보드 코어/라이브러리에서 컴파일이 실패하면 오류 내용을 확인해야 합니다. 현재 실물/컴파일 도구가 없어 해당 단계는 미검증입니다.

## 3. UNO Q Linux에서 서버 실행

압축을 UNO Q의 Linux 사용자 홈 폴더에 풀고, 그 폴더에서 실행합니다. 노트북의 Windows 터미널이 아니라 UNO Q Linux 터미널에서 실행합니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/server.py --init
.venv/bin/python backend/server.py
```

`--init`는 처음 한 번만 실행합니다. `config.local.json`에 비밀키와 기본 리더 매핑을 생성하며 기존 파일을 덮어쓰지 않습니다. `arduino-router` 서비스가 작동해야 합니다. Bridge를 사용할 수 없으면 실제 모드는 시작하지 않고 오류를 냅니다.

같은 Wi-Fi의 노트북/휴대폰에서 `http://UNO_Q의_IP:8080`에 접속합니다. 예: 보드 IP가 192.168.0.25라면 `http://192.168.0.25:8080`입니다. 실제 IP는 UNO Q에서 `hostname -I`로 확인하세요.

화면 오른쪽 상단 **연결 설정 → 실제 RFID 서버 → 서버 주소를 비워두고 적용**합니다. 이제 `B1_001`은 리더의 heartbeat가 오면 이용 가능으로 바뀝니다. 카드를 대면 사용 중, 카드를 충분히 떼었다가 2초 이상 후 다시 대면 이용 가능으로 바뀝니다. 다른 좌석은 해당 리더가 없으므로 회색 미연결입니다.

프로그램 실행을 종료하면 갱신도 멈춥니다. 보드 전원을 껐다 켜도 SQLite 이용 기록은 남지만 Python 서버를 다시 실행해야 합니다. 자동 실행을 원하면 `backend/soongsil-seat.service.example`을 본인 경로로 수정해 systemd에 설치하세요.

## 4. GitHub로 웹페이지 관리

1. 새 GitHub 저장소를 생성합니다. 압축 해제한 소스 전체를 업로드하세요(프로젝트별 `.openai` 파일은 패키지에서 제외되어 있습니다).
2. 저장소 Settings → Pages → Build and deployment에서 **GitHub Actions**를 선택합니다.
3. `main`에 push하면 포함된 workflow가 `dist/`를 배포합니다.
4. GitHub Pages 페이지의 기본 모드는 시연입니다. 실제 상태를 받으려면 다음 HTTPS 연결을 설정합니다.

**GitHub Pages는 Python 서버를 실행하지 않습니다.** Python 서버는 UNO Q 또는 별도 서버에서 계속 실행해야 합니다. GitHub Pages의 HTTPS 페이지는 보드의 HTTP 주소를 직접 읽을 수 없습니다. `localhost` 역시 방문자 자신의 기기를 뜻하므로 보드 주소 대신 사용할 수 없습니다.

UNO Q 서버를 본인 도메인의 HTTPS 리버스 프록시/신뢰할 수 있는 터널 뒤에 배치한 후:

- `config.local.json`의 `allowed_origins`에 GitHub Pages 원본(origin), 예를 들어 `https://YOURNAME.github.io`를 추가합니다. 저장소 경로는 포함하지 않습니다.
- Python 서버를 재시작합니다.
- 웹의 연결 설정에서 서버의 **HTTPS 원본 주소**를 입력합니다.
- 모든 방문자의 기본 연결을 설정하려면 `dist/config.js`의 `apiBase`에 그 HTTPS 주소를 넣고 push합니다.

공개 HTTPS 주소나 GitHub 저장소는 이 패키지가 자동으로 생성하지 않습니다. 실제 GitHub 계정/저장소와 보드 접근이 제공되지 않은 상태이므로 여기까지는 배포 준비된 소스입니다. 우선 3번의 같은 Wi-Fi 방식으로 실물을 검증한 뒤 연결하세요.

## 규칙과 연결 상태

- 빈 좌석 + 카드: 사용 시작.
- 같은 카드가 같은 좌석에 다시 인식: 사용 종료.
- 다른 카드가 사용 중인 좌석: 거절.
- 한 카드가 다른 좌석을 이미 사용 중: 거절.
- 카드가 계속 놓여 있으면 반복 처리하지 않음. MCU는 1초간 제거 감지 후 재활성화, 서버는 같은 카드·리더 2초 이내 이벤트도 방지.
- 응답 손실 시 MCU는 동일 event_id로 재전송. SQLite 이벤트 ID 중복 제거로 다시 뒤집히지 않음.
- 서버 재시작 후 상태는 유지. 리더의 5초 heartbeat가 15초 넘게 끊기면 해당 좌석을 미연결로 표시.
- 웹 서버 연결 실패 시 모든 좌석의 현재 상태를 알 수 없으므로 미연결 표시. 마지막 사용 중 기록은 상세에 구분해 안내.
- 시연 모드는 브라우저 로컬 저장소에만 저장하고 실제 DB에 전송하지 않음.
- 원본 맵 좌석 좌표의 상대 위치를 유지한 2D 안내도입니다. 휴게 공간/통로 표시는 단순화된 안내 요소이며 벽체·출입문을 정밀 측량한 건축 평면도가 아닙니다.

## 다른 리더와 중앙 서버 확장

`config.local.json`의 readers에 고유 reader ID, 실제 `seat_id`, 서로 다른 무작위 token을 추가하세요. 같은 좌석에 리더를 중복 매핑할 수 없습니다. 현재 스케치는 UNO Q에 직접 연결된 RC522 1개를 지원합니다. 83개 리더를 현재 한 보드의 같은 SS 핀에 연결하면 안 됩니다. 여러 리더 직접 배선은 SS 핀/전원/거리 설계와 스케치 확장이 필요합니다.

다른 제어 장치는 아래 API로 중앙 서버에 이벤트를 전송할 수 있습니다. 서버가 reader→seat 매핑을 적용하므로 클라이언트가 임의 좌석을 바꿀 수 없습니다.

- `GET /api/seats`: 공개 상태. UID, 카드 해시, 장치 키 없음.
- `GET /api/health`: HTTP 프로세스 상태. `bridge_enabled`는 Bridge 사용 여부이며 카드 인식 성공을 뜻하지 않음.
- `POST /api/tap`: `Authorization: Bearer <해당 리더 토큰>`, `X-Reader-Id: reader-01`, JSON `{"uid":"AABBCCDD","event_id":"고유한-이벤트-ID"}`.
- `POST /api/heartbeat`: 같은 헤더, JSON `{}`. 5초마다 전송.

인증 토큰은 브라우저 JS, GitHub 저장소, 스크린샷에 올리지 마세요. UID는 메모리에서 HMAC 처리 후 카드 해시만 DB에 저장합니다. 공개 API는 좌석 상태와 시간만 제공합니다. UID만으로 출입 보안이나 결제 인증을 구현한 것은 아닙니다. 기록량은 소규모 시제품에 맞춰져 있으며 장기 운영 시 이벤트 보존 기간·관리자 강제 퇴실·백업·접근 정책을 추가해야 합니다. 전원 차단 시 아직 MCU 메모리에만 있던 미전달 이벤트는 손실될 수 있습니다.

## 검증

```sh
python3 -m unittest discover -s tests -v
node --check dist/app.js
```

실물 합격 확인: 카드 A 입실 → 웹 갱신 / 계속 대고 있어도 유지 / 제거 후 재태그 퇴실 / 카드 B 퇴실 거절 / 서버 재시작 후 기록 유지 / 리더 분리 후 미연결. 이 마지막 실물 확인은 아직 수행하지 않았습니다.

## 참고한 공식 자료

- UNO Q 핀/통신: https://docs.arduino.cc/tutorials/uno-q/user-manual/
- UNO Q 전압: https://docs.arduino.cc/tutorials/uno-q/power-specification/
- C++ Bridge API: https://github.com/arduino-libraries/Arduino_RouterBridge
- Python Bridge: https://github.com/arduino/arduino-router-bridge-py
- MFRC522 라이브러리: https://github.com/miguelbalboa/rfid
