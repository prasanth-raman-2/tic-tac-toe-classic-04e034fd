from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DRAW = "draw"

class PlayerSymbol(str, Enum):
    X = "X"
    O = "O"

# Database Model
class GameDB(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    player1_id = Column(Integer, ForeignKey("users.id"))
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    current_player_id = Column(Integer, ForeignKey("users.id"))
    board = Column(JSON, default=[[""]*3 for _ in range(3)])
    status = Column(String, default=GameStatus.WAITING.value)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player1 = relationship("UserDB", foreign_keys=[player1_id])
    player2 = relationship("UserDB", foreign_keys=[player2_id])
    winner = relationship("UserDB", foreign_keys=[winner_id])

# Pydantic Schemas
class GameBase(BaseModel):
    player1_id: int
    player2_id: Optional[int] = None
    current_player_id: int
    board: List[List[str]] = Field(default_factory=lambda: [[""]*3 for _ in range(3)])
    status: GameStatus = GameStatus.WAITING

class GameCreate(GameBase):
    pass

class GameUpdate(BaseModel):
    player2_id: Optional[int] = None
    current_player_id: Optional[int] = None
    board: Optional[List[List[str]]] = None
    status: Optional[GameStatus] = None
    winner_id: Optional[int] = None

class GameResponse(GameBase):
    id: int
    winner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Move(BaseModel):
    row: int = Field(..., ge=0, lt=3)
    col: int = Field(..., ge=0, lt=3)

# Game Logic
def validate_move(board: List[List[str]], move: Move) -> bool:
    """
    Validate if the move is legal
    """
    return board[move.row][move.col] == ""

def make_move(board: List[List[str]], move: Move, symbol: PlayerSymbol) -> List[List[str]]:
    """
    Make a move on the board
    """
    new_board = [row.copy() for row in board]
    new_board[move.row][move.col] = symbol
    return new_board

def check_winner(board: List[List[str]]) -> Optional[str]:
    """
    Check if there's a winner
    Returns the winning symbol (X or O) or None if no winner
    """
    # Check rows
    for row in board:
        if row[0] and row[0] == row[1] == row[2]:
            return row[0]
    
    # Check columns
    for col in range(3):
        if board[0][col] and board[0][col] == board[1][col] == board[2][col]:
            return board[0][col]
    
    # Check diagonals
    if board[0][0] and board[0][0] == board[1][1] == board[2][2]:
        return board[0][0]
    if board[0][2] and board[0][2] == board[1][1] == board[2][0]:
        return board[0][2]
    
    return None

def is_board_full(board: List[List[str]]) -> bool:
    """
    Check if the board is full (draw)
    """
    return all(cell != "" for row in board for cell in row)

def get_game_status(board: List[List[str]]) -> Tuple[GameStatus, Optional[str]]:
    """
    Get the current game status and winner
    Returns (status, winner_symbol)
    """
    winner = check_winner(board)
    if winner:
        return GameStatus.COMPLETED, winner
    elif is_board_full(board):
        return GameStatus.DRAW, None
    else:
        return GameStatus.IN_PROGRESS, None
