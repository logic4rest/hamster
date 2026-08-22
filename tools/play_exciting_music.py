"""
슈퍼 마리오 테마곡 (Super Mario Bros. Theme) 연주 및 아케이드 LED 애니메이션 스크립트
=============================================================================
실행 방법:
    python tools/play_exciting_music.py
    또는
    uv run python tools/play_exciting_music.py
"""

import sys
import io
import random
from roboid import Hamster, wait

# Windows 콘솔에서 유니코드(이모지) 출력 시 CP949 인코딩 오류가 발생하는 것을 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def play_mario():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)  # 연결 대기
        print("연결 성공! 🎮")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("\n[!] BLE 동글이 PC에 연결되어 있고, 햄스터 로봇 전원이 켜져 있는지 확인하세요.")
        return

    print("\n" + "=" * 60)
    print("   🍄 슈퍼 마리오 테마 (Super Mario Theme) 연주 시작 🍄")
    print("=" * 60)
    
    # 신나는 템포 설정 (BPM: 150)
    hamster.tempo(150)

    # 멜로디 정의 (음정, 박자)
    # 0.25 박자: 8분 음정
    # 0.5 박자: 4분 음정
    melody = [
        # 도입부 (Intro)
        ("E5", 0.25), ("E5", 0.25), ("off", 0.25), ("E5", 0.25), ("off", 0.25), ("C5", 0.25), ("E5", 0.25), ("off", 0.25),
        ("G5", 0.5), ("off", 0.5), ("G4", 0.5), ("off", 0.5),

        # 메인 테마 (Main Theme) - Part 1
        ("C5", 0.5), ("off", 0.25), ("G4", 0.5), ("off", 0.25), ("E4", 0.5), ("off", 0.25),
        ("A4", 0.25), ("B4", 0.25), ("A#4", 0.25), ("A4", 0.25),
        ("G4", 0.25), ("E5", 0.25), ("G5", 0.25), ("A5", 0.5), ("F5", 0.25), ("G5", 0.25),
        ("off", 0.25), ("E5", 0.5), ("C5", 0.25), ("D5", 0.25), ("B4", 0.5), ("off", 0.25),

        # 메인 테마 (Main Theme) - Part 2 (반복)
        ("C5", 0.5), ("off", 0.25), ("G4", 0.5), ("off", 0.25), ("E4", 0.5), ("off", 0.25),
        ("A4", 0.25), ("B4", 0.25), ("A#4", 0.25), ("A4", 0.25),
        ("G4", 0.25), ("E5", 0.25), ("G5", 0.25), ("A5", 0.5), ("F5", 0.25), ("G5", 0.25),
        ("off", 0.25), ("E5", 0.5), ("C5", 0.25), ("D5", 0.25), ("B4", 0.5), ("off", 0.25),

        # 브릿지 파트 (Bridge) - 1
        ("off", 0.5), ("G5", 0.25), ("F#5", 0.25), ("F5", 0.25), ("D#5", 0.5), ("E5", 0.25),
        ("off", 0.25), ("G4", 0.25), ("A4", 0.25), ("C5", 0.25), ("off", 0.25), ("A4", 0.25), ("C5", 0.25), ("D5", 0.25),
        ("off", 0.5), ("G5", 0.25), ("F#5", 0.25), ("F5", 0.25), ("D#5", 0.5), ("E5", 0.25),
        ("off", 0.25), ("C6", 0.25), ("off", 0.25), ("C6", 0.25), ("C6", 0.5), ("off", 0.5),

        # 브릿지 파트 (Bridge) - 2
        ("off", 0.5), ("G5", 0.25), ("F#5", 0.25), ("F5", 0.25), ("D#5", 0.5), ("E5", 0.25),
        ("off", 0.25), ("G4", 0.25), ("A4", 0.25), ("C5", 0.25), ("off", 0.25), ("A4", 0.25), ("C5", 0.25), ("D5", 0.25),
        ("off", 0.5), ("D#5", 0.5), ("off", 0.25), ("D5", 0.5), ("off", 0.25), ("C5", 0.5)
    ]

    mario_emojis = ["🍄", "🪙", "⭐", "🔥", "🧱", "🦖", "🌟"]
    led_colors = ["red", "blue", "green", "yellow", "cyan", "magenta", "white"]

    for note_name, beats in melody:
        if note_name == "off":
            hamster.leds("off", "off")
            wait(beats * 60 * 1000.0 / 150)
            continue
            
        # 화려한 아케이드 LED 효과
        c1 = random.choice(led_colors)
        c2 = random.choice(led_colors)
        hamster.leds(c1, c2)
        
        # 화면 애니메이션 출력
        emoji = random.choice(mario_emojis)
        sys.stdout.write(f"\r{emoji}  Super Mario Bros!  |  음정: {note_name:3s}")
        sys.stdout.flush()

        # 음 연주
        hamster.note(note_name, beats)

    # 연주 종료
    hamster.note("off")
    hamster.leds("green", "green")
    print("\n\n🎉 연주 완료! 클리어! 🌟")
    wait(1000)
    hamster.leds("off", "off")

if __name__ == "__main__":
    play_mario()
