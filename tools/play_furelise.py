"""
햄스터 로봇으로 '엘리제를 위하여' 연주하기 스크립트
==================================================
실행 방법:
    python tools/play_furelise.py
    또는
    uv run python tools/play_furelise.py
"""

from roboid import Hamster, wait

def play_fur_elise():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)  # 연결 안정화를 위해 잠시 대기
        print("연결 성공!")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("BLE 동글과 햄스터 전원을 확인하세요.")
        return

    print("음악 재생 시작: '엘리제를 위하여' (Für Elise)...")
    
    # 템포(속도) 설정 - 130 BPM
    hamster.tempo(130)

    # 멜로디 데이터 정의: (음정 이름, 박자)
    # 0.5 박자: 8분 음정 (엘리제를 위하여의 빠른 진행 부분)
    # 1.5 박자: 점4분 음정 (길게 끄는 부분)
    melody = [
        # 도입부
        ("E5", 0.5), ("D#5", 0.5),
        ("E5", 0.5), ("D#5", 0.5), ("E5", 0.5), ("B4", 0.5), ("D5", 0.5), ("C5", 0.5),
        ("A4", 1.5), 
        ("C4", 0.5), ("E4", 0.5), ("A4", 0.5),
        ("B4", 1.5),
        ("E4", 0.5), ("G#4", 0.5), ("B4", 0.5),
        ("C5", 1.5),
        
        # 반복 및 변형 파트
        ("E4", 0.5), ("E5", 0.5), ("D#5", 0.5),
        ("E5", 0.5), ("D#5", 0.5), ("E5", 0.5), ("B4", 0.5), ("D5", 0.5), ("C5", 0.5),
        ("A4", 1.5),
        ("C4", 0.5), ("E4", 0.5), ("A4", 0.5),
        ("B4", 1.5),
        ("E4", 0.5), ("C5", 0.5), ("B4", 0.5),
        ("A4", 1.5)
    ]

    for note_name, beats in melody:
        print(f"연주 음정: {note_name:3s} ({beats} 박자)")
        hamster.note(note_name, beats)
    
    # 연주 종료 후 소리 끄기
    hamster.note("off")
    print("연주가 완료되었습니다!")

if __name__ == "__main__":
    play_fur_elise()
