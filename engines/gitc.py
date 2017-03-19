import random
import sys
import math
import numpy as np

min_factory_count = 7
max_factory_count = 15
min_prod_rate = 0
max_prod_rate = 3
min_tot_prod_rate = 4
min_init_units = 15
max_init_units = 30
extra_space_between_fac = 300
cost_increase_prod = 10
damage_duration = 5
nbombs = [2, 0, 2]
scores = [0, 0, 0]

stfu = False
def log(x):
    if not stfu:
        sys.stderr.write(x+'\n')

if len(sys.argv) > 1:
    seed = sys.argv[1]
else:
    seed = 123456789
    
random.seed(seed)


class Factory(object):
    def __init__(self):
        self.fid         = -1
        self.x           = 0
        self.y           = 0.0
        self.owner       = 0
        self.ncyborgs    = 0
        self.prod        = 0
        self.blocked_for = 0
        self.adj         = {}

        self.attackers   = [0, 0, 0]
        
class Troop(object):
    def __init__(self):
        self.owner    = 0
        self.f_from   = -1
        self.f_to     = -1
        self.ncyborgs = 0
        self.eta      = 0

class Bomb(object):
    def __init__(self):
        self.owner = 0
        self.f_from = -1
        self.f_to   = -1
        self.timer  = -1

factories  = []
dist_table = []
bombs      = []
troops     = []

def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)
        
def init():
    global factories
    global dist_table
    log('Initialising game')
    log(' - Random seed = {}'.format(seed))

    factory_count = random.randint(min_factory_count, max_factory_count)
    if factory_count % 2 == 0:
        factory_count += 1

    factory_radius = 600 if factory_count > 10 else 700
    min_space = 2 * (factory_radius + extra_space_between_fac)
    
    factories = [Factory() for _ in range(factory_count)]

    log(' - n_factories = {}'.format(factory_count))
    
    # Adding one at the center
    factories[0].fid   = 0
    factories[0].x     = 8000
    factories[0].y     = 3250
    factories[0].prod  = 0
    factories[0].units = 0


    total_prod = 0
    i = 1
    while i < factory_count:
        x = random.randint(0, 8000 - 2 * factory_radius) + factory_radius + extra_space_between_fac
        y = random.randint(0, 6500 - 2 * factory_radius) + factory_radius + extra_space_between_fac

        valid = True
        for f in factories[:i]:
            if dist(f.x, f.y, x, y) < min_space:
                valid = False
                break

        
        if valid:
            prod_rate = random.randint(min_prod_rate, max_prod_rate)

            if i == 1:
                init_unit = random.randint(min_init_units, max_init_units)
            else:
                init_unit = random.randint(0, 5*prod_rate)

            factories[i].fid      = i
            factories[i].x        = x
            factories[i].y        = y
            factories[i].ncyborgs = init_unit
            factories[i].prod     = prod_rate

            factories[i+1].fid      = i+1
            factories[i+1].x        = 16000 - x
            factories[i+1].y        = 6500  - y
            factories[i+1].ncyborgs = init_unit
            factories[i+1].prod     = prod_rate

            if i == 1:
                factories[i].owner   = 1
                factories[i+1].owner = -1
            else:
                factories[i].owner   = 0
                factories[i+1].owner = 0
            

            total_prod += 2 * prod_rate
            i += 2

    # Balancing the total production
    i = 1
    while total_prod < min_prod_rate:
        if factories[i].prod < max_prod_rate:
            factories[i].prod += 1
            total_prod += 1
            
        i += 1

    # Computing the distances
    dist_table = np.zeros((factory_count, factory_count), dtype=np.int8)
    for f1 in factories[:-1]:
        for f2 in factories[f1.fid+1:]:
            d = int(round((dist(f1.x, f1.y, f2.x, f2.y) - 2*factory_radius) / 800.0))
            dist_table[f1.fid, f2.fid] = d
            dist_table[f2.fid, f1.fid] = d

    # Debug info
    log(' - Distance table :')
    for i1 in range(factory_count):
        s = '    '
        for i2 in range(factory_count):
            s += '{:>3d}'.format(dist_table[i1, i2])
        log(s)

    log(' - Factories :')
    log('\t\t#ID\tOwner\tProd\tUnits')
    for f in factories:
        log('\t\t{}\t{}\t{}\t{}'.format(f.fid, f.owner, f.prod, f.ncyborgs))


def turn_owner(turn, owner):
    if owner == 0:
        return 0
    
    if turn % 2 == 0:
        return owner
    else:
        return 1 if owner == -1 else -1
    
def send_turn_info(turn):
    lines = []

    # If first turn, we send all the info of the map to the player
    if turn <= 1:
        N      = len(factories)
        Nlinks = 0
        
        lines += [str(N)]

        links = []
        for i in range(N-1):
            for j in range(i+1, N):
                links += ['{} {} {}'.format(i, j, dist_table[i, j])]

        lines += [str(len(links))]
        lines += links

    lines += [str(len(factories) + len(troops) + len(bombs))]

    # Then we send factories
    for f in factories:
        owner = turn_owner(turn, f.owner)
        s = '{} FACTORY {} {} {} {} -1'.format(f.fid, owner, f.ncyborgs, f.prod, f.blocked_for)
        lines += [s]

    # Then we send troops
    eid = len(factories)
    for t in troops:
        owner = turn_owner(turn, t.owner)

        s = '{} TROOP {} {} {} {} {}'.format(eid, owner, t.f_from, t.f_to, t.ncyborgs, t.eta)
        lines += [s]
        eid += 1

    # Then we send the bombs
    for b in bombs:
        owner = turn_owner(turn, b.owner)
        f_to = b.f_to if owner == 1 else -1
        timer = b.timer if owner == 1 else -1
        
        s = '{} BOMB {} {} {} {} -1'.format(eid, owner, b.f_from, f_to, timer)
        lines += [s]
        eid += 1

    print(len(lines))
    for l in lines:
        print(l)
    sys.stdout.flush()

def end_game(ranking, tied=False):
    print(-1)
    res = ranking
    if tied:
        res = 'tied'
    log('Game ending with ranking : ' + res)
    print(res)
    exit(0)

def execute_orders(pid, actions):
    global factories, bombs, troops
    
    actions = [action.strip() for action in actions.split(';')]
    for i in range(len(actions)):
        if actions[i].startswith('BOMB'):
            actions[i] = '0_'+actions[i]
        elif actions[i].startswith('MOVE'):
            actions[i] = '1_'+actions[i]
        elif actions[i].startswith('INC'):
            actions[i] = '2_'+actions[i]
            
    bomb_paths = []
    
    actions.sort() # We sort to get the order of the operations right
    for a_token in actions:
        action = a_token.split(' ')

        atype = action[0]

        if atype == '0_BOMB':
            f_from = int(action[1])
            f_to   = int(action[2])
            valid = True

            if nbombs[pid+1] == 0:
                log('WARNING : Player {} tries to send a bomb, but no bombs left !'.format(pid))
                valid = False

            if f_from < 0 or f_from >= len(factories):
                log('Player {} : non-existent factory {}'.format(pid, f_from))
                return False

            if f_to < 0 or f_to >= len(factories):
                log('Player {} : non-existent factory {}'.format(pid, f_to))
                return False

            if f_to == f_from:
                log('Player {} : can\'t bomb the sender ! : from == to ...'.format(pid))
                return False

            if valid:
                bomb_paths += [(f_from, f_to)]

                b = Bomb()
                b.owner = pid
                b.f_from = f_from
                b.f_to   = f_to
                b.timer  = dist_table[f_from, f_to]
                
                bombs += [b]
                nbombs[pid+1] -= 1
                log('Player {} sending bomb from {} to {}'.format(pid, f_from, f_to))

            
        elif atype == '1_MOVE':
            f_from = int(action[1])
            f_to   = int(action[2])
            valid = True
            
            # Errors
            if f_from < 0 or f_from >= len(factories):
                log('Player {} : non-existent factory {}'.format(pid, f_from))
                return False

            if f_to < 0 or f_to >= len(factories):
                log('Player {} : non-existent factory {}'.format(pid, f_to))
                return False

            if f_to == f_from:
                log('Player {} : sending units : from == to ...'.format(pid))
                return False

            if factories[f_from].owner != pid:
                log('Player {} tries to move units from enemy factory {}'.format(pid, f_from))
                return False

            count  = int(action[3])

            if count < 0:
                log('Player {} tries to move {} units ...'.format(pid, count))
                return False
            
            if count <= 0 or (f_from, f_to) in bomb_paths or factories[f_from].ncyborgs <= 0:
                valid = False

            # If everything is ok, we create the troop
            if valid:

                if count > factories[f_from].ncyborgs:
                    count = factories[f_from].ncyborgs
                    log('WARNING : Player {} tries to more more units than available at factory {}. Scaled down to {}'.format(pid,
                                                                                                                              f_from,
                                                                                                                              count))
                t          = Troop()
                t.owner    = pid
                t.ncyborgs = count
                t.f_from   = f_from
                t.f_to     = f_to
                t.eta      = dist_table[f_from, f_to]

                troops += [t]
                factories[f_from].ncyborgs -= count
                log('Player {} creating new troop, {} {} {}, ETA = {}'.format(pid,
                                                                              t.f_from,
                                                                              t.f_to,
                                                                              count,
                                                                              t.eta))
            elif (f_from, f_to) in bomb_paths:
                log('WARNING : Player {} tries to send troops from bomb source {} to bomb destination {}, move cancelled'.format(pid, 
                                                                                                                                 f_from,
                                                                                                                                 f_to))
            elif count == 0:
                log('WARNING : Player {} tries to send 0 troops ! Move ignored.'.format(pid))
                
        elif atype == '2_INC':
            f_from = int(action[1])
            valid = True
            # Errors
            if f_from < 0 or f_from >= len(factories):
                log('Player {} : non-existent factory {}'.format(pid, f_from))
                return False

            if factories[f_from].owner != pid:
                log('Player {} tries to move units from enemy factory {}'.format(pid, f_from))
                return False

            if factories[f_from].ncyborgs < 10:
                log('Player {} tries to inc a factory {} with not enough robots'.format(pid, f_from))
                valid = False

            if factories[f_from].prod == 3:
                log('WARNING : Player {} tries to inc the already maxxed factory {}'.format(pid, f_from))
                valid = False

            if valid:
                factories[f_from].prod    += 1
                factories[f_from].ncyborgs -= 10

                log('Player {} increases production of factory {} to {}'.format(pid, f_from, factories[f_from].prod))
        elif atype == 'MSG':
            log('Player {} says {}'.format(pid, action))
        elif atype == 'WAIT':
            pass
        
    return True

def evolve(a1, a2):
    global troops
    global factories
    global bombs
    global scores

    for f in factories:
        f.attackers = [0, 0, 0]
    
    # 1- Moving troops and bombs
    t_to_resolve = []
    for t in troops:
        t.eta -= 1
        if t.eta == 0:
            t_to_resolve += [t]
            factories[t.f_to].attackers[t.owner+1] += t.ncyborgs

    b_to_resolve = []
    for b in bombs:
        b.timer -= 1
        if b.timer == 0:
            b_to_resolve += [b]

    # 2- Decreasing disabled countdown
    for f in factories:
        f.blocked_for = max(0, f.blocked_for-1)

    # 3- Executing orders
    r0 = execute_orders(1, a1)
    r1 = execute_orders(-1, a2)

    # Are we finished because of an error
    if not r0 and not r1:
        end_game('0 1', True)
    elif not r0:
        end_game('1 0')
    elif not r1:
        end_game('0 1')


    # 4- Production
    for f in factories:
        if f.owner != 0 and f.blocked_for == 0:
            f.ncyborgs += f.prod
        
    # 5- BATTLES
    for f in factories:
        units = min(f.attackers[0], f.attackers[2])
        f.attackers[0] -= units
        f.attackers[2] -= units

        for pid in (-1, 1):
            if f.owner == pid:
                f.ncyborgs += f.attackers[pid+1]
            else:
                if f.attackers[pid+1] > f.ncyborgs:
                    f.owner = pid
                    f.ncyborgs = f.attackers[pid+1] - f.ncyborgs
                else:
                    f.ncyborgs -= f.attackers[pid+1]
                    
    # 6- Bombs
    for b in b_to_resolve:
        f = factories[b.f_to]
        units = max(10, f.ncyborgs // 2)
        f.ncyborgs = max(0, f.ncyborgs - units)
        f.blocked_for = 5

    # 7- Cleaning
    for t in t_to_resolve:
        troops.remove(t)
    for b in b_to_resolve:
        bombs.remove(b)

    # 8- Updating score
    scores = [0, 0, 0]
    for f in factories:
        scores[f.owner+1] += f.ncyborgs
    for t in troops:
        scores[t.owner+1] += t.ncyborgs

    if scores[0] == 0:
        prod = 0
        for f in factories:
            if f.owner == -1:
                prod += f.prod

        if prod == 0:
            end_game('0 1')
    elif scores[2] == 0:
        prod = 0
        for f in factories:
            if f.owner == 1:
                prod += f.prod

        if prod == 0:
            end_game('1 0')
        
        
# Main loop
if __name__ == '__main__':
    init()
    turn = 0
    while True:
        log('\n---- Turn {}'.format(turn//2 + 1))
        log('{} troops in motion'.format(len(troops)))
        log('{} bombs in motion'.format(len(bombs)))
            
        # Sending turn info to player 1
        send_turn_info(turn)
        p1_turn = raw_input()

        log('p1 = ' + p1_turn)
        
        # Sending turn info to player 2
        send_turn_info(turn+1)        
        p2_turn = raw_input()

        log('p2 = ' + p2_turn)

        # Evolving the situation according to both players
        evolve(p1_turn, p2_turn)

        # Advancing turn info and checking for end of game
        turn += 2
        if turn > 400:
            count = [0, 0, 0]
            for f in factories:
                count[f.owner+1] += f.ncyborgs
                log(str(count))
            log('--------')
            for t in troops:
                count[t.owner+1] += t.ncyborgs
                log(str(count))

            log('Maximum turns elapsed, Scores = {} / {}'.format(count[0], count[2]))
            log('Final state of the game :')
            log('\t\t#ID\tOwner\tProd\tUnits')
            for f in factories:
                log('\t\t{}\t{}\t{}\t{}'.format(f.fid, f.owner, f.prod, f.ncyborgs))      


            if count[0] == count[2]:
                end_game('0 1', True)
            elif count[0] > count[2]:
                end_game('1 0')
            else:
                end_game('0 1')


    

    
            
    
