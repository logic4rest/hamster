"""
JayM - 장난감 숲 (Forest of Toys) 연주 및 LED 포레스트 애니메이션 스크립트
========================================================================
실행 방법:
    python tools/play_toy_forest.py
    또는
    uv run python tools/play_toy_forest.py
"""

import sys
import io
import random
from roboid import Hamster, wait

# Windows 콘솔에서 유니코드(이모지) 출력 시 CP949 인코딩 오류가 발생하는 것을 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def play_toy_forest():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)  # 연결 대기
        print("연결 성공!")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("BLE 동글과 햄스터 전원을 확인하세요.")
        return

    print("\n" + "=" * 60)
    print("   🌲 JayM - 장난감 숲 (Forest of Toys) 연주 시작 🌲")
    print("=" * 60)
    
    # 경쾌하고 빠른 템포 설정 (BPM: 155)
    hamster.tempo(155)

    # 멜로디 정의 (음정, 박자)
    # D Major 선율 기반의 통통 튀는 8분음표/4분음표 구성
    melody = [
        # [A 파트 - 1]
        ("D5", 0.25), ("E5", 0.25), ("F#5", 0.25), ("G5", 0.25), ("A5", 0.5), ("B5", 0.25), ("A5", 0.25), ("G5", 0.5), ("F#5", 0.5),
        ("G5", 0.25), ("A5", 0.25), ("B5", 0.25), ("C#6", 0.25), ("D6", 0.5), ("C#6", 0.25), ("B5", 0.25), ("A5", 0.5), ("G5", 0.5),
        ("F#5", 0.25), ("G5", 0.25), ("A5", 0.25), ("B5", 0.25), ("C#6", 0.5), ("B5", 0.25), ("A5", 0.25), ("G5", 0.5), ("F#5", 0.5),
        ("E5", 0.25), ("F#5", 0.25), ("G5", 0.25), ("A5", 0.25), ("B5", 0.5), ("A5", 0.25), ("G5", 0.25), ("F#5", 0.5), ("E5", 0.5),

        # [A 파트 - 2]
        ("D5", 0.25), ("E5", 0.25), ("F#5", 0.25), ("G5", 0.25), ("A5", 0.5), ("B5", 0.25), ("A5", 0.25), ("G5", 0.5), ("F#5", 0.5),
        ("G5", 0.25), ("A5", 0.25), ("B5", 0.25), ("C#6", 0.25), ("D6", 0.5), ("C#6", 0.25), ("B5", 0.25), ("A5", 0.5), ("G5", 0.5),
        ("A5", 0.25), ("B5", 0.25), ("C#6", 0.25), ("D6", 0.25), ("E6", 0.5), ("D6", 0.25), ("C#6", 0.25), ("B5", 0.5), ("A5", 0.5),
        ("D6", 1.0), ("off", 0.5)
    ]

    forest_emojis = ["🌲", "🌳", "🌱", "🌿", "🍀", "✨", "🐿️"]
    
    tick = True
    for note_name, beats in melody:
        if note_name == "off":
            hamster.leds("off", "off")
            continue
            
        # 초록색(숲)과 노란색(장난감 전구) 번갈아 점등
        if tick:
            hamster.leds("green", "off")  # 왼쪽 초록
            emoji = random.choice(forest_emojis)
            sys.stdout.write(f"\r{emoji}  장난감 숲 연주 중...  |  음정: {note_name:3s}")
        else:
            hamster.leds("off", "yellow") # 오른쪽 노랑
            emoji = random.choice(forest_emojis)
            sys.stdout.write(f"\r{emoji}  장난감 숲 연주 중...  |  음정: {note_name:3s}")
            
        sys.stdout.flush()
        tick = not tick

        # 음정 재생
        hamster.note(note_name, beats)

    # 연주 종료
    hamster.note("off")
    hamster.leds("green", "green")
    print("\n\n🎉 연주가 완료되었습니다!")
    wait(1000)
    hamster.leds("off", "off")

if __name__ == "__main__":
    play_toy_forest()
