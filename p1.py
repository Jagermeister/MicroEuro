import time
import copy
import sys
import itertools
import json
import math
from collections import deque

def moveMeeples(player, coin, buildings, lended_building, meepleMoves, meeple_locations, lender, harborMaster, harborRoll, verbose):
    moves = []
    #green, green, green, camp, village, red/blue, red/blue, red/blue
    if verbose: verboseMsg = "Lent " + str(lended_building) + "; MMoves: " + str(meepleMoves) + "; "
    new_coin = copy.copy(coin)
    work = 0
    if (buildings | lended_building) & 0b10000000 == 0b10000000:#Camp
        work += 1
    if (buildings | lended_building) & 0b01000000 == 0b01000000:#Village
        work += 1

    for meeple in meepleMoves:
        meeple_locations[meeple-1] += 1
        if meeple_locations[meeple-1] in [4, 7]:
            meeple_locations[meeple-1] -= 3

        if meeple_locations[meeple-1] % 3 == 0:
            new_coin += 1
            if (buildings | lended_building) & 0b00100000 == 0b00100000:#Bank
                new_coin +=1
        else:
            work += 1

    if verbose: harborMsg = ""
    if player == harborMaster:
        harborRolls = [1,2,3]
        if new_coin >= 3 and meeple_locations[5] & meeple_locations[6] & meeple_locations[7] == 0:#free space
            harborRolls.append(4)
        if verbose: harborMsg += "HM rolled a " + str(harborRoll)
    else:
        harborRolls = [harborRoll]

    for harborRoll in harborRolls:
        if (buildings | lended_building) & 0b00001000 == 0b00001000:#Harbor
            if harborRoll == 1:
                work += 1
            elif harborRoll == 2:
                new_coin += 1
            elif harborRoll == 3:
                pass #You rolled Sailer and didnt purchase
            elif harborRoll == 4 and new_coin >= 3:
                new_coin -= 3
                if meeple_locations[7] == 0:
                    meeple_locations[7] = 1 if player == 1 else 4
                elif meeple_locations[6] == 0:
                    meeple_locations[6] = 1 if player == 1 else 4
                else:
                    meeple_locations[5] = 1 if player == 1 else 4
            else: #You already didnt purchase and you also cant (too few $)
                continue

        if verbose: verboseMsg += "W: " + str(work) + "; C: " + str(coin) + "; "
        a, b, c = meeple_locations[0:3]
        if a > b:
            if a > c:
                max = a
                if b > c: med, min = b, c
                else: med, min = c, b
            else:
                med = a
                if b > c: max, min = b, c
                else: max, min = c, b
        else:
            if b > c:
                max = b
                if a > c: med, min = a, c
                else: med, min = c, a
            else: med, max, min = b, c, a
        
        meeple_locations[0:3] = min, med, max
        a, b, c = meeple_locations[5:8]
        if a > b:
            if a > c:
                max = a
                if b > c: med, min = b, c
                else: med, min = c, b
            else:
                med = a
                if b > c: max, min = b, c
                else: max, min = c, b
        else:
            if b > c:
                max = b
                if a > c: med, min = a, c
                else: med, min = c, a
            else: med, max, min = b, c, a

        meeple_locations[5:8] = min, med, max
        grind_work_count = int(work/2)
        if (buildings | lended_building) & 0b00000100 == 0b00000100:#Union
            grind_work_count += int(new_coin/2)

        for r in range(0, grind_work_count + 1):
            new_work = work
            newest_coin = new_coin
            if r == 0:
                pass
            elif r <= int(work/2):
                for g in range(1, r+1):
                    new_work -= 2
                    newest_coin += 1
                if verbose: verboseMsg += "Grind " + str(r) + "x = " + str(new_work) + "w, " + str(newest_coin) + "c "
            else:
                for g in range(1, r-int(work/2)+1):
                    new_work += 1
                    newest_coin -= 2
                if verbose: verboseMsg += "Union " + str(r-int(work/2)) + "x = " + str(new_work) + "w, " + str(newest_coin) + "c "

            moves.append((newest_coin, buildings, meeple_locations, lender, harborMaster, harborRoll))
            if verbose:
                print (len(moves), "Pass", verboseMsg, "nW", new_work, "nC", newest_coin, "b", buildings, "p", len(_affordable_cache[new_work << 12 | newest_coin << 8 | buildings]))

            if not new_work << 12 | newest_coin << 8 | buildings in _affordable_cache:
                print (new_work, newest_coin, buildings, new_work << 12 | newest_coin << 8 | buildings)

            for b in _affordable_cache[new_work << 12 | newest_coin << 8 | buildings]:
                if is_first_finding and _is_first_building[b["V"]]:
                    print ("First Purchase of", b["N"])
                    _is_first_building[b["V"]] = False
                if b["V"] & 0b00000001 == 0b00000001 and meeple_locations[3] == 0:
                    meeple_locations[3] = 1
                elif b["V"] & 0b00000010 == 0b00000010 and meeple_locations[4] == 0:
                    meeple_locations[4] = 1
                elif b["V"] & 0b00001000 == 0b00001000 and harborMaster == 0:
                    harborMaster = player
                moves.append((newest_coin - b["C"], buildings | b["V"], meeple_locations, lender, harborMaster, harborRoll))
                if verbose:
                    print (len(moves), "Purch", b["V"])

    return moves

def player_combinations(turn, node, verbose):
    moves = []
    if turn:
        player = 1
        coin = node[0]
        buildings = node[1]
        other_buildings = node[3]
        other_coin = node[4]
    else:
        player = 2
        coin = node[2]
        buildings = node[3]
        other_buildings = node[1]
        other_coin = node[2]

    meeple_locations = node[4:12]
    lender = node[12]
    harborMaster = node[13]
    harborRoll = node[14]
    meeple_move_options = [(1, node[4]), (2, node[5]), (3, node[6])]
    if buildings & 0b00000001 == 0b00000001:
        meeple_move_options.append((4, node[7]))
    if buildings & 0b00000010 == 0b00000010:
        meeple_move_options.append((5, node[8]))
    if node[9] > 0 and ((player == 1 and node[9] <= 3) or (player == 2 and node[9] > 3)):
        meeple_move_options.append((6, node[9]))
    if node[10] > 0 and ((player == 1 and node[10] <= 3) or (player == 2 and node[10] > 3)):
        meeple_move_options.append((7, node[10]))
    if node[11] > 0 and ((player == 1 and node[11] <= 3) or (player == 2 and node[11] > 3)):
        meeple_move_options.append((8, node[11]))

    seen = set()
        #Combos based on position, not meeple index
    for r in range(len(meeple_move_options) + 1):
        meeple_combos = itertools.combinations(meeple_move_options, r)
        for meeple_combo in meeple_combos:
            key = tuple([n[1] for n in meeple_combo])
            if key in seen:
                continue
            seen.add(key)
            meeple_combo = tuple([n[0] for n in meeple_combo])
            lending = [0b0]
            has_repaid = False
            if lender == player and coin >= 3:
                for option in moveMeeples(player, coin, buildings, 0b0, meeple_combo, list(meeple_locations), player, harborMaster, harborRoll, verbose):
                    new_coin, new_buildings, new_meeple_locations, new_lender, new_harborMaster, new_harborRoll = option
                    if turn:
                        updated_node = (new_coin, new_buildings) + node[2:4] + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                    else:
                        updated_node = node[0:2] + (new_coin, new_buildings) + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                    moves.append(updated_node)
                has_repaid = True
                lender = 0b0

            if buildings & 0b00010000 == 0b00010000 and lender != player:
                lending.extend(_lending_cache[buildings << 8 | other_buildings])
            for lended_building in lending:
                for option in moveMeeples(player, coin if not has_repaid else coin - 3, buildings, lended_building, meeple_combo, list(meeple_locations), player if lended_building != 0b0 else lender, harborMaster, harborRoll, verbose):
                    new_coin, new_buildings, new_meeple_locations, new_lender, new_harborMaster, new_harborRoll = option
                    if turn:
                        updated_node = (new_coin, new_buildings) + node[2:4] + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                    else:
                        updated_node = node[0:2] + (new_coin, new_buildings) + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                    moves.append(updated_node)
    return moves

def toIdentity(moveData):
    #1_786_403 calls = 4.885 tottime vs 11.776
    return moveData[0] | moveData[1] << 4 | moveData[2] << 12 | moveData[3] << 16 | moveData[4] << 24 | moveData[5] << 26 | \
        moveData[6] << 28 | moveData[7] << 30 | moveData[8] << 32 | moveData[9] << 36 | moveData[10] << 40 | moveData[11] << 44 | \
        moveData[12] << 46 | moveData[13] << 48 | moveData[14] << 50

def toIdentityTurn(moveData, player):
    return toIdentity(moveData) << 1 | player 

import multiprocessing
_buildings = [
#Work, Coin, Value, Requirement
    {"W": 2, "C": 3, "V": 0b00000001, "N": "Camp"},
    {"W": 4, "C": 6, "V": 0b00000010, "N": "Village", "R": 0b00000001},
    {"W": 3, "C": 4, "V": 0b00000100, "N": "Union"},
    {"W": 4, "C": 4, "V": 0b00001000, "N": "Harbor"},
    {"W": 2, "C": 2, "V": 0b00010000, "N": "Lender"},
    {"W": 4, "C": 5, "V": 0b00100000, "N": "Bank", "R": 0b00010000},
    {"W": 2, "C": 3, "V": 0b01000000, "N": "Mill"},
    {"W": 5, "C": 5, "V": 0b10000000, "N": "Smithy", "R": 0b01000000}
]

_affordable_cache = {}
_lending_cache = {}
_building_count_cache = {}

_output_header = "Ply ___IN___ __OUT___ __SAVE__ __CUT___ __SKIP__ __TOTAL_ __CACHE_\tTime (s)"
_output_format = "{0:02d}  {1:08d} {2:08d} {3:08d} {4:08d} {5:08d} {6:08d} {7:08d}\t@ {8}"
_update_header = "Ply ________ __OUT___ __SAVE__ __CUT___ __SKIP__ ________ __CACHE_\tTime (s)"
_update_format = "{0}  ........ {1:08d} {2:08d} {3:08d} {4:08d} ........ {5:08d}\t@ {6}"

def check_gameover(moveHistory, path_length, total_in, save, cut, skip, total_generated, cache_count, total_time):
    if moveHistory[-1][1] | moveHistory[-1][3] == 0b11111111 or _building_count_cache[moveHistory[-1][1]] == 7 or _building_count_cache[moveHistory[-1][3]] == 7:
        print("Game Over!!")
        for m in moveHistory:
            print(">>", m)
        print(_output_format.format(
            path_length, total_in, save + cut + skip, save, cut, skip, save + cut + skip + total_generated, cache_count, total_time))
        sys.stdout.flush()
        return True
    elif len(moveHistory) > 12:
        print("Ply Limit Reached")
        print(_output_format.format(
            path_length, total_in, save + cut + skip, save, cut, skip, save + cut + skip + total_generated, cache_count, total_time))
        sys.stdout.flush()
        return True

_is_first_building = {0b00000001: True,0b00000010: True,0b00000100: True,0b00001000: True,0b00010000: True,0b00100000: True,0b01000000: True,0b10000000: True}
is_first_finding = False

def main():
    skipped_count = 0
    seen_count = 0
    total_seen_count = 0

    for wcb in itertools.product(range(16), range(16), range(256)):
        _affordable_cache[wcb[0] << 12 | wcb[1] << 8 | wcb[2]] = [b for b in _buildings if b["V"] & wcb[2] != b["V"] and b["W"] <= wcb[0] and b["C"] <= wcb[1] and (("R" not in b) or (b["R"] & wcb[2] == b["R"]))]
    for p in itertools.product(range(256), range(256)):
        _lending_cache[p[0] << 8 | p[1]] = [b["V"] for b in _buildings if b["V"] & p[0] != b["V"] and b["V"] & p[1] == b["V"]]
    for b in range(256):
        _building_count_cache[b] = bin(b).count("1")

    positions_seen = {}
    queue = deque()
    path_length = 1
    path_count = 1
    seen_count = 0
    total_generated = 0
    all_moves = []
    test_output = False
    if test_output:
        save = []
        skip = []
        cut = []
    else:
        save = 0
        skip = 0
        cut = 0
    total_seen_count = 0
    skipped_count = 0
    time_start = time.clock()
    #P1$, Builings, P2$, Buildings, Green Locations, Camp, Village, Red / Blue, Lender, HarborMaster, HarborRoll
    queue.append([(2, 0, 3, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0)])
        #Starting Position!

    print(_output_header)
    while queue:
        moveHistory = queue.popleft()
        move = moveHistory[-1]
        if test_output:
            if check_gameover(moveHistory, path_length, seen_count, len(save), len(cut), len(skip), total_generated, len(positions_seen), time.clock() - time_start):
                return
        else:
            if check_gameover(moveHistory, path_length, seen_count, save, cut, skip, total_generated, len(positions_seen), time.clock() - time_start):
                return
        
        if len(moveHistory) != path_length:
            if test_output:
                total_generated += len(save) + len(cut) + len(skip)
                print(_output_format.format(
                    path_length, seen_count, len(save) + len(cut) + len(skip), len(save), len(cut), len(skip), total_generated, len(positions_seen), time.clock() - time_start))
            else:
                total_generated += save + cut + skip
                print(_output_format.format(
                    path_length, seen_count, save + cut + skip, save, cut, skip, total_generated, len(positions_seen), time.clock() - time_start))
            
            if test_output:
                parent = ""
                save_keys = [toIdentity(s) for s in save]
                skip_keys = [toIdentityTurn(s, path_length % 2) for s in skip]
                save2 = copy.copy(save)
                save_keys = sorted(save_keys)
                #print(json.dumps(save_keys))
                s = 0
                k = 0
                for m in all_moves:
                    #print('"' + str(m[0]) + '"', "->", '"' + str(m[1]) + '";')
                    if test_output:
                        if parent != m[0]:
                            print("P",m[0])
                            parent = m[0]
                        if m[1] in save2:
                            save2.remove(m[1])
                            if m[1] in skip:
                                print (len([kk for kk in all_moves if kk[1] == m[1]]), m[1])
                            else:
                                print("_",m[1])
                            s += 1
                        else:
                            print("!",m[1])
                            k += 1

                if (s != len(save) or k != (len(cut) + len(skip))):
                    print()
                    print(">>>>>", s, "!=", len(save), "and/or", k, "!=", len(skip))
                    print("!!!!!", s, "!=", len(save), "and/or", k, "!=", len(skip))
                    print("<<<<<", s, "!=", len(save), "and/or", k, "!=", len(skip))
                    print()
            path_length = len(moveHistory)
            path_count = len(list(queue)) + 1
            total_seen_count += seen_count
            seen_count = 0
            if test_output:
                all_moves = []
                save = []
                skip = []
                cut = []
            else:
                save = 0
                skip = 0
                cut = 0
            sys.stdout.flush()

        seen_count += 1
        futureMoves = player_combinations(len(moveHistory) % 2, move, False)#len(moveHistory) == 2)

        for futureMove in futureMoves:
            if save + cut + skip > 0 and (save + cut + skip) % 500000 == 0:
                print (_update_format.format("..", save + cut + skip, save, cut, skip, len(positions_seen), time.clock() - time_start))
                sys.stdout.flush()

            key = toIdentityTurn(futureMove, (len(moveHistory) + 1) % 2)
            if test_output:
                all_moves.append((move, futureMove))
            if positions_seen.get(key) is None:
                positions_seen[key] = True
                new_path = deque(list(moveHistory))
                new_path.append(futureMove)
                if test_output:
                    if len(moveHistory) >= 6 and (futureMove[1] & futureMove[3] == 0 or moveHistory[lookback][1] == futureMove[1] or moveHistory[lookback][3] == futureMove[3]):
                        cut.append(futureMove)
                    else:
                        save.append(futureMove)
                        queue.append(new_path)
                else:
                    if len(moveHistory) >= 6 and (futureMove[1] & futureMove[3] == 0 or moveHistory[lookback][1] == futureMove[1] or moveHistory[lookback][3] == futureMove[3]):
                        #no one has purchased or you havent purchased in 3 turns
                        cut += 1
                    else:
                        save += 1
                        queue.append(new_path)
            else:
                skipped_count += 1
                if test_output:
                    skip.append(futureMove)
                else:
                    skip += 1

lookback = -6
if __name__ ==  '__main__':
    multiprocessing.freeze_support()
    import cProfile, pstats, io
    pr = cProfile.Profile()
    pr.enable()

    main()

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    print(s.getvalue())