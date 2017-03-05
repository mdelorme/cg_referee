#!/usr/bin/python

# Generic referee program for Codingame bots
import sys
import os
import subprocess
import json
import shutil
import multiprocessing as mp
import numpy as np
import random
from copy import copy

seed_bank = []

# Thanks to Steven Bethard for this nice trick, found on :
# https://bytes.com/topic/python/answers/552476-why-cant-you-pickle-instancemethods
# Allows the methods of Bot and Referee to be pickled for multiprocessing
import copy_reg
import types

def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
    for cls in cls.__mro__:
        try:
            func = cls.__dict__[func_name]
            return func.__get__(obj, cls)
        except KeyError:
            pass
    return None

copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)

lock = mp.Lock()
rankings = None

class Bot(object):
    def __init__(self, name, bin_file, arguments, game_name, log_stderr=False):
        ''' Constructor for the Bot class

        Args:
          name       (string): Name of te bot
          bin_file   (string): Path to the binary corresponding to the bot
          game_name  (string): Name of the game
          log_stderr (bool):   Shall we log stderr to a file ?
        '''
        #print(' - Creating bot {}. Command line : {} {}'.format(name, bin_file, ' '.join(arguments)))
        self.name       = name        
        self.game_name  = game_name
        self.arguments  = arguments
        self.bin_file   = bin_file    
        self.log_stderr = log_stderr  
        self.stderr_f   = None        
        self.process    = None
        self.stdin      = None
        self.stdout     = None

    def start(self, log_dir):
        ''' Starts the bot process and open descriptors to log the error stream if necessary
        
        Args:
          run (int): The id of the current run, to store the logs in the right subdir
        '''
        if self.log_stderr:
            self.stderr_f = open(log_dir + self.name + '.err', 'w')
        else:
            self.stderr_f = subprocess.PIPE # We pipe so nothing appears on screen

        self.process = subprocess.Popen([self.bin_file] + self.arguments, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.stderr_f)

        # Redirecting handles
        self.stdin  = self.process.stdin
        self.stdout = self.process.stdout

    def stop(self):
        ''' Stops the process running the bot. '''
        self.process.kill()
        if self.log_stderr:
            self.stderr_f.close()


class Referee(object):
    def __init__(self, param_file):
        ''' Constructor for the Referee class
        
        Args:
          param_file (string): Path to the JSON file holding the parameters of the game
        '''
        global seed_bank
        
        # Reading the JSON-param file
        f_in = open(param_file, 'r')
        data_s = f_in.read()
        config = json.loads(data_s)
        f_in.close()

        print(' - Reading parameter file : {}'.format(param_file))

        # Distributing the values over dictionaries
        self.game_dict = config['Game']
        self.bots_list = config['Bots']
        self.settings  = config['Settings']

        self.game_name = self.game_dict['Name']
        print(' - Refering for game : {}'.format(self.game_name))

        # We make sure the necessary subfolders exist
        if not os.path.exists('runs'):
            os.mkdir('runs')

        if not os.path.exists('runs/' + self.game_name):
            os.mkdir('runs/' + self.game_name)

        # Are we logging the results ?
        if self.settings['Log scores']:
            self.score_log = open('runs/' + self.game_name + '/scores.log', 'w')
        else:
            self.score_log = None

        self.runs     = int(self.settings['Runs'])

        if "Seed" in self.settings:
            random.seed(self.settings['Seed'])
        else:
            random.seed()
            
        seed_bank = [random.randint(0, 100000) for _ in range(self.runs)]


        print('Playing games :')
        self.run()

    def init_bots(self):
        ''' Initialises bots for the run '''
        bots = []
        for bot in self.bots_list:
            b_name      = bot['Name']
            b_bin       = bot['Bin']
            b_arguments = bot['Arguments']
            stderr      = (self.settings['Log stderr'])
            bots += [Bot(b_name, b_bin, b_arguments, self.game_dict["Name"], stderr)]
        return bots

    def finalize(self):
        ''' Closing the log file descriptor '''
        if self.settings['Log stderr']:
            stderr_f.close()

    def run_game(self, run_info):
        ''' Run one session of the game
        
        Args:
          run_info (couple): A couple (int, string). The first element is the id of the run and the second
                             the path to the log.
        '''
        global lock, rankings, seed_bank
        
        ite, log_dir, seed = run_info
        print(' - Playing run {}'.format(ite+1))
        # Creating the program process
        game_bin   = self.game_dict['Game bin']

        args = copy(self.game_dict['Arguments'])
        for i, arg in enumerate(args):
            if arg == '$seed':
                args[i] = str(seed)
        
        start_list = [game_bin] + args
        
        if self.settings['Log stderr']:
            stderr_f = open(log_dir + self.game_dict['Name'] + '.log', 'w')
        else:
            stderr_f = subprocess.PIPE # We pipe so we don't get anything on the screen
            
        game_proc = subprocess.Popen(start_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=stderr_f)

        # Creating the bots and starting them
        bots = self.init_bots()
        for bot in bots:
            bot.start(log_dir)

        finished = False
        cur_bot = 0
        try:
            while not finished:            
                # Getting the exec code from the eval code :
                exec_code = int(game_proc.stdout.readline())
                # Behaviour depending on the code :
                # < 0 : The game is finished and the bots are ranked in the next line
                # = 0 : The current bot is not active anymore
                # > 0 : The current bot is active and the system is providing exec_code lines to feed it
                if exec_code < 0:
                    rank_str = game_proc.stdout.readline().strip()
                    if rank_str == 'tied':
                        ranking = 'tied'
                    else:
                        ranking = [int(x) for x in rank_str.split(' ')]
                    finished = True
                elif exec_code > 0:
                    # Sending input to the bot
                    for i in range(exec_code):
                        line = game_proc.stdout.readline().strip()
                        bots[cur_bot].stdin.write(line+'\n')

                    # Reading output
                    line = bots[cur_bot].stdout.readline().strip()
                    game_proc.stdin.write(line+'\n')

                # Next bot
                cur_bot = (cur_bot + 1) % len(bots)

            # Once we have finished, we display the ranking
        
            s = '   . Ranking = '
            if ranking == 'tied':
                s += 'tied'
            else:
                s += '; '.join(bots[i].name for i in ranking)

            lock.acquire()
            # if tied : We add 1 to the first ranking of every bot
            sys.stdout.flush()
            nbots = len(bots)
            if ranking == 'tied':
                for id_bot in range(nbots):
                    rankings[id_bot * nbots] += 1
            else:
                nbots = len(ranking)
                for rank, id_bot in enumerate(ranking):
                    rankings[id_bot * nbots + rank] += 1
            lock.release()

            # Stopping the bots
            for bot in bots:
                bot.stop()
        except:
            print('Error while running run {}'.format(ite+1))

    def run(self):
        ''' Runs the whole session of games and records the logs everything in subdirectories'''

        # Creating the Pool of tasks
        runs = []
        nbots = len(self.bots_list)
        global rankings
        rankings = mp.Array('f', [0]*(nbots*nbots))
        
        for run in range(self.runs):
            log_dir = ''
            if self.settings['Log stderr']:
                # Clearing path if necessary, making sure everything is empty
                log_dir = 'runs/' + self.game_name + '/run_{:03d}'.format(run+1) + '/'
                if os.path.exists(log_dir):
                    shutil.rmtree(log_dir)    
                os.mkdir(log_dir)
            runs += [(run, log_dir, seed_bank.pop())] 

        # If mono-threaded then run everything in order
        nthreads = self.settings['Threads']
        if nthreads == 1:
            for run_info in runs:
                self.run_game(run_info)
        else:
            pool = mp.Pool(nthreads)
            pool.map(self.run_game, runs)

        # Writing the rankings to a file
        if self.settings['Log scores']:
            score_log = open('runs/' + self.game_name + '/scores.log', 'w')
            for bot in range(nbots):
                s = ''
                for i in range(nbots):
                    s += '{:.2f}'.format(rankings[bot * nbots + i] / self.settings['Runs']) + '\t'
                    
                score_log.write(s + '\n')
                score_log.flush()
                
            score_log.close()

        # Printing the stats for every game :
        print('Statistics (in percents) :')
        s = '{:<15}'.format('Bot name')
        for bot in range(nbots):
            s += 'Rank {}\t'.format(bot + 1)
        print(s)

        for bot in range(nbots):
            s = '{:<15}\t'.format(self.bots_list[bot]['Name'])
            for i in range(nbots):
                rankings[bot * nbots + i] *= 100.0 / self.settings['Runs']
                s += '{:.2f}'.format(rankings[bot * nbots + i]) + '\t'
            print(s)

            
            
        


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('USAGE : {} [FILE]'.format(sys.argv[0]))
        print('  Generic referee for CG Bots.')
        print('  You must provide a json file as configuration input for the program')
        exit(0)
        
    print('==============================================')
    print('================= CG Referee =================')
    print('')
    print('')
    print('Running the game :')
    r = Referee(sys.argv[1])
    
