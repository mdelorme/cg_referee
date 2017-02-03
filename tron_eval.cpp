// Evaluation program for 
#include <iostream>
#include <time.h>
#include <stdlib.h>

#define WIDTH       30
#define HEIGHT      20
#define MAX_PLAYERS 4

int main(int argc, char** argv) {
  srand(time(NULL));
  
  int n_players = atoi(argv[1]);

  // Initial positions
  int x0[MAX_PLAYERS], y0[MAX_PLAYERS];
  for (int i=0; i < n_players; ++i) {
    bool valid = true;
    do {
      x0[i] = int((float)rand() / RAND_MAX * WIDTH);
      y0[i] = int((float)rand() / RAND_MAX * HEIGHT);

      for(int j=0; j < i; ++j) {
	if (x0[j] == x0[i] && y0[j] == y0[i]) {
	  valid = false;
	  break;
	}
      }
    }
    while (!valid);
    std::cerr << "Initial position for player " << i << " : " << x0[i] << " " << y0[i] << std::endl;
  }

  // Sending the initial positions
  bool finished = false;
  bool alive[MAX_PLAYERS] = {true, true, true, true};
  int dead_order[MAX_PLAYERS];
  int n_dead = 0;
  
  // The map -> All the positions are ok at first
  int map[HEIGHT][WIDTH];
  for (int i=0; i < HEIGHT; ++i) {
    for (int j=0; j < WIDTH; ++j)
      map[i][j] = 0;
  }

  int x[MAX_PLAYERS], y[MAX_PLAYERS];
  for (int i=0; i < n_players; ++i) {
    x[i] = x0[i];
    y[i] = y0[i];
    map[y[i]][x[i]] = false;
  }

  int cur_player = 0;
  // Every loop the server waits for a code C
  // If C > 0, the player is alive and is being sent C lines of input
  // If C == 0, the player is dead.
  // If C == -1, the game is finished, and the ranking of the players is given on the next line
  while (!finished) {
    std::cerr << "Current player : " << cur_player << std::endl;
    // Is current player active
    if (!alive[cur_player]) {
      std::cout << 0 << std::endl; // 0 lines to send, the player is dead
    }
    else {
      // How many lines are we expecting and if current player is active
      std::cout << 1 + n_players << std::endl;
    
      // Number of players and current player
      std::cout << n_players << " " << cur_player << std::endl;

      // Players info
      for (int i=0; i < n_players; ++i) {
	if (!alive[i])
	  std::cout << "-1 -1 -1 -1" << std::endl;
	else
	  std::cout << x0[i] << " " << y0[i] << " " << x[i] << " " << y[i] << std::endl;
      }

      // Now waiting for the next move
      std::string move;
      std::cin >> move;
      std::cerr << "Player " << cur_player << " moving : " << move << std::endl;

      // Moving the cycle
      if (move == "RIGHT")
	x[cur_player]++;
      else if (move == "LEFT")
	x[cur_player]--;
      else if (move == "UP")
	y[cur_player]--;
      else if (move == "DOWN")
	y[cur_player]++;

      int ci, cj;
      cj = x[cur_player];
      ci = y[cur_player];

      // Checking if the cycle is dead
      if (x[cur_player] < 0 || x[cur_player] >= WIDTH || y[cur_player] < 0
       || y[cur_player] >= HEIGHT || map[ci][cj] != 0) {
	alive[cur_player] = false;
	x[cur_player] = -1;
	y[cur_player] = -1;

	// Cleaning up the map
	for (int i=0; i < HEIGHT; ++i)
	  for (int j=0; j < WIDTH; ++j)
	    if (map[i][j] == cur_player + 1)
	      map[i][j] = 0;

	// Storing the information for the rank
	dead_order[n_dead] = cur_player;
	n_dead++;

	std::cerr << "Player " << cur_player << " dies ! " << n_players - n_dead
		  << " players still alive." << std::endl;

	// Only one player alive ? We exit
	if (n_dead == n_players-1) {
	  std::cerr << "Only one player alive, end of the game" << std::endl;
	  std::cout << "-1" << std::endl;

	  // Finding which player is still alive
	  for(int i=0; i < MAX_PLAYERS; ++i) {
	    if (alive[i]) {
	      std::cout << i << " ";
	      std::cerr << "Ranking : " << i+1;
	      break;
	    }
	  }

	  // Giving the order for the rest
	  for (int i=n_players-2; i>=0; --i) {
	    std::cout << dead_order[i] << " ";
	    std::cerr << "; " << dead_order[i];
	  }
	  std::cout << std::endl;
	  std::cerr << std::endl;
	  return 0;
	}
	
      }
      else
	map[ci][cj] = cur_player + 1;
    }

    // Next player
    cur_player = (cur_player + 1) % n_players;
  }

  return 0;
}
