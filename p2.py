import time
import copy
import sys
import itertools
import json
import math
from collections import deque

#CACHES
_affordable_cache = {}
    #For Work, Coin, Buildings what can I purchase
    #Key = work << 12 | coin << 8 | buildings
_lending_cache = {}
    #For my buildings and your buildings, what can I steal
    #Key = buildings << 8 | yourBuildings
_building_count_cache = {}
    #For buildings, how many have been purchased
    #Key = buildings
_buildings = [
    # Work,   Coin,   Value,           Name            Requirement
    {"W": 2, "C": 3, "V": 0b00000001, "N": "Camp"},
    {"W": 4, "C": 6, "V": 0b00000010, "N": "Village", "R": 0b00000001},
    {"W": 3, "C": 4, "V": 0b00000100, "N": "Union"},
    {"W": 4, "C": 4, "V": 0b00001000, "N": "Harbor"},
    {"W": 2, "C": 2, "V": 0b00010000, "N": "Lender"},
    {"W": 4, "C": 5, "V": 0b00100000, "N": "Bank",    "R": 0b00010000},
    {"W": 2, "C": 3, "V": 0b01000000, "N": "Mill"},
    {"W": 5, "C": 5, "V": 0b10000000, "N": "Smithy",  "R": 0b01000000}
]

def toIdentity(moveData):
    return moveData[0] | moveData[1] << 4 | moveData[2] << 12 | moveData[3] << 16 | moveData[4] << 24 | moveData[5] << 26 | \
        moveData[6] << 28 | moveData[7] << 30 | moveData[8] << 32 | moveData[9] << 36 | moveData[10] << 40 | moveData[11] << 44 | \
        moveData[12] << 46 | moveData[13] << 48 | moveData[14] << 50 | moveData[15] << 52 | moveData[16] << 60

def toIdentityTurn(moveData, player):
    return toIdentity(moveData) << 1 | player 

def meepleCount(player, buildings, meeple_locations):
    n = 3
    if buildings & 0b00000001 == 0b00000001:
        n += 1
    if buildings & 0b00000010 == 0b00000010:
        n += 1
    if meeple_locations[5] > 0 and ((player == 1 and meeple_locations[5] <= 3) or (player == 2 and meeple_locations[5] > 3)):
        n += 1
    if meeple_locations[6] > 0 and ((player == 1 and meeple_locations[6] <= 3) or (player == 2 and meeple_locations[6] > 3)):
        n += 1
    if meeple_locations[7] > 0 and ((player == 1 and meeple_locations[7] <= 3) or (player == 2 and meeple_locations[7] > 3)):
        n += 1
    return n

def valuateState(moveData):
    b1, b2 = 0, 0
    for b in _buildings:
        if moveData[15] & b["V"] == b["V"]:
            b1 += 3
        if moveData[16] & b["V"] == b["V"]:
            b2 += 3

    m1, m2 = meepleCount(1, moveData[1], moveData[4:12]), meepleCount(2, moveData[3], moveData[4:12])
    c1, c2 = int(moveData[0] / 4), int(moveData[2] / 4)
    return (b1 + m1 + c1) - (b2 + m2 + c2)

def moveMeeples(player, coin, buildings, other_coin, other_buildings, lended_building, meepleMoves, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, isLendable):
    moves = []
    #green, green, green, camp, village, red/blue, red/blue, red/blue
    verbose = False
    meeple_locations = copy.copy(meeple_locations)
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
            new_meeple_locations = copy.copy(meeple_locations)
            new_work = copy.copy(work)
            newest_coin = copy.copy(new_coin)
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

            moves.append((newest_coin, buildings, new_meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp))
            if verbose:
                print (len(moves), "Pass", verboseMsg, "nW", new_work, "nC", newest_coin, "b", buildings, "p", len(_affordable_cache[new_work << 12 | newest_coin << 8 | buildings]))

            if not new_work << 12 | newest_coin << 8 | buildings in _affordable_cache:
                print (new_work, newest_coin, buildings, new_work << 12 | newest_coin << 8 | buildings)

            for b in _affordable_cache[new_work << 12 | newest_coin << 8 | buildings]:
                new_b1vp = b1vp
                new_b2vp = b2vp
                if b["V"] & 0b00000001 == 0b00000001 and new_meeple_locations[3] == 0:
                    new_meeple_locations[3] = 1
                elif b["V"] & 0b00000010 == 0b00000010 and new_meeple_locations[4] == 0:
                    new_meeple_locations[4] = 1
                elif b["V"] & 0b00001000 == 0b00001000 and harborMaster == 0:
                    harborMaster = player
                elif b["V"] & 0b00010000 == 0b00010000:
                    pass#lend buildings

                if b["V"] & other_buildings != b["V"]:
                    if player == 1:
                        new_b1vp |= b["V"]
                    else:
                        new_b2vp |= b["V"]
                    
                moves.append((newest_coin - b["C"], buildings | b["V"], new_meeple_locations, lender, harborMaster, harborRoll, new_b1vp, new_b2vp))
                if verbose:
                    print (len(moves), "Purch", b["V"])


    return moves


def meeple_movements(player, c1, b1, c2, b2, lended_building, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, isLendable):
    moves = []
    meeple_move_options = [1, 2, 3]#[(1, node[4]), (2, node[5]), (3, node[6])]
        #Index, Location
    if b1 & 0b00000001 == 0b00000001:
        meeple_move_options.append(4)#(4, node[7]))
    if b1 & 0b00000010 == 0b00000010:
        meeple_move_options.append(5)#(5, node[8]))
    if meeple_locations[5] > 0 and ((player == 1 and meeple_locations[5] <= 3) or (player == 2 and meeple_locations[5] > 3)):
        meeple_move_options.append(6)#(6, node[9]))
    if meeple_locations[6] > 0 and ((player == 1 and meeple_locations[6] <= 3) or (player == 2 and meeple_locations[6] > 3)):
        meeple_move_options.append(7)#(7, node[10]))
    if meeple_locations[7] > 0 and ((player == 1 and meeple_locations[7] <= 3) or (player == 2 and meeple_locations[7] > 3)):
        meeple_move_options.append(8)#(8, node[11]))

    #TODO: This needs to be by type (common, camp/village, sailors)
    if isLendable:
        meeple_moves = itertools.chain.from_iterable(itertools.permutations(meeple_move_options, r) for r in range(len(meeple_move_options)+1))
    else:
        meeple_moves = itertools.chain.from_iterable(itertools.combinations(meeple_move_options, r) for r in range(len(meeple_move_options)+1))

    for meeple_combo in meeple_moves:
        if meeple_combo == ():
            continue
        for option in moveMeeples(player, c1, b1, c2, b2, lended_building, meeple_combo, list(meeple_locations), lender, harborMaster, harborRoll, b1vp, b2vp, isLendable):
            new_coin, new_buildings, new_meeple_locations, new_lender, new_harborMaster, new_harborRoll, new_b1vp, new_b2vp = option
            if player == 1:
                updated_node = (new_coin, new_buildings) + (c2, b2) + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll) + (new_b1vp, new_b2vp)
            else:
                updated_node = (c2, b2) + (new_coin, new_buildings) + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll) + (new_b1vp, new_b2vp)
            moves.append(updated_node)
    return moves

def player_combinations(turn, node, verbose):
    return generateAllMoves(turn == 1, node)

def generateAllMoves(player, node):
        #this state 'node' into data to generate moves
    moves = []
    if player:
        player = 1
        coin, buildings, other_coin, other_buildings = node[0], node[1], node[2], node[3]
    else:
        player = 2
        coin, buildings, other_coin, other_buildings = node[2], node[3], node[0], node[1]

    meeple_locations = node[4:12]
    lender = node[12]
    harborMaster = node[13]
    harborRoll = node[14]
    b1vp, b2vp = node[15], node[16]
#player, c1, b1, c2, b2, lended_building, meeple_locations, lender, harborMaster, harborRoll, isLendable
    if buildings & 0b00010000 == 0b00010000:
        lendable_buildings = [0b0]
        lendable_buildings.extend(_lending_cache[buildings << 8 | other_buildings])
        if lender == player:
            if coin >= 3:
                for lended_building in lendable_buildings:
                    moves.extend(meeple_movements(player, coin - 3, buildings, other_coin, other_buildings, lended_building, meeple_locations, 0b0 if lended_building == 0b0 else player, harborMaster, harborRoll, b1vp, b2vp, False))
            else:
                moves.extend(meeple_movements(player, coin, buildings, other_coin, other_buildings, 0b0, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, isLendable=True))

            moves.extend(meeple_movements(player, coin, buildings, other_coin, other_buildings, 0b0, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, False))
        else:
            for lended_building in _lending_cache[buildings << 8 | other_buildings]:
                moves.extend(meeple_movements(player, coin, buildings, other_coin, other_buildings, lended_building, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, False))
    else:
        moves = meeple_movements(player, coin, buildings, other_coin, other_buildings, 0b0, meeple_locations, lender, harborMaster, harborRoll, b1vp, b2vp, False)
        #for meeple_combo in itertools.chain.from_iterable(itertools.combinations(meeple_move_options, r) for r in range(len(meeple_move_options)+1)):
    
    return moves
    meeple_move_options = [1, 2, 3]#[(1, node[4]), (2, node[5]), (3, node[6])]
        #Index, Location
    if buildings & 0b00000001 == 0b00000001:
        meeple_move_options.append(4)#(4, node[7]))
    if buildings & 0b00000010 == 0b00000010:
        meeple_move_options.append(5)#(5, node[8]))
    if node[9] > 0 and ((player == 1 and node[9] <= 3) or (player == 2 and node[9] > 3)):
        meeple_move_options.append(6)#(6, node[9]))
    if node[10] > 0 and ((player == 1 and node[10] <= 3) or (player == 2 and node[10] > 3)):
        meeple_move_options.append(7)#(7, node[10]))
    if node[11] > 0 and ((player == 1 and node[11] <= 3) or (player == 2 and node[11] > 3)):
        meeple_move_options.append(8)#(8, node[11]))

    #seen = set()
        #Combos based on position, not meeple index
    for meeple_combo in itertools.chain.from_iterable(itertools.combinations(meeple_move_options, r) for r in range(len(meeple_move_options)+1)):
        #key = tuple([n[1] for n in meeple_combo])
        #if key in seen:
        #    continue
        #seen.add(key)
        #meeple_combo = tuple([n[0] for n in meeple_combo])
        lending = [0b0]
        has_repaid = False
        if lender == player and coin >= 3:
            for option in moveMeeples(player, coin, buildings, 0b0, meeple_combo, list(meeple_locations), player, harborMaster, harborRoll, verbose):
                new_coin, new_buildings, new_meeple_locations, new_lender, new_harborMaster, new_harborRoll = option
                if player == 1:
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
                if player == 1:
                    updated_node = (new_coin, new_buildings) + node[2:4] + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                else:
                    updated_node = node[0:2] + (new_coin, new_buildings) + tuple(new_meeple_locations) + (new_lender, new_harborMaster, new_harborRoll)
                moves.append(updated_node)
    return moves

def main():
    #Constants
    _output_header = "Ply ___IN___ __OUT___ __SAVE__ __CUT___ __SKIP__ __TOTAL_ __CACHE_\tTime (s)"
    _output_format = "{0:02d}  {1:08d} {2:08d} {3:08d} {4:08d} {5:08d} {6:08d} {7:08d}\t@ {8}"
    _update_header = "Ply ________ __OUT___ __SAVE__ __CUT___ __SKIP__ ________ __CACHE_\tTime (s)"
    _update_format = "{0}  ........ {1:08d} {2:08d} {3:08d} {4:08d} ........ {5:08d}\t@ {6}"

    _s = {
        "depth": 1,
        "time": None,
        "in": 0,
        "save": 0,
        "cut": 0,
        "skip": 0,
        "in_total": 0,
        "save_total": 0,
        "cut_total": 0,
        "skip_total": 0
    }
        #Statistics
    _positions_seen = {}
        #Cache of seen positions
    queue = deque()
    #queue.append([(2, 0, 3, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)])
    queue.append([(6, 0b00000001|0b01000000|0b10000000, 3, 0, 2, 2, 2, 2, 0, 1, 1, 1, 0, 0, 0, 0, 0)])
    
    _s["time"] = time.clock()
    print(_output_header)
    while queue:
        #Queue of a List of states representing the move history
        moveHistory = queue.popleft()
        state = moveHistory[-1]
        if len(moveHistory) != _s["depth"]:
            _s["in_total"] += _s["in"]
            _s["save_total"] += _s["save"]
            _s["cut_total"] += _s["cut"]
            _s["skip_total"] += _s["skip"]
            print(_output_format.format(_s["depth"], _s["in"], _s["save"] + _s["cut"] + _s["skip"], _s["save"], _s["cut"], _s["skip"], _s["save_total"] + _s["cut_total"] + _s["skip_total"], len(_positions_seen), time.clock() - _s["time"]))
            sys.stdout.flush()
            _s["depth"] = len(moveHistory)
            _s["in"], _s["save"], _s["cut"], _s["skip"] = 0, 0, 0, 0

        if len(moveHistory) == 4:
            return

        _s["in"] += 1
        futureMoveCount = 0
        for futureMove in player_combinations(len(moveHistory) % 2, state, False):
            if _s["in"] > 1 and (_s["save"] + _s["cut"] + _s["skip"]) % 500000 == 0:
                print (_update_format.format("..", _s["save"] + _s["cut"] + _s["skip"], _s["save"], _s["cut"], _s["skip"], len(_positions_seen), time.clock() - _s["time"]))
                sys.stdout.flush()

            key = toIdentityTurn(futureMove, (len(moveHistory) + 1) % 2)
            if _positions_seen.get(key) is None:
                _positions_seen[key] = True
                moveHistoryNew = deque(list(moveHistory))
                moveHistoryNew.append(futureMove)
                queue.append(moveHistoryNew)
                _s["save"] += 1
            else:
                _s["skip"] += 1

def isGameOver(node):
    if node[1] | node[3] == 0b11111111 or _building_count_cache[node[1]] == 7 or _building_count_cache[node[3]] == 7:
        return True

_alphaBetaTransposition = {}
bestMove = None

def alphaBetaSearch(moveHistory, depth, alpha, beta, color, maxPlayerIsOne, debugOutput):
    global bestMove
    node = moveHistory[-1]
    _alpha = alpha
    lookup = _alphaBetaTransposition.get(node)
    if lookup is not None and lookup[1] >= depth:
        if lookup[2] == "E":
            return lookup[0]
        elif lookup[2] == "L" and lookup[0] > alpha:
            alpha = lookup[0]
        elif lookup[2] == "U" and lookup[0] < beta:
            beta = lookup[0]

        if alpha >= beta:
            return lookup[0]

    if depth == 0 or isGameOver(node):
        return color * valuateState(node)

    bestValue = -float('inf')

    debug = False
    children = generateAllMoves(True if color == 1 else False, node)
    if debug: input(str(depth) + ": " + str(node) + " => children " + str(len(children)))
    for i, child in enumerate(children):
        moveHistoryNew = list(moveHistory)
        moveHistoryNew.append(child)
        result = -alphaBetaSearch(moveHistoryNew, depth - 1, -beta, -alpha, -color, maxPlayerIsOne, debugOutput + ">" + str(i))
        if debug: input(str(depth) + ": " + str(i) + ": " + debugOutput + ": " + str(node) + " => " + str(child) + " == " + str(result) + " best " + str(bestValue))
        if not bestMove or result > bestValue:
            bestValue = result
            bestMove = [moveHistoryNew]

        if result > alpha:
            alpha = result

        if result == bestValue and depth == 1:
            bestMove.append(moveHistoryNew)

        if alpha >= beta:
            break

    if debug: print("Completed depth", depth, "best value and move", bestValue, bestMove)

    if bestValue <= _alpha:
        aType = "U"
    elif bestValue >= beta:
        aType = "L"
    else:
        aType = "E"

    _alphaBetaTransposition[node] = (bestValue, depth, aType)

    return bestValue

def alphaBetaMain():
    #initial_position = (2, 0, 3, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0)
    #initial_position = (6, 0b00000001|0b01000000|0b10000000, 3, 0, 2, 2, 2, 2, 0, 1, 1, 1, 0, 0, 0)
    
    initial_position = (2, 0, 3, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    #initial_position = (4, 0, 3, 0, 2, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0)
    #initial_position = (4, 0, 5, 0, 1, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0)

    #initial_position = (0, 1, 3, 0, 1, 2, 3, 1, 0, 0, 0, 0, 0, 0, 0)
    print(initial_position)
    print("answer?", alphaBetaSearch([initial_position], 3, -float('inf'), float('inf'), 1, True, "0"))
    #print("answer?", alphaBetaSearch(initial_position, 4, -float('inf'), float('inf'), -1, False, "0"))
    for i, m in enumerate(bestMove):
        for ii, n in enumerate(m):
            print (i, ii, n)

if __name__ ==  '__main__':
    is_profiling = True
    is_threading = False
    if is_threading:
        #TODO Threading
        import multiprocessing
        multiprocessing.freeze_support()
        print("THREADING is ON")

    if is_profiling:
        import cProfile, pstats, io
        pr = cProfile.Profile()
        pr.enable()

    #Build Caches
    for wcb in itertools.product(range(16), range(16), range(256)):
        _affordable_cache[wcb[0] << 12 | wcb[1] << 8 | wcb[2]] = [b for b in _buildings if b["V"] & wcb[2] != b["V"] and b["W"] <= wcb[0] and b["C"] <= wcb[1] and (("R" not in b) or (b["R"] & wcb[2] == b["R"]))]
    for p in itertools.product(range(256), range(256)):
        _lending_cache[p[0] << 8 | p[1]] = [b["V"] for b in _buildings if b["V"] & p[0] != b["V"] and b["V"] & p[1] == b["V"]]
    for b in range(256):
        _building_count_cache[b] = bin(b).count("1")

    main()
    #alphaBetaMain()

    if is_profiling:
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())