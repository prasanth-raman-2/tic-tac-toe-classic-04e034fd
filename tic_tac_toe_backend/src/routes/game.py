from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.auth.auth import get_current_user
from src.models.game import (
    GameDB, GameResponse, Move,
    PlayerSymbol, GameStatus,
    validate_move, make_move, get_game_status
)
from src.models.user import UserDB

router = APIRouter(prefix="/game", tags=["Game"])

# Dependency to get database session (same as in auth.py)
def get_db():
    # TODO: Implement database session handling
    raise NotImplementedError("Database session handling not implemented")

# PUBLIC_INTERFACE
@router.post("/create", response_model=GameResponse)
async def create_game(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Create a new game with the current user as player 1.
    
    Returns:
        GameResponse: The newly created game information
    """
    game = GameDB(
        player1_id=current_user.id,
        current_player_id=current_user.id,
        status=GameStatus.WAITING
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game

# PUBLIC_INTERFACE
@router.post("/{game_id}/join", response_model=GameResponse)
async def join_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Join an existing game as player 2.
    
    Args:
        game_id: ID of the game to join
        
    Returns:
        GameResponse: Updated game information
    """
    game = db.query(GameDB).filter(GameDB.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )
    
    if game.status != GameStatus.WAITING:
        raise HTTPException(
            status_code=400,
            detail="Game is not available to join"
        )
    
    if game.player1_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot join your own game"
        )
    
    game.player2_id = current_user.id
    game.status = GameStatus.IN_PROGRESS
    db.commit()
    db.refresh(game)
    return game

# PUBLIC_INTERFACE
@router.post("/{game_id}/move", response_model=GameResponse)
async def make_game_move(
    game_id: int,
    move: Move,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Make a move in the game.
    
    Args:
        game_id: ID of the game
        move: Row and column coordinates for the move
        
    Returns:
        GameResponse: Updated game information
    """
    game = db.query(GameDB).filter(GameDB.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )
    
    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Game is not in progress"
        )
    
    if game.current_player_id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Not your turn"
        )
    
    if not validate_move(game.board, move):
        raise HTTPException(
            status_code=400,
            detail="Invalid move"
        )
    
    # Determine player's symbol
    symbol = PlayerSymbol.X if current_user.id == game.player1_id else PlayerSymbol.O
    
    # Make the move
    game.board = make_move(game.board, move, symbol)
    
    # Check game status
    game_status, winner_symbol = get_game_status(game.board)
    game.status = game_status
    
    if game_status in [GameStatus.COMPLETED, GameStatus.DRAW]:
        if game_status == GameStatus.COMPLETED:
            game.winner_id = game.player1_id if winner_symbol == PlayerSymbol.X else game.player2_id
    else:
        # Switch current player
        game.current_player_id = game.player2_id if current_user.id == game.player1_id else game.player1_id
    
    db.commit()
    db.refresh(game)
    return game

# PUBLIC_INTERFACE
@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Get the current state of a game.
    
    Args:
        game_id: ID of the game
        
    Returns:
        GameResponse: Current game information
    """
    game = db.query(GameDB).filter(GameDB.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )
    
    if current_user.id not in [game.player1_id, game.player2_id]:
        raise HTTPException(
            status_code=403,
            detail="Not a participant in this game"
        )
    
    return game

# PUBLIC_INTERFACE
@router.get("/", response_model=List[GameResponse])
async def list_games(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    List all games where the current user is a participant.
    
    Returns:
        List[GameResponse]: List of games
    """
    games = db.query(GameDB).filter(
        (GameDB.player1_id == current_user.id) | 
        (GameDB.player2_id == current_user.id)
    ).all()
    return games
