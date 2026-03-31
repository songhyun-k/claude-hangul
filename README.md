# claude-hangul

**iOS SSH에서 Claude Code 한글 입력 깨짐을 고치는 PTY 프록시**

iOS 터미널 앱(Termius, Moshi 등)에서 Claude Code를 쓸 때, 한글 자모가 합쳐지는 순간 글자가 통째로 사라집니다. Anthropic은 [이 이슈](https://github.com/anthropics/claude-code/issues/15705)를 **not planned**으로 닫았습니다.

`claude-hangul`은 Claude Code를 PTY 프록시로 감싸서, iOS IME의 `DEL + 재삽입` 시퀀스를 시간차 분리하여 문제를 우회합니다.

## 설치

```bash
git clone https://github.com/songhyun-k/claude-hangul.git
cd claude-hangul
bash install.sh
```

<details>
<summary>한 줄 설치</summary>

```bash
curl -fsSL https://raw.githubusercontent.com/songhyun-k/claude-hangul/main/claude-hangul \
  -o ~/.local/bin/claude-hangul && chmod +x ~/.local/bin/claude-hangul
```

</details>

설치 후 `claude` 대신 `claude-hangul`을 실행하면 됩니다. alias 설정 시 기존처럼 `claude`만 입력해도 동작합니다.

```bash
claude-hangul                    # 기본 실행
claude-hangul --model sonnet     # 모든 claude 인자 그대로 전달
```

## 요구사항

- Python 3.8+ (macOS/Linux 기본 포함)
- Claude Code (`claude`가 PATH에 있어야 함)
- 외부 패키지 의존성 없음

## 삭제

```bash
bash install.sh uninstall
```

## 동작 원리

iOS 터미널 앱은 한글 조합 시 `DEL(0x7f) + 합성문자`를 하나의 청크로 전송합니다. Claude Code의 DEL 필터가 이 청크를 통째로 가로채면서 합성문자가 버려집니다.

```
기존:  "\x7f가" → DEL 필터가 전체를 가로챔 → "가" 소실

수정:  "\x7f가" → PTY 프록시가 분리
         ├─ write("\x7f")  → backspace 정상 처리
         ├─ 5ms 대기
         └─ write("가")    → 텍스트 정상 삽입
```

한글뿐 아니라 일본어, 중국어 등 모든 비ASCII IME 조합에 대응합니다. 일반 입력에는 지연이 없습니다.

## 테스트

```bash
python3 test_split.py
```

## 제한사항

- macOS / Linux 전용 (Windows는 pty 모듈 미지원)
- TTY가 아닌 환경에서는 프록시 없이 `claude`를 직접 실행

## 라이선스

[MIT](LICENSE)
