"""
슈퍼 마리오 테마곡 연주 + 엉덩이 흔들기 + 실물 집게 개폐 싱크로율 100% 스크립트
==========================================================================
실행 방법:
    python tools/play_mario_gripper.py
    또는
    uv run python tools/play_mario_gripper.py
"""

import sys
import io
import random
from roboid import Hamster, wait

# Windows 콘솔 유니코드 출력 에러 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def play_mario_gripper():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)
        print("연결 성공! 🎮🍑🦾")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("\n[!] BLE 동글이 PC에 연결되어 있고, 햄스터 로봇 전원이 켜져 있는지 확인하세요.")
        return

    print("\n" + "=" * 70)
    print("   🍄 슈퍼 마리오 연주 + 엉덩이 흔들기 + 집게 박수 3합동 댄스 쇼! 🍄")
    print("=" * 70)

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
    
    # 엉덩이 흔들기 및 집게 개폐 상태 관리 토글 변수
    wiggle_left = True
    gripper_open = True
    accumulated_beats = 0.0
    last_toggle_beat = 0.0

    for note_name, beats in melody:
        timeout = beats * 60.0 * 1000.0 / bpm
        tail = 100.0 if timeout > 100 else 0.0
        play_time = timeout - tail

        # 1.0 박자마다 집게 상태 변경 확인
        accumulated_beats += beats
        if accumulated_beats - last_toggle_beat >= 1.0:
            gripper_open = not gripper_open
            last_toggle_beat = accumulated_beats

        if note_name == "off":
            # 쉼표 구간: 연주 끄기, 바퀴 멈춤
            hamster.note("off")
            hamster.stop()
            
            # 집게는 현재 상태 유지
            if gripper_open:
                hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.OUTPUT_A, 1)
                hamster.write(Hamster.OUTPUT_B, 0)
            else:
                hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.OUTPUT_A, 0)
                hamster.write(Hamster.OUTPUT_B, 1)
                
            hamster.leds("off", "off")
            sys.stdout.write("\r💤 [쉬는 구간] 똑딱똑딱                      ")
            sys.stdout.flush()
        else:
            # 1. 음 재생 시작 (비동기)
            hamster.note(note_name)
            
            # 2. 바퀴 흔들기 (여전히 음마다 활기차게 흔들기)
            if wiggle_left:
                hamster.wheels(-85, 85)
                wiggle_label = "좌"
            else:
                hamster.wheels(85, -85)
                wiggle_label = "우"
            wiggle_left = not wiggle_left
                
            # 3. 집게 개폐 제어 (누적 1.0 박자마다 교차 제어)
            if gripper_open:
                hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.OUTPUT_A, 1)
                hamster.write(Hamster.OUTPUT_B, 0)
                gripper_label = "열기 👐"
            else:
                hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
                hamster.write(Hamster.OUTPUT_A, 0)
                hamster.write(Hamster.OUTPUT_B, 1)
                gripper_label = "닫기 ✊"
                
            sys.stdout.write(f"\r🍑 {random.choice(mario_emojis)} [엉덩이 {wiggle_label} + 집게 {gripper_label}] 음정: {note_name:3s}")
            sys.stdout.flush()
            
            # 4. LED 반짝임
            hamster.leds(random.choice(led_colors), random.choice(led_colors))

        # 음 지속시간 대기
        wait(play_time)

        # 5. 스타카토 절도감을 위해 음정과 바퀴 일시 차단
        hamster.note("off")
        hamster.stop()
        if tail > 0:
            wait(tail)

    # 연주 및 쇼 종료
    hamster.note("off")
    hamster.stop()
    # 집게 릴리즈 (해제)
    hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.OUTPUT_A, 0)
    hamster.write(Hamster.OUTPUT_B, 0)
    hamster.leds("green", "green")
    
    print("\n\n🎉 3합동 연주와 댄스가 성공적으로 끝났습니다! 👏👏👏")
    wait(1000)
    hamster.leds("off", "off")

if __name__ == "__main__":
    play_mario_gripper()
