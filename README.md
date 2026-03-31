# claude-hangul

**iOS 모바일 SSH에서 Claude Code 한글 입력이 안 되는 문제를 해결하는 PTY 프록시**

Claude Code는 iOS 터미널 앱(Termius, Moshi 등)에서 한글을 입력하면 자음과 모음이 합쳐지는 순간 글자가 사라집니다. Anthropic은 이 이슈를 **not planned**로 분류했습니다. `claude-hangul`은 이 문제를 외부에서 우회하여 해결합니다.

> **관련 이슈**: [anthropics/claude-code#15705](https://github.com/anthropics/claude-code/issues/15705)

---

## 증상

| 동작 | 결과 |
|------|------|
| `ㄱ` 입력 | `ㄱ` 표시됨 |
| `ㅏ` 입력 (→ `가`로 조합) | **글자 사라짐** |

- Termius (iOS), Moshi, 기타 iOS SSH 앱에서 재현
- Android, macOS 네이티브 터미널에서는 정상
- Gemini CLI, Codex CLI 등 다른 CLI 도구는 정상

---

## 원인

iOS 터미널 앱은 한글 IME 조합을 **"삭제 + 재삽입"** 시퀀스로 서버에 전송합니다:

```
ㄱ 입력:  e3 84 b1              → "ㄱ" (U+3131)
ㅏ 입력:  7f ea b0 80           → DEL + "가" (U+AC00)
```

이 `DEL(0x7f)` + `가`가 하나의 stdin chunk로 Claude Code에 도착하면, [`useTextInput.ts:442-465`](https://github.com/anthropics/claude-code/issues/15705)의 DEL 필터가 backspace만 수행하고 **`return`으로 즉시 종료**하여 뒤따르는 합성 글자(`가`)를 버립니다:

```javascript
// hooks/useTextInput.ts — Issue #1853 fix (SSH/tmux DEL 이중 처리 방지)
if (!key.backspace && !key.delete && input.includes('\x7F')) {
    // backspace 처리...
    return  // ← 여기서 "가"가 사라짐
}
```

## 해결 방법

`claude-hangul`은 **PTY 프록시**로 Claude Code를 감싸서, `DEL + 비ASCII` 시퀀스를 시간차를 두고 분리 전달합니다:

```
기존:    stdin → Claude Code
         "\x7f가" 한 덩어리 → DEL 필터에서 "가" 소실

claude-hangul:
         stdin → PTY 프록시 → Claude Code
         "\x7f가" 수신
            ├─ write("\x7f")  → Claude가 backspace로 정상 처리
            ├─ 5ms 대기       → Bun 이벤트 루프가 첫 입력 소화
            └─ write("가")    → Claude가 텍스트로 정상 삽입
```

---

## 설치

### 방법 1: git clone

```bash
git clone https://github.com/songhyun-k/claude-hangul.git
cd claude-hangul
bash install.sh          # 설치 + alias 설정까지 대화형으로 진행
```

### 방법 2: 한 줄 설치

```bash
curl -fsSL https://raw.githubusercontent.com/songhyun-k/claude-hangul/main/claude-hangul \
  -o ~/.local/bin/claude-hangul && chmod +x ~/.local/bin/claude-hangul
```

### 삭제

```bash
bash install.sh uninstall   # 바이너리 + alias 모두 정리
```

또는 수동으로:

```bash
rm ~/.local/bin/claude-hangul
# ~/.zshrc 등에서 alias claude='claude-hangul' 줄 제거
```

### 상태 확인

```bash
bash install.sh status
```

### 요구사항

- Python 3.8+ (macOS/Linux 기본 포함)
- Claude Code 설치 완료 (`claude` 명령이 PATH에 있어야 함)
- 외부 패키지 의존성 **없음** (표준 라이브러리만 사용)

---

## 사용법

```bash
# claude 대신 claude-hangul 실행
claude-hangul

# 모든 claude 인자 그대로 전달
claude-hangul --model sonnet
claude-hangul -p "코드 리뷰해줘"
claude-hangul --resume
```

설치 시 alias를 설정했다면 기존처럼 `claude`만 입력해도 됩니다.

---

## 동작 상세

### 무엇을 하나

`DEL(0x7f)` 바로 뒤에 **비ASCII 바이트**(>= 0x80, UTF-8 멀티바이트 시작)가 올 때만 분리합니다.

| 입력 패턴 | 동작 | 이유 |
|-----------|------|------|
| `\x7f` + `가` (0xea…) | 분리 | iOS IME 조합 시퀀스 |
| `\x7f` + `あ` (0xe3…) | 분리 | 일본어 IME도 동일 |
| `\x7f` + `中` (0xe4…) | 분리 | 중국어 IME도 동일 |
| `\x7f` 단독 | 통과 | 일반 backspace |
| `\x7f` + ASCII | 통과 | Issue #1853 호환성 유지 |
| 일반 텍스트 | 통과 | 변환 불필요 |

### 무엇을 하지 않나

- 바이너리 패치 없음 (Claude Code 실행 파일을 수정하지 않음)
- 일반 입력에 지연 없음 (DEL + 비ASCII일 때만 5ms 지연)
- 네트워크 통신 없음
- 설정 파일 없음

---

## 기술 배경

### 왜 iOS에서만 발생하는가

| 플랫폼 | IME 동작 | Claude Code 수신 |
|--------|---------|-----------------|
| macOS / Android | **클라이언트에서 조합 완료** 후 최종 문자만 전송 | `가` |
| iOS (Termius, Moshi) | **삭제 + 재삽입** 시퀀스 전송 | `\x7f` + `가` |

### 왜 다른 CLI는 되는가

Codex CLI(Rust):
- `!ch.is_ascii()` 전용 경로로 비ASCII 입력을 별도 처리
- `delete_backward()`가 grapheme 단위로 독립 동작

Claude Code(TypeScript/Bun):
- DEL 필터(`useTextInput.ts:442`)가 `\x7f` 포함 입력 전체를 가로챔
- backspace 후 `return`으로 나머지 텍스트를 버림

### 왜 바이너리 패치가 안 되는가

Claude Code는 **Bun standalone 바이너리**(188MB Mach-O arm64)로 배포됩니다:

```
claude (Mach-O arm64)
├── Bun 런타임 + JavaScriptCore
├── __jsc_int, __jsc_opcodes (bytecode)
└── __bun 섹션 (124MB)
    ├── minified JS 소스
    └── JSC bytecode 캐시
```

- 올바른 수정에는 코드 **추가**가 필요 (backspace + 나머지 insert)
- 동일 길이 바이너리 패치로는 불가능
- 소스 수정 시 bytecode 캐시와 불일치 → crash 위험

---

## 테스트

```bash
python3 test_split.py
```

```
  PASS  test_chinese
  PASS  test_consecutive_dels_then_korean
  PASS  test_del_alone
  PASS  test_del_at_end
  PASS  test_del_plus_ascii
  PASS  test_del_plus_bare_continuation_byte
  PASS  test_del_plus_korean
  PASS  test_empty
  PASS  test_japanese
  PASS  test_multi_composition
  PASS  test_only_non_ascii
  PASS  test_prefix_text_then_del_korean
  PASS  test_pure_text
  PASS  test_rapid_triple_composition

14 passed, 0 failed
```

---

## 제한사항

- **macOS / Linux 전용** (Windows는 pty 모듈 미지원)
- TTY가 아닌 환경(파이프 등)에서는 프록시 없이 `claude`를 직접 실행합니다
- 5ms 딜레이가 극단적으로 느린 환경에서 부족할 수 있습니다 (`SPLIT_DELAY_S` 조정 가능)

---

## 라이선스

[MIT](LICENSE)
