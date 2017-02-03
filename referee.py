#!/usr/bin/python

# Generic referee program for Codingame bots
import sys
import os
import subprocess
import json
import shutil

class Bot:
    def __init__(self, name, bin_file, arguments, game_name, log_stderr=False):
        ''' Constructor for the Bot class

        Args:
          name       (string): Name of te bot
          bin_file   (string): Path to the binary corresponding to the bot
          game_name  (string): Name of the game
          log_stderr (bool):   Shall we log stderr to a file ?
        '''
        print(' - Creating bot {}. Command line : {} {}'.format(name, bin_file, ' '.join(arguments)))
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


class Referee:
    def __init__(self, param_file):
        ''' Constructor for the Referee class
        
        Args:
          param_file (string): Path to the JSON file holding the parameters of the game
        '''
        
        # Basic init
        self.stderr_f = None
        
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

        # Are we 
        self.runs = int(self.settings['Runs'])

        # Bots initialization
        self.bots = []
        self.init_bots()

    def init_bots(self):
        ''' Initialises bots for the run '''
        for bot in self.bots_list:
            b_name      = bot['Name']
            b_bin       = bot['Bin']
            b_arguments = bot['Arguments']
            stderr      = (self.settings['Log stderr'])
            self.bots += [Bot(b_name, b_bin, b_arguments, self.game_dict["Name"], stderr)]

    def finalize(self):
        ''' Closing the log file descriptor '''
        if self.settings['Log stderr']:
            self.stderr_f.close()

    def run_game(self, log_dir):
        ''' Run one session of the game
        
        Args:
          log_dir (string): Optional parameter stating where the bots and the game should log their stderr
        '''
        # Creating the program process
        game_bin   = self.game_dict['Game bin']
        start_list = [game_bin] + self.game_dict['Arguments']

        if self.settings['Log stderr']:
            self.stderr_f = open(log_dir + game_bin + '.log', 'w')
        else:
            self.stderr_f = subprocess.PIPE # We pipe so we don't get anything on the screen
            
        game_proc = subprocess.Popen(start_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr_f)

        # Starting the bots
        for bot in self.bots:
            bot.start(log_dir)

        finished = False
        cur_bot = 0
        while not finished:            
            # Getting the exec code from the eval code :
            exec_code = int(game_proc.stdout.readline())

            # Behaviour depending on the code :
            # < 0 : The game is finished and the bots are ranked in the next line
            # = 0 : The current bot is not active anymore
            # > 0 : The current bot is active and the system is providing exec_code lines to feed it
            if exec_code < 0:
                rank_str = game_proc.stdout.readline().strip()
                ranking = [int(x) for x in rank_str.split(' ')]
                finished = True
            elif exec_code > 0:
                # Sending input to the bot
                for i in range(exec_code):
                    line = game_proc.stdout.readline()
                    self.bots[cur_bot].stdin.write(line+'\n')

                # Reading output
                line = self.bots[cur_bot].stdout.readline()
                game_proc.stdin.write(line+'\n')

            # Next bot
            cur_bot = (cur_bot + 1) % len(self.bots)

        # Once we have finished, we display the ranking
        s = '   . Ranking = ' + '; '.join(self.bots[i].name for i in ranking)
        print(s)

        if self.score_log:
            self.score_log.write(' '.join(str(i) for i in ranking) + '\n')
            self.score_log.flush()

        # Stopping the bots
        for bot in self.bots:
            bot.stop()

    def run(self):
        ''' Runs the whole session of games and records the logs everything in subdirectories'''
        for run in range(self.runs):
            log_dir = ''
            if self.settings['Log stderr']:
                # Clearing path if necessary, making sure everything is empty
                log_dir = 'runs/' + self.game_name + '/run_{:03d}'.format(run+1) + '/'
                if os.path.exists(log_dir):
                    shutil.rmtree(log_dir)
                    os.mkdir(log_dir)
            print(' - Playing run {} / {}'.format(run+1, self.runs))
            self.run_game(log_dir)
            
        


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
    print('Initializing referee :')
    r = Referee(sys.argv[1])
    print('')
    print('Running the game ...')
    r.run()
    print('Closing all descriptors')
    r.finalize()
    
