"""
Frontend Demo - Example of using the new OOP display architecture

This demonstrates how to use the refactored frontend system.
"""

from backend_adapter import WorldBackendAdapter
from backend import AI_System, world_system
from frontend.game_display import GameDisplay


def main():
    """Run the game with the new architecture."""
    # Initialize backend
    if world_system is None:
        print("Error: World system not initialized")
        return
    
    # Create backend adapter
    backend_adapter = WorldBackendAdapter(world_system)
    
    # Create and run the game display
    game = GameDisplay(backend_adapter)
    game.run()


if __name__ == "__main__":
    main()