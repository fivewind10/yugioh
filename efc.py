import random
import os

# ==========================================
# 콘솔 UI 및 화면 제어 함수
# ==========================================
def wait():
    """사용자가 내용을 확인하고 진행할 수 있도록 엔터 대기"""
    input("▶ 엔터")

def clear_screen():
    """콘솔 화면을 깔끔하게 지워주는 함수 (OS 대응)"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_step(text):
    """특정 연출이나 효과 단계의 텍스트를 보여주고 대기"""
    clear_screen()
    print(text)
    wait()

# ==========================================
# 카드 데이터베이스 및 텍스트 매핑
# ==========================================
# 카드 ID (인덱스)에 대응하는 카드 이름 리스트
names = [
    "", "꼬마모스", "진화의 고치", "식인 곤충", "궁극완전체 모스", "그레이트 모스",
    "어스퀘이크", "바늘 벌레", "바퀴볼", "중력반전", "대수해", "무시가호",
    "원위치", "아머드플라이", "라바모스"
]

# 카드 레벨 (마법/함정은 표시형식 '-'로 처리)
levels = [0, 1, 4, 2, 8, 6, "-", 2, 4, "-", "-", "-", "-", 4, 2]

# 카드 종족/분류 (몬스터의 경우 종족, 그 외는 마법/함정 표시)
tribes = [
    "", "곤충족", "곤충족", "곤충족", "곤충족", "곤충족", "마법", 
    "곤충족", "곤충족", "함정", "마법", "마법", "마법", "곤충족", "곤충족"
]

# 카드 종류 (일=일반 몬스터, 효=효과 몬스터, 마=마법, 함=함정)
types = ["", "일", "효", "효", "효", "효", "마", "효", "일", "함", "마", "마", "마", "효", "효"]

# 카드 효과 텍스트 토큰 사전
token_dict = {
    "0a": "이 카드명의 카드는 ", "0m": "1턴에 1번 ",
    "0e": "자신 필드의 '꼬마모스'에게 장착한다. ", "0f": "정해진 턴 후 특수 소환. ",
    "0b": "리버스: 몬스터 1장 파괴. ", "0g": "덱 위 5장 묘지. ",
    "0h": "모든 표시 형식 변경. ", "0i": "상대 몬스터 전부 파괴. ",
    "0n": "작은 나방 유충. ", "0p": "평범한 바퀴벌레. ",
    "0s": "곤충족 1장 묘지 보내고 발동. "
}

# 각 카드 번호에 할당된 효과 토큰 매핑
effects = [
    "", "0n", "0e", "0b", "0f", "0f", "0h", "0g", "0p", "0h",
    "0a0m", "0i", "0a", "0s", "0f"
]

# 룰 특수 소환 몬스터(모스족)가 장착 상태로 버텨야 하는 요구 턴 수
moth_require_turn = {
    4: 6,   # 궁극완전체 모스 (6턴 이상)
    5: 4,   # 그레이트 모스 (4턴 이상)
    14: 2   # 라바모스 (2턴 이상)
}
rule_special_monsters = list(moth_require_turn.keys())

# ==========================================
# 게임 환경 및 세션 변수 설정
# ==========================================
deck = [] # 덱 영역 리스트
# 1번부터 13번 카드까지 각각 3장씩 덱에 추가 (고유 번호 형식: 카드ID * 100 + 장수)
for m_id in range(1, 14):
    for sub in range(1, 4):
        deck.append(m_id * 100 + sub)
deck.append(1401) # 라바모스 1장 추가

random.shuffle(deck) # 게임 시작 전 덱 셔플
hand = []            # 패 리스트
grave = []           # 묘지 리스트
exclude = []         # 제외 존 리스트

# 필드 상태 초기화 (몬스터 존 5칸, 마함 존 5칸)
monster_field = [{"card": None, "pos": None, "set_turn": None, "counter": 0} for _ in range(5)]
st_field = [{"card": None, "pos": None, "set_turn": None, "counter": 0, "parent_zone": None} for _ in range(5)]

turn = 1                     # 현재 턴 수
normal_summon_used = False   # 이번 턴 일반 소환권 사용 여부 플래그
is_opponent_turn = False     # 현재 상대 턴 진행 여부 플래그

def start_turn():
    """자신 턴의 스타트 시 실행되는 상태 갱신 함수"""
    global normal_summon_used
    normal_summon_used = False # 소환권 초기화
    
    # 내 필드의 장착 카드(진화의 고치 등) 턴 수 진행
    for zone in st_field:
        if zone["card"] and (zone["card"] // 100 == 2) and zone["parent_zone"] is not None:
            zone["counter"] += 1
            
    clear_screen()
    print(f"\n==============================")
    print(f"    자신 턴 (TURN {turn}) 시작")
    print(f"==============================")
    wait()

# ==========================================
# 유틸리티 및 보드 판독 함수
# ==========================================
def valid_hand(idx): 
    """지정한 인덱스가 현재 패 범위 내에 있는지 안전 검사"""
    return 0 <= idx < len(hand)

def valid_field(idx): 
    """지정한 필드 번호(0~4)가 유효한 범위인지 검사"""
    return 0 <= idx < 5

def parse_effect(code):
    """토큰화된 카드 효과 코드를 읽을 수 있는 텍스트로 치환"""
    result = ""
    for i in range(0, len(code), 2):
        result += token_dict.get(code[i:i+2], "")
    return result if result else "효과 없음"

def level_str(m_id):
    """몬스터의 레벨을 텍스트로 변환 (마함은 '-' 반환)"""
    return f"{levels[m_id]}렙" if isinstance(levels[m_id], int) else "-"

def draw_phase():
    """드로우 페이즈: 덱 맨 위에서 카드를 가져와 패에 추가"""
    clear_screen()
    print("=== 드로우 페이즈 ===")
    if deck:
        card = deck.pop(0)
        hand.append(card)
        m_id = card // 100
        print(f">> 드로우한 카드: 【{names[m_id]}】")
    else:
        print(">> [경고] 덱에 카드가 없어 드로우할 수 없습니다.")
    wait()

def show_hand():
    """현재 패 상황과 덱/묘지/제외 수량 정보 출력"""
    print(f"\n[패] (덱:{len(deck)} / 묘지:{len(grave)} / 제외:{len(exclude)})")
    for i, uid in enumerate(hand):
        m_id = uid // 100
        sub = uid % 100
        print(f"{i+1}. {names[m_id]}{sub} ({level_str(m_id)} / {types[m_id]})")

def show_field():
    """현재 앞면/뒷면 필드 상황을 그래픽 형식으로 요약 출력"""
    print("\n[몬스터 존]")
    for i, zone in enumerate(monster_field):
        if zone["card"]:
            m_id = zone["card"] // 100
            print(f" M{i+1}: {names[m_id]} ({zone['pos']})")
        else:
            print(f" M{i+1}: (빈칸)")
            
    print("\n[마법 / 함정 존]")
    for i, zone in enumerate(st_field):
        if zone["card"]:
            m_id = zone["card"] // 100
            if zone["parent_zone"] is not None:
                # 꼬마모스에게 장착된 상태일 때 연동 및 버틴 턴 수 출력
                print(f" S{i+1}: {names[m_id]} (장착:M{zone['parent_zone']+1}.{zone['counter']}t)")
            else:
                display_name = names[m_id] if zone["pos"] == "faceup" else "뒷면 카드"
                print(f" S{i+1}: {display_name} ({zone['pos']})")
        else:
            print(f" S{i+1}: (빈칸)")

def show_card_detail(target_str):
    """특정 구역의 카드를 정밀 탐색하여 정보를 상세 출력하는 정보 도구"""
    if len(target_str) < 2:
        print("명령어가 올바르지 않습니다."); wait(); return
        
    where = target_str[0]
    if not target_str[1:].isdigit():
        print("번호 입력 오류"); wait(); return
    idx = int(target_str[1:]) - 1
    
    uid = None
    status_str = "상태: 패 보유"
    
    if where == 'h':
        if valid_hand(idx): uid = hand[idx]
    elif where == 'm':
        if valid_field(idx) and monster_field[idx]["card"]:
            uid = monster_field[idx]["card"]
            status_str = f"상태: 몬스터 존 M{idx+1} ({monster_field[idx]['pos']})"
    elif where == 's':
        if valid_field(idx) and st_field[idx]["card"]:
            uid = st_field[idx]["card"]
            zone = st_field[idx]
            if zone["parent_zone"] is not None:
                status_str = f"상태: M{zone['parent_zone']+1}번 몬스터에게 장착 중 ({zone['counter']}턴 경과)"
            else:
                status_str = f"상태: 마함 존 S{idx+1} ({zone['pos']})"
                
    if uid is None:
        print("지정한 위치에 카드가 존재하지 않습니다."); wait(); return
        
    m_id = uid // 100
    clear_screen()
    print("========================================")
    print(f" 카드명 : {names[m_id]}")
    print(f" 분류   : {level_str(m_id)} / {tribes[m_id]} / {types[m_id]}")
    print(f" {status_str}")
    print("----------------------------------------")
    print(f" [효과]")
    print(f" {parse_effect(effects[m_id])}")
    print("========================================")
    wait()

# ==========================================
# 게임 엔진 작동 메커니즘 함수들
# ==========================================
def send_monster_to_grave(m_idx):
    """몬스터가 전투/효과로 파괴되었을 때 연쇄 장착 카드까지 함께 묘지로 보내는 처리"""
    if monster_field[m_idx]["card"] is None: return
    
    uid = monster_field[m_idx]["card"]
    monster_field[m_idx] = {"card": None, "pos": None, "set_turn": None, "counter": 0}
    grave.append(uid)
    
    # 이 몬스터에게 장착되어 있던 장착 마법들을 연쇄 파괴 처리
    for i in range(5):
        if st_field[i]["card"] and st_field[i]["parent_zone"] == m_idx:
            st_uid = st_field[i]["card"]
            st_field[i] = {"card": None, "pos": None, "set_turn": None, "counter": 0, "parent_zone": None}
            grave.append(st_uid)
            print(f">> [연쇄 파괴] 장착 대상 소멸로 인해 {names[st_uid // 100]}가 묘지로 보내졌습니다.")

def play_magic_trap(hand_idx):
    """패에서 직접 수동으로 마법/함정을 활성화하거나 세트하는 구식 제어 기기"""
    if not valid_hand(hand_idx): return
    uid = hand[hand_idx]
    m_id = uid // 100
    card_type = tribes[m_id]
    
    print(f"\n[{names[m_id]}] 선택됨.")
    print("1. 패에서 직접 발동 (마법만 가능) / 2. 마함존에 세트")
    choice = input("입력 → ").strip()
    
    empty_idx = -1
    for i in range(5):
        if st_field[i]["card"] is None:
            empty_idx = i; break
    if empty_idx == -1:
        print("마함존 공간 부족"); wait(); return

    if choice == "1":
        if card_type != "마법":
            print("함정은 패에서 직접 발동할 수 없습니다."); wait(); return
        hand.pop(hand_idx)
        grave.append(uid)
        show_step(f">> 마법 카드 [{names[m_id]}] 발동 및 효과 처리 후 묘지 이송.")
    elif choice == "2":
        hand.pop(hand_idx)
        st_field[empty_idx] = {"card": uid, "pos": "set", "set_turn": turn, "counter": 0, "parent_zone": None}
        show_step(f">> 마함존 {empty_idx+1}번에 세트 완료.")

def trigger_set_st(st_idx):
    """마함 존에 뒷면 세트된 마법/함정을 오픈하여 격발시키는 처리기"""
    if not valid_field(st_idx): return
    zone = st_field[st_idx]
    if zone["card"] is None or zone["pos"] != "set":
        print("발동 불가"); wait(); return
        
    m_id = zone["card"] // 100
    card_type = tribes[m_id]
    
    # 상대 턴이 아닌데 함정을 강제 기동하려는 행위 방어
    if card_type == "함정" and not is_opponent_turn:
        print("함정 카드는 상대 턴 조건 충족 시 발동 대기 상태입니다."); wait(); return
    
    zone["pos"] = "faceup"
    uid = zone["card"]
    
    # 1회성 일반 마법(6=어스퀘이크, 12=원위치) 혹은 함정은 발동 후 바로 묘지행
    if m_id in [6, 12] or card_type == "함정": 
        st_field[st_idx] = {"card": None, "pos": None, "set_turn": None, "counter": 0, "parent_zone": None}
        grave.append(uid)
        show_step(f">> [{names[m_id]}] 발동 성공! 효과 처리 후 묘지로 보내집니다.")
    else:
        # 그 외 지속/장착마법은 필드에 유지
        show_step(f">> 세트 지속/장착 마법 [{names[m_id]}] 필드 활성화.")

def equip_cocoon(hand_idx):
    """패의 진화의 고치를 필드의 꼬마모스에게 연동 장착하는 구식 기구"""
    if not valid_hand(hand_idx) or (hand[hand_idx] // 100 != 2):
        print("진화의 고치가 아닙니다."); wait(); return
        
    targets = []
    for i, zone in enumerate(monster_field):
        if zone["card"] and (zone["card"] // 100 == 1) and (zone["pos"] != "set"):
            targets.append(i)
            
    if not targets:
        print("필드에 앞면 표시 '꼬마모스'가 없습니다."); wait(); return
        
    print("\n=== 장착 대상 선택 ===")
    for t in targets:
        print(f"[{t+1}] {t+1}번 몬스터 존의 꼬마모스")
    
    sel = input("선택 → ").strip()
    if not sel.isdigit() or (int(sel)-1) not in targets:
        print("대상 오류"); wait(); return
        
    m_target = int(sel) - 1
    
    st_idx = -1
    for i in range(5):
        if st_field[i]["card"] is None:
            st_idx = i; break
    if st_idx == -1:
        print("마함존 공간 부족"); wait(); return
        
    uid = hand.pop(hand_idx)
    st_field[st_idx] = {
        "card": uid,
        "pos": "faceup",
        "set_turn": turn,
        "counter": 0,
        "parent_zone": m_target
    }
    show_step(f">> 꼬마모스(M{m_target+1})에게 진화의 고치를 장착했습니다. (M{m_target+1}.0t)")

def check_moth_special_summon(hand_idx):
    """패에 있는 그레이트 모스류 룰 특수 소환 조건(턴 수 경과)이 맞는지 검사하여 진화 실행"""
    if not valid_hand(hand_idx): return
    uid = hand[hand_idx]
    m_id = uid // 100
    
    if m_id not in rule_special_monsters:
        print("특수 소환 몬스터가 아닙니다."); wait(); return
        
    req_turn = moth_require_turn[m_id]
    
    valid_pairs = []
    for i, st_zone in enumerate(st_field):
        if st_zone["card"] and (st_zone["card"] // 100 == 2) and (st_zone["parent_zone"] is not None):
            if st_zone["counter"] >= req_turn:
                m_idx = st_zone["parent_zone"]
                if monster_field[m_idx]["card"] and (monster_field[m_idx]["card"] // 100 == 1):
                    valid_pairs.append((i, m_idx))
                    
    if not valid_pairs:
        print(f"[{names[m_id]}] 소환 실패: {req_turn}턴 이상 장착된 고치 페어가 없습니다."); wait(); return
        
    chosen_st, chosen_m = valid_pairs[0]
    
    c_uid = st_field[chosen_st]["card"]
    m_uid = monster_field[chosen_m]["card"]
    
    # 소재 카드 필드에서 청소 및 묘지 안착
    st_field[chosen_st] = {"card": None, "pos": None, "set_turn": None, "counter": 0, "parent_zone": None}
    monster_field[chosen_m] = {"card": None, "pos": None, "set_turn": None, "counter": 0}
    
    grave.append(c_uid)
    grave.append(m_uid)
    
    hand.pop(hand_idx)
    # 신규 진화 몬스터 소환 완료
    monster_field[chosen_m] = {"card": uid, "pos": "atk", "set_turn": turn, "counter": 0}
    
    clear_screen()
    print("==================================================")
    print(f" ▶▶ 진화 유발 조건 충족 ({req_turn}턴 달성) ◀◀")
    print(f" 필드의 고치와 유충을 묘지로 보내고 패에서...")
    print(f" 【{names[m_id]}】 초진화 룰 특수 소환 성공!!")
    print("==================================================")
    wait()

# ==========================================
# 🆕 통합 단축코드 분석기 (7자리 vs 8자리)
# ==========================================
def process_shortcut_unified(cmd):
    """
    7자리 이하: 몬스터 소환/세트 단축 코드로 분기
    8자리 이상: 마법 발동/세트/장착 단축 코드로 분기 (앞의 7자리 슬라이싱)
    """
    
    # ------------------------------------------
    # CASE A: 8자리 이상 입력 (마법/효과 발동 및 장착 연동)
    # ------------------------------------------
    if len(cmd) >= 8:
        sub_cmd = cmd[:7] # 앞 7자리 파싱 진행
        from_zone = int(sub_cmd[0])       # 1번째: 발동 위치 (0=패, 1=필드, 2=묘지, 3=제외)
        st_val = int(sub_cmd[1])          # 2번째: 지정 마함존 (1~5)
        sub_val = int(sub_cmd[2])         # 3번째: 일의 자리 (기본 0)
        effect_no = int(sub_cmd[3])       # 4번째: 효과 번호
        target_zone = int(sub_cmd[4])     # 5번째: 대상 카드 위치 (1=필드)
        target_action = int(sub_cmd[5])   # 6번째: 대상 카드 행선지 (0=이동 없이 필드 유지)
        is_equip = int(sub_cmd[6])        # 7번째: 장착/지속 판별 (1=필드 유지, 0=묘지 전송)

        # 1. 발동할 마법 카드가 패(0)에 있는지 찾기
        uid = None
        hand_idx = -1
        if from_zone == 0:
            # 패 전체를 돌면서 마법 카드인지 판별해 우선순위 선택
            for idx, h_uid in enumerate(hand):
                card_m_id = h_uid // 100
                if tribes[card_m_id] == "마법":
                    uid = h_uid
                    hand_idx = idx
                    break
            if uid is None:
                print(">> [에러] 패에 발동 가능한 마법 카드가 존재하지 않습니다."); wait(); return
        else:
            print(">> [가이드] 현재 간이 버전은 패 발동(0) 마법을 최우선 처리합니다."); wait(); return

        # 2. 지정 마함존 적합성 판정
        st_idx = st_val - 1
        if not valid_field(st_idx) or st_field[st_idx]["card"] is not None:
            print(">> [에러] 대상 지정 마함존이 비어있지 않거나 범위를 초과했습니다."); wait(); return

        # 3. 대상 타겟팅 분석 (꼬마모스 등 필드 몬스터 여부 검증)
        m_target = -1
        if target_zone == 1:
            for idx, zone in enumerate(monster_field):
                if zone["card"] and (zone["card"] // 100 == 1): # 꼬마모스 탐색
                    m_target = idx
                    break
        
        card_m_id = uid // 100
        # 10=대수해, 11=무시가호는 지속 마법이므로 규칙에 따라 7번째 자리를 1로 가이드 보정해 줌
        is_continuous = card_m_id in [10, 11]
        
        # 패에서 카드를 소비하여 이동 처리 시작
        hand.pop(hand_idx)
        
        # 장착 규칙 작동 혹은 지속 마법 판별 작동 시 필드 마함존에 존속시킴
        if is_equip == 1 or is_continuous:
            st_field[st_idx] = {
                "card": uid,
                "pos": "faceup",
                "set_turn": turn,
                "counter": 0,
                # 장착 마법일 경우에만 parent_zone(장착 대상)을 설정
                "parent_zone": m_target if card_m_id == 2 else None 
            }
            if card_m_id == 2:
                show_step(f">> [단축 장착] {names[card_m_id]}을 꼬마모스(M{m_target+1})에 장착 완료!")
            else:
                show_step(f">> [단축 지속] 지속 마법 {names[card_m_id]}을 S{st_idx+1}에 영구 배치 완료!")
        else:
            # 지속/장착이 아니면 일반 마법 효과 기동 처리 후 고스란히 묘지로 즉시 이송
            grave.append(uid)
            show_step(f">> [단축 발동] 일반 마법 {names[card_m_id]} 효과 정상 기동 및 묘지 전송 완료.")

    # ------------------------------------------
    # CASE B: 7자리 이하 입력 (몬스터 단축 소환)
    # ------------------------------------------
    else:
        play_type = int(cmd[0])       # 1번째: 1 = 일반 플레이
        summon_type = int(cmd[1])     # 2번째: 1 = 일반 소환, 2 = 룰 특수 소환
        from_where = int(cmd[2])      # 3번째: 3 = 패에서 출발
        hand_idx = int(cmd[3]) - 1    # 4번째: 패의 카드 인덱스
        field_idx = int(cmd[4]) - 1   # 5번째: 놓을 필드 인덱스
        reconfirm = int(cmd[5])       # 6번째: 패 번호 재검증
        pos_type = int(cmd[6])        # 7번째: 표시형식 (1=앞면 공격, 2=뒷면 수비 세트)

        # 인덱스 유효 범위 및 무결성 체크
        if from_where != 3 or not valid_hand(hand_idx):
            print(">> [에러] 패 범위를 초과했거나 출발지가 패가 아닙니다."); wait(); return

        # 1. 일반 소환 로직 실행
        if summon_type == 1:
            global normal_summon_used
            if normal_summon_used:
                print(">> [에러] 이번 턴에 일반 소환을 이미 수행하여 불가합니다."); wait(); return
            
            uid = hand[hand_idx]
            m_id = uid // 100
            
            # 마법/함정이나 특소 전용 대형 몬스터는 통상 소환 불가 차단
            if tribes[m_id] in ["마법", "함정"] or m_id in rule_special_monsters:
                print(">> [에러] 일반 소환이 제한된 카드입니다."); wait(); return

            if monster_field[field_idx]["card"] is not None:
                print(">> [에러] 지정한 몬스터 존 자리가 비어있지 않습니다."); wait(); return

            # 표시 형식 처리 후 필드 배치
            pos = "atk" if pos_type == 1 else "set"
            hand.pop(hand_idx)
            monster_field[field_idx] = {"card": uid, "pos": pos, "set_turn": turn, "counter": 0}
            normal_summon_used = True
            show_step(f">> [단축 소환] {names[m_id]}을 M{field_idx+1}에 성공적으로 안착시켰습니다.")

        # 2. 룰 특수 소환(체인 검사) 로직 실행
        elif summon_type == 2:
            check_moth_special_summon(hand_idx)

# ==========================================
# 간이 구현된 상대 턴 시스템
# ==========================================
def opponent_turn():
    """상대가 가볍게 수단을 전개하고 자신 턴에 깔아둔 함정 발동 타이밍 확인"""
    global is_opponent_turn
    is_opponent_turn = True

    clear_screen()
    print(f"\n==============================")
    print(f"      상대 턴 (TURN {turn})")
    print(f"==============================")
    print("상대가 행동을 시작합니다...")
    wait()

    # 함정 카드 발동 메커니즘: 현재 내 마함존에 세트된 카드가 함정 속성일 때 활성화 가능성 제공
    trap_zones = [i for i, z in enumerate(st_field)
                  if z["card"] and z["pos"] == "set" and tribes[z["card"] // 100] == "함정"]

    if trap_zones:
        print("\n[세트된 함정 카드 발견]")
        for i in trap_zones:
            print(f" S{i+1}: 뒷면 카드")
        cmd = input("발동할 함정 번호 입력 (없으면 엔터) → ").strip()
        if cmd.isdigit() and (int(cmd) - 1) in trap_zones:
            trigger_set_st(int(cmd) - 1) # 함정 오픈

    print(">> 상대 턴 종료.")
    wait()
    is_opponent_turn = False

# ==========================================
# 메인 게임 루프 핸들러 (사용자 행동 제어)
# ==========================================
def main_phase1():
    """메인 페이즈 1: 사용자의 선택 명령어를 감지하고 알맞은 규칙에 라우팅"""
    global normal_summon_used
    while True:
        clear_screen()
        print("=== 메인 페이즈 ===")
        show_field()
        show_hand()
        
        has_cocoon = any(uid // 100 == 2 for uid in hand)
        has_boss = any(uid // 100 in rule_special_monsters for uid in hand)

        print("\n[명령어 가이드]")
        print("- 숫자 : 몬스터 일반 소환/세트 (구식 개별 소환 방식)")
        print("- m숫자 : 패의 마법/함정 제어 (예: m3)")
        
        if has_cocoon:
            print("- g숫자 : [장착 가능] 패의 진화의 고치를 꼬마모스에 장착")
        if has_boss:
            print("- s숫자 : [특소 가능] 패의 모스류 룰 특수 소환 체크")
            
        print("- o숫자 : 마함존에 세트된 마법/함정 발동")
        print("- d(h/m/s)숫자 : 패/필드 카드 상세 보기 (예: dh1, dm2)")
        print("- 7자리 단축소환 : 몬스터 일반/특수 소환 통합 실행 (예: 1134441, 1231211)")
        print("- 8자리 마법장착 : 패의 고치 장착/지속마법 발동 통합 실행 (예: 03011010)")
        print("- r숫자 : 몬스터 파괴 시뮬레이션 [연쇄파괴 확인용]")
        print("- e : 페이즈 종료")
        
        cmd = input("\n입력 → ").strip().lower()
        
        if cmd == "e": break
        
        # 🆕 통합 단축코드 감지 (숫자이고 길이가 7 이상일 때 작동)
        if cmd.isdigit() and len(cmd) >= 7:
            process_shortcut_unified(cmd)
            continue
        
        # 카드 상세 보기 분기
        if cmd.startswith("d") and len(cmd) >= 3 and cmd[1] in ['h', 'm', 's']:
            show_card_detail(cmd[1:])
            continue
        
        # 일반 단일 몬스터 소환 수동 로직
        if cmd.isdigit():
            idx = int(cmd) - 1
            if valid_hand(idx):
                uid = hand[idx]
                m_id = uid // 100
                if tribes[m_id] in ["마법", "함정"] or m_id in rule_special_monsters:
                    print("일반 소환 불가능 카드"); wait(); continue
                if normal_summon_used:
                    print("소환권 이미 소모됨"); wait(); continue
                    
                pos_choice = input("1. 앞면공격 / 2. 뒷면수비 세트 → ").strip()
                pos = "atk" if pos_choice == "1" else "set"
                
                empty_m = -1
                for i in range(5):
                    if monster_field[i]["card"] is None: empty_m = i; break
                if empty_m == -1: print("몬스터 존 가득 참"); wait(); continue
                
                hand.pop(idx)
                monster_field[empty_m] = {"card": uid, "pos": pos, "set_turn": turn, "counter": 0}
                normal_summon_used = True
                show_step(f">> {names[m_id]} 필드 배치 완료.")
            continue
            
        # 개별 마함 제어 분기
        if cmd.startswith("m") and cmd[1:].isdigit():
            play_magic_trap(int(cmd[1:]) - 1)
            continue
        # 개별 장착 고치 연동 분기
        if cmd.startswith("g") and cmd[1:].isdigit():
            equip_cocoon(int(cmd[1:]) - 1)
            continue
        # 개별 진화 룰 특소 분기
        if cmd.startswith("s") and cmd[1:].isdigit():
            check_moth_special_summon(int(cmd[1:]) - 1)
            continue
        # 세트 카드 격발 분기
        if cmd.startswith("o") and cmd[1:].isdigit():
            trigger_set_st(int(cmd[1:]) - 1)
            continue
        # 파괴 시뮬레이션 작동 확인 분기
        if cmd.startswith("r") and cmd[1:].isdigit():
            send_monster_to_grave(int(cmd[1:]) - 1)
            wait()
            continue

# ==========================================
# 게임 엔진 시작 및 라이프사이클 작동 루프
# ==========================================
# 선공 선패 5장 드로우 세팅
for _ in range(5):
    if deck: hand.append(deck.pop(0))

while True:
    start_turn()      # 자신 턴 셋업 시작 (대기 턴 +1 증가)
    draw_phase()      # 카드 드로우 진행
    main_phase1()     # 사용자가 마음껏 조작하는 메인 페이즈 진입
    
    opponent_turn()   # 상대 턴 진행 (체인 세팅 감지 기회 제공)
    
    if input("다음 턴을 계속 진행합니까? (q 종료) → ").strip().lower() == "q":
        break
    turn += 1 # 턴 카운터 업
