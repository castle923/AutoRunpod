# 모니터링 체계

갱신: 2026-09-15

## 1. 리스너 서버 (on-pod, 상시 가동)

2026-09-15부터 포드 내부에 Flask 기반 리스너 서버가 상주하며, 기존 watchdog.sh의 역할을
대체·확장한다. 기존 watchdog은 단순 프로세스 존재 여부만 체크했지만, 리스너 서버는
Forge API 응답성까지 확인하고 상태를 JSON으로 기록한다.

### 동작 방식
- **프로세스 감시** (2초 간격): psutil로 `launch.py` 프로세스 존재 확인. 죽으면
  `restart_forge_clean.sh`로 자동 재시작. 재시작 후 최대 120초간 Forge API 응답 대기.
- **재시작 폭풍 방지**: 5분 내 3회 이상 재시작 시 자동 재시작 중단, `restart_storm_stopped: true` 기록.
- **배치 진행 추적** (5초 간격): Forge `/sdapi/v1/progress` 폴링. job/progress 정보를
  `state.json`에 기록. 배치 100% 완료 감지 시 `batch_completed: true` 기록.
- **HTTP API** (포트 5000): `/health`, `/status`, `/restart`, `/upload` 엔드포인트 제공.

### 배포 위치
```
/workspace/listener/
├── server.py    # 메인 서버
├── start.sh     # tmux 실행 스크립트
├── state.json   # 상태 파일 (자동 생성)
└── listener.log # 로그
```

### restart_forge_clean.sh
`env -i`로 환경변수를 완전 격리하여 Forge를 재시작한다. Jupyter의 `MPLBACKEND=module://matplotlib_inline.backend_inline`
환경변수가 Forge에 유입되어 크래시를 일으키는 문제를 원천 차단하는 핵심 스크립트.

## 2. Cron Jobs (on-pod, 상시 가동)

| 주기 | 스크립트 | 용도 |
|------|----------|------|
| 5분 | `auto_clean_kernels.py` | Jupyter idle 커널 정리 (idle 20분+ 커널 DELETE) |
| 10분 | `preventive_restart.py` | 5시간마다 예방적 Forge 재시작 (배치 idle일 때만) |
| 30분 | `auto_backup_workspace.sh` | 워크스페이스 스냅샷 → gdrive 백업 |
| @reboot | `auto_restore_on_boot.sh` | LoRA/체크포인트/dynamic_prompts 자동 복원 |

## 3. Claude Routine (외부, 참고용)

아래 Routine들은 포드 안이 아니라 사용자의 Claude 계정에 등록된 예약 트리거다.
GitHub 저장소를 복사하거나 이 문서를 읽는다고 해서 감시 기능이 되살아나지 않으며,
동일한 방식으로 다시 동작하게 하려면 Claude 세션에서 Routine을 새로 만들어야 한다.

### HFdyd 포드 정밀검사 (매시간)
- GPU 온도/사용률/메모리, 디스크 여유공간, RAM(cgroup 기준 ~58GiB), Jupyter 커널 수,
  rclone 인증, LoRA 무결성 등을 점검
- 배치 실행 중이면 스킵, 배치 완료 직후면 완료 처리(zip/업로드/검증) 후 점검

### RunPod 잔여 시간 24시간 경고 (매시간)
- RunPod 계정 잔액/시간당 소비율로 잔여 사용 가능 시간 계산
- 24시간 이하 진입 시 푸시 알림, 12시간 이하면 매 사이클 알림

### 참고: cgroup RAM 상한
`free -h`는 호스트 전체 메모리(251GiB)를 표시하지만, 실제 컨테이너 상한은
`cat /sys/fs/cgroup/memory.max` 기준 **~57.7GiB**(61999996928 bytes)이다.
RAM 판단 시 반드시 cgroup 한도 대비로 판단할 것.
