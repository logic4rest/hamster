"""
웹캠 카메라 연결 상태 및 인덱스 정밀 진단 도구
====================================================================================================
- 사용 가능한 웹캠 인덱스(0~5) 및 백엔드(DirectShow, Media Foundation, Default)를 정밀 스캔
- C922 Pro 및 모든 USB 카메라의 작동 여부를 검증하고 최적 백엔드 설정 반환
"""

import sys
import cv2

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def test_cameras():
    print("=" * 65)
    print("  📹 웹캠 카메라 연결 상태 및 백엔드 정밀 진단 스캔")
    print("=" * 65)

    working_cameras = []

    backends = [
        ("Default (기본)", cv2.CAP_ANY),
        ("DirectShow (CAP_DSHOW)", cv2.CAP_DSHOW),
        ("Media Foundation (CAP_MSMF)", cv2.CAP_MSMF),
    ]

    for idx in range(6):
        for b_name, b_val in backends:
            try:
                cap = cv2.VideoCapture(idx, b_val)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w, _ = frame.shape
                        print(f"  ✅ [성공] 인덱스 {idx} | 백엔드: {b_name} | 해상도: {w}x{h}")
                        working_cameras.append((idx, b_val, b_name, w, h))
                        cap.release()
                        break
                cap.release()
            except Exception as e:
                pass

    print("\n" + "=" * 65)
    if working_cameras:
        print(f"  🎉 총 {len(working_cameras)}개의 정상 작동 웹캠을 찾았습니다:")
        for idx, b_val, b_name, w, h in working_cameras:
            print(f"     - 인덱스 [{idx}] ({b_name}, {w}x{h})")
    else:
        print("  ❌ 사용 가능한 웹캠을 찾지 못했습니다!")
        print("     1. C922 웹캠 USB 케이블을 다시 뽑았다가 연결해 보세요.")
        print("     2. 다른 앱(카메라 앱, Zoom, 줌, 팀즈, 디스코드)이 카메라를 사용 중인지 확인해 주세요.")
    print("=" * 65 + "\n")

    return working_cameras


if __name__ == "__main__":
    test_cameras()
