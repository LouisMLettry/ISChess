
<p align="center"><img src="Data/assets/icon.png" alt="logo" width="96"></p>
<p align="center">
<img src="Data/assets/p.png" alt="pawn">
<img src="Data/assets/n.png" alt="knight">
<img src="Data/assets/b.png" alt="bishop">
<img src="Data/assets/r.png" alt="rook">
<img src="Data/assets/q.png" alt="queen">
<img src="Data/assets/k.png" alt="king">
</p>

# ISChess
This is the repository containing the GUI supporting the ISChess project of the algorithmic lecture.

The project's aim is to program a chess playing bot by adding a new file in the [`Bots/`](Bots) folder and registering it to the global bot list as shown in [`BaseChessBot.py`](Bots/BaseChessBot.py).
This file will produce your final handout.

You are more than welcome to modify these files.
However, be careful that the final evaluation will be carried out using the version of the software presented in this repository.

If you would like to share modifications to improve the GUI, don't hesitate to submit a change request.

# Structure
- [`Data/`](Data): neutral assets location 
   - [`maps/`](Data/maps): example boards which can be loaded
   - [`assets/`](Data/assets): location of needed images and other assets
   - [`tournaments/`](Data/tournaments): example tournaments can be loaded
   - [`UI.ui`](Data/UI.ui): GUI file from QtDesigner
- [`Bots/`](Bots): contains the global list of bots ([`ChessBotList.py`](Bots/ChessBotList.py)) as well as an example pawn moving bot ([`BaseChessBot.py`](Bots/BaseChessBot.py))
- [`main.py`](main.py): Main execution point
- [`ParallelPlayer.py`](ParallelPlayer.py): Threaded wrapper for bot execution
- [`ChessRules.py`](ChessRules.py): Basic custom chess rules and verification
- [`ChessArena.py`](ChessArena.py): Primary GUI
- [`Tournament.py`](Tournament.py): Tournament GUI
- [`TournamentManager.py`](TournamentManager.py): Tournament algorithms
- other internal classes to run the game

# Libraries
This software requires python 3.10+ together with two libraries:
- Numpy
- PyQt6

![ISC Logo inline (preferred)](https://github.com/LouisMLettry/ISChess/assets/114392644/799c6157-3088-4b0b-be09-ac805a2bd024)
