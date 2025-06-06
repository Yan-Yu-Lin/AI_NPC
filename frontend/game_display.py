"""
GameDisplay - Main Display Controller

This is the main controller class that coordinates all display components.
It implements the Model-View-Controller pattern where:
- Model: Backend API (AI logic)
- View: Renderers and UI components
- Controller: This class and EventHandler
"""

import pygame
from typing import Dict, Optional, Any
import sys

from interfaces import BackendAPI, WorldDisplayData
from .event_handler import EventHandler
from .renderers.space_renderer import SpaceRenderer
from .renderers.npc_renderer import NPCRenderer
from .renderers.item_renderer import ItemRenderer
from .ui.ui_manager import UIManager
from .ui.dialog_manager import DialogManager
from .ui.terminal_interface import TerminalInterface
from .utils.ai_processor import AIProcessor


class GameDisplay:
    """
    Main display controller that manages the game window and coordinates all components.
    
    This class is responsible for:
    1. Initializing pygame and all display components
    2. Running the main game loop
    3. Coordinating between different renderers and UI components
    4. Managing the connection to the backend API
    """
    
    def __init__(self, backend_api: BackendAPI, initial_window_size: tuple = (1200, 700)):
        """
        Initialize the game display controller.
        
        Args:
            backend_api: The backend API instance for accessing game data
            initial_window_size: Initial window dimensions (width, height)
        """
        self.backend_api = backend_api
        self.initial_window_size = initial_window_size
        
        # Pygame components
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.font: Optional[pygame.font.Font] = None
        self.info_font: Optional[pygame.font.Font] = None
        self.button_font: Optional[pygame.font.Font] = None
        
        # Display components
        self.renderers: Dict[str, Any] = {}
        self.event_handler: Optional[EventHandler] = None
        self.ui_manager: Optional[UIManager] = None
        self.dialog_manager: Optional[DialogManager] = None
        self.terminal_interface: Optional[TerminalInterface] = None
        self.ai_processor: Optional[AIProcessor] = None
        
        # Game state
        self.running = False
        self.active_npc_id: Optional[str] = None
        self.scale = 1.0
        self.offset = (0, 0)
        
    def initialize(self) -> bool:
        """
        Initialize pygame and all display components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize pygame
            pygame.init()
            
            # Create resizable window
            self.screen = pygame.display.set_mode(
                self.initial_window_size, 
                pygame.RESIZABLE
            )
            pygame.display.set_caption("AI NPC World Demo")
            
            # Load fonts
            self.font = pygame.font.Font("fonts/msjh.ttf", 22)
            self.info_font = pygame.font.Font("fonts/msjh.ttf", 18)
            self.button_font = pygame.font.Font("fonts/msjh.ttf", 20)
            
            # Initialize clock
            self.clock = pygame.time.Clock()
            
            # Initialize renderers
            self.renderers['space'] = SpaceRenderer(self.screen, self.font)
            self.renderers['npc'] = NPCRenderer(self.screen, self.font)
            self.renderers['item'] = ItemRenderer(self.screen, self.font)
            
            # Initialize UI components
            self.ui_manager = UIManager(self.screen, self.info_font, self.button_font)
            self.dialog_manager = DialogManager(self.screen, self.font)
            self.terminal_interface = TerminalInterface(self.backend_api)
            
            # Initialize AI processor
            self.ai_processor = AIProcessor(self.backend_api)
            
            # Initialize event handler
            self.event_handler = EventHandler(
                self,
                self.ui_manager,
                self.dialog_manager,
                self.terminal_interface,
                self.ai_processor
            )
            
            # Start terminal interface
            self.terminal_interface.start()
            
            # Get initial active NPC
            world_data = self.backend_api.get_world_display_data()
            if world_data.npcs:
                self.active_npc_id = world_data.npcs[0].id
                self.backend_api.set_active_npc(self.active_npc_id)
            
            return True
            
        except Exception as e:
            print(f"Error initializing game display: {e}")
            return False
    
    def run(self):
        """
        Run the main game loop.
        
        This method contains the main game loop that:
        1. Handles events
        2. Updates game state
        3. Renders everything
        4. Controls frame rate
        """
        if not self.initialize():
            print("Failed to initialize game display")
            return
        
        self.running = True
        
        while self.running:
            # Handle events
            self.handle_events()
            
            # Update game state
            self.update()
            
            # Render everything
            self.render()
            
            # Update display
            pygame.display.flip()
            
            # Control frame rate (60 FPS)
            self.clock.tick(60)
        
        # Cleanup
        self.cleanup()
    
    def handle_events(self):
        """Process all events through the event handler."""
        events = pygame.event.get()
        self.running = self.event_handler.process_events(events)
    
    def update(self):
        """
        Update game state.
        
        This includes:
        1. Updating NPC positions
        2. Processing AI responses
        3. Updating UI state
        """
        # Get latest world data
        world_data = self.backend_api.get_world_display_data()
        
        # Update renderers with latest data
        self.renderers['space'].update(world_data.spaces)
        self.renderers['npc'].update(world_data.npcs, self.active_npc_id)
        self.renderers['item'].update(world_data.items)
        
        # Update UI
        self.ui_manager.update(world_data)
        
        # Calculate rendering scale and offset
        self._calculate_render_params()
    
    def render(self):
        """
        Render all components in the correct order.
        
        Rendering order:
        1. Clear screen
        2. Render spaces
        3. Render items
        4. Render NPCs
        5. Render UI overlay
        """
        # Clear screen
        self.screen.fill((30, 30, 30))
        
        # Render game world (with scale and offset)
        self.renderers['space'].render(self.scale, self.offset)
        self.renderers['item'].render(self.scale, self.offset)
        self.renderers['npc'].render(self.scale, self.offset)
        
        # Render UI overlay (no scaling)
        self.ui_manager.render()
        
        # Render any active dialogs
        self.dialog_manager.render_active_dialog()
    
    def _calculate_render_params(self):
        """Calculate scale and offset for rendering based on window size."""
        # This would calculate appropriate scale and offset
        # based on world size and window size
        # For now, using default values
        self.scale = 1.0
        self.offset = (100, 100)
    
    def cleanup(self):
        """Clean up resources before exit."""
        # Stop terminal interface
        if self.terminal_interface:
            self.terminal_interface.stop()
        
        # Stop AI processor
        if self.ai_processor:
            self.ai_processor.stop()
        
        # Quit pygame
        pygame.quit()
        sys.exit()
    
    def set_active_npc(self, npc_id: str):
        """Set the active NPC for display."""
        self.active_npc_id = npc_id
        self.backend_api.set_active_npc(npc_id)