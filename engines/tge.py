import sys
import math
import random

# Helper classes
class Player:
    def __init__(self, x, y, pid, wc):
        self.x   = x
        self.y   = y
        self.pid = pid
        self.wc  = wc

class Wall:
    def __init__(self, x, y, o):
        self.x = x
        self.y = y
        self.o = o

# Base game vars
n_players = int(sys.argv[1])
walls   = []
players = []
turn = 0

# Helper vars
moves_id = {'L': 0, 'R': 1, 'U': 2, 'D': 3}
moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# Can player pid place wall w ?
def can_place_wall(pid, w):
    global walls
    
    # Invalid placement
    if w.x < 0 or w.x >= 8 or w.y < 0 or w.y >= 8:
        return False

    if players[pid].wc <= 0:
        return False

    if (w.o == 'H' and w.x == 8) or (w.o == 'V' and w.y == 8):
        return False

    # No wall => No collisions
    if len(walls) == 0:
        return True;

    # Checking collision with previous walls
    for ow in walls:
        if ow.o == 'V':
            if w.o == 'H' and w.x == ow.x-1 and w.y == ow.y+1:
                return False
            elif w.o == 'V' and w.x == ow.x and w.y >= ow.y-1 and w.y <= ow.y+1:
                return False
        else:
            if w.o == 'H' and w.y == ow.y and w.x >= ow.x-1 and w.x >= ow.x+1:
                return False
            elif w.o == 'V' and w.y == ow.y-1 and w.x == ow.x+1:
                return False

    # Checking that a player is not blocked
    walls += [w]
    result = players_blocked()
    walls.pop()

    return result

# Can player pid move in direction d ?
def can_move(x, y, d):
    global walls
    
    # Stuck by a wall
    for w in walls:
        if w.o == 'V' and d < 2 and y >= w.y and y <= w.y+1:
            if (d == 'L' and x == w.x) or (d == 'R' and x == w.x+1):
                return False
        elif w.o == 'H' and d >= 2 and x >= w.x and x <= w.x+1:
            if (d == 'U' and y == w.x) or (d == 'D' and y == w.y+1):
                return False
            
    # Out of the map ?
    if (x == 0 and d == 'L') or (x == 8 and d == 'R') or (y == 0 and d == 'U') or (y == 8 and d == 'D'):
        return False

    return True

# Is player p blocked ?
def bfs_player(p):
    # BFS
    todo = [(p.x, p.y)]
    done = set()
    finished = False
    
    while todo:
        x, y = todo.pop()
        done.add((x, y))

        # Termination ?
        if p.pid == 0 and x == 8:
            finished = True
            break
        elif p.pid == 1 and x == 0:
            finished = True
            break
        elif p.pid == 2 and y == 8:
            finished = True
            break

        # Moving from that point
        for did in moves_id.items():
            # Can't move ?
            if not can_move(x, y, did[0]):
                continue
            
            nx = x + moves[did[1]][0]
            ny = y + moves[did[1]][1]

            if (nx, ny) not in todo and (nx, ny) not in done:
                todo += [(nx, ny)]

    return finished

# Is any player blocked ?
def players_blocked():
    for p in players:
        # If deactivated, we pass
        if p.x == -1:
            continue

        # Else we check the player can finish 
        if not bfs_player(p):
            return True
        
    return False

def write_current_state(first, pid):
    global walls
    
    # How many lines to print ?
    n_lines = n_players + len(walls) + 1

    if first:
        n_lines += 1
    print(n_lines)
        
    if first:
        print('8 8 {} {}'.format(n_players, pid))

    for p in players:
        print('{} {} {}'.format(p.x, p.y, p.wc))

    print(len(walls))
    for w in walls:
        print('{} {} {}'.format(w.x, w.y, w.o))
    

# Main
if __name__ == '__main__':
    base_walls = 10 if n_players == 2 else 6

    print('Game starting, {} players in the game'.format(n_players), file=sys.stderr)
    
    # Initial position
    for i in range(n_players):
        if i == 0:
            x = 0
            y = random.randint(0, 8)
        elif i == 1:
            x = 8
            y = random.randint(0, 8)
        else:
            x = random.randint(0, 8)
            y = 0

        print('Creating player {} : ({} {} {})'.format(i, x, y, base_walls), file=sys.stderr)

        players.append(Player(x, y, i, base_walls))
    
    turn     = 0
    finished = False
    ended    = []
    dead     = []
    print('Game loop :', file=sys.stderr)
    while not finished:
        # Playing every player in turn
        for pid in range(n_players):
            # If player is dead, we go on to the next
            if players[pid].x == -1:
                print(0)
                continue
            
            # Sending turn information
            write_current_state(turn == 0, pid)

            # Reading player action
            print('- Player {}\'s turn'.format(pid), file=sys.stderr)
            action = input().split()
            print(action, len(action), file=sys.stderr)
            # Movement
            if len(action) <= 2:
                move = action[0][0]
                
                # Invalid ?
                if not can_move(players[pid].x, players[pid].y, move):
                    players[pid].x = -1
                    dead += [pid]
                    print('Player {} tried to move where they shouldn\'t have'.format(pid), file=sys.stderr)
                else:
                    dx, dy = moves[move]
                    players[pid].x += dx
                    players[pid].y += dy

                    # Finished ?
                    if (pid == 0 and x == 8) or (pid == 1 and x == 0) or (pid == 2 and y == 8):
                        players[pid].x = -1
                        ended += [pid]
                        print('Player {} reached the end, finished in position {}'.format(pid, len(ended)),
                              file=sys.stderr)

                # The game is finished ?
                if len(dead) + len(finished) == n_players - 1:
                    ranking = finished + dead[::-1]
                    print('-1')
                    print(' '.join(str(x) for x in ranking))
                    exit(0)
                    
            # Wall        
            else:
                x, y = int(action[0]), int(action[1])
                wall = Wall(x, y, action[2])

                if not can_place_wall(pid, wall):
                    players[pid].x = -1
                    dead += [pid]
                    print('Player {} tried to place a wall where they shouldn\'t have'.format(pid), file=sys.stderr)
                else:
                    walls += [wall]
                    players[pid].wc -= 1

            
                
                
            
