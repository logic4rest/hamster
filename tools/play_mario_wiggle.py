"""
슈퍼 마리오 테마곡 연주 + 제자리 엉덩이 흔들기 싱크로율 100% 스크립트
====================================================================
실행 방법:
    python tools/play_mario_wiggle.py
    또는
    uv run python tools/play_mario_wiggle.py
"""

import sys
import io
import random
from roboid import Hamster, wait

# Windows 콘솔 유니코드 출력 에러 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def play_mario_wiggle():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)
        print("연결 성공! 🎮🍑")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("\n[!] BLE 동글이 PC에 연결되어 있고, 햄스터 로봇 전원이 켜져 있는지 확인하세요.")
        return

    print("\n" + "=" * 60)
    print("   🍄 슈퍼 마리오 테마곡 + 제자리 엉덩이 흔들기 댄스 쇼! 🍄")
    print("=" * 60)

    # 템포 설정 (BPM: 150)
    hamster.tempo(150)
    bpm = 150

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
        ("off", 0.25), ("C6", 0.25), ("off", 0.25), ("C6", 0.25), ("C6", 0.5), ("off", 0.5)
    ]

    mario_emojis = ["🍄", "🪙", "⭐", "🔥", "🧱"]
    led_colors = ["red", "blue", "green", "yellow", "cyan", "magenta", "white"]
    
    # 엉덩이 흔들기 방향을 교차하기 위한 토글 변수
    wiggle_left = True

    for note_name, beats in melody:
        timeout = beats * 60.0 * 1000.0 / bpm
        tail = 100.0 if timeout > 100 else 0.0
        play_time = timeout - tail

        if note_name == "off":
            # 쉼표 구간: 소리와 바퀴 모두 정지
            hamster.note("off")
            hamster.stop()
            hamster.leds("off", "off")
            sys.stdout.write("\r💤 [쉬는 구간] 똑딱똑딱   ")
            sys.stdout.flush()
        else:
            # 1. 음 재생 시작 (비동기로 버저 활성화)
            hamster.note(note_name)
            
            # 2. 바퀴 제어를 통한 제자리 엉덩이 흔들기
            if wiggle_left:
                hamster.wheels(-85, 85)  # 제자리 좌회전 방향
                sys.stdout.write(f"\r🍑 {random.choice(mario_emojis)} [엉덩이 좌] 음정: {note_name:3s}")
            else:
                hamster.wheels(85, -85)  # 제자리 우회전 방향
                sys.stdout.write(f"\r🍑 {random.choice(mario_emojis)} [엉덩이 우] 음정: {note_name:3s}")
            sys.stdout.flush()
            
            # 3. 화려하게 LED 반짝임
            hamster.leds(random.choice(led_colors), random.choice(led_colors))
            
            # 방향 교차
            wiggle_left = not wiggle_left

        # 메인 음 지속시간만큼 대기
        wait(play_time)

        # 4. 음 구분을 위해 음정 끄기 및 바퀴 멈춤 (스타카토 효과 극대화)
        hamster.note("off")
        hamster.stop()
        if tail > 0:
            wait(tail)

    # 연주 완료 및 정지
    hamster.note("off")
    hamster.stop()
    hamster.leds("green", "green")
    print("\n\n🎉 노래 연주와 엉덩이 댄스가 완료되었습니다! 👏👏👏")
    wait(1000)
    hamster.leds("off", "off")

if __name__ == "__main__":
    play_mario_wiggle()
