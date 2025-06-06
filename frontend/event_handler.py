"""
EventHandler - Centralized event processing

This class handles all user input events and routes them to appropriate components.
"""

from typing import List, Optional
import pygame


class EventHandler:
    """
    Centralized event handler for all user input.
    
    This class processes:
    1. Pygame events (keyboard, mouse, window)
    2. Terminal commands
    3. UI interactions
    """
    
    def __init__(self, game_display, ui_manager, dialog_manager, 
                 terminal_interface, ai_processor):
        """
        Initialize the event handler.
        
        Args:
            game_display: Main game display controller
            ui_manager: UI manager instance
            dialog_manager: Dialog manager instance
            terminal_interface: Terminal interface instance
            ai_processor: AI processor instance
        """
        self.game_display = game_display
        self.ui_manager = ui_manager
        self.dialog_manager = dialog_manager
        self.terminal_interface = terminal_interface
        self.ai_processor = ai_processor
        
        # Input state
        self.keys_pressed = set()
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        
    def process_events(self, events: List[pygame.event.Event]) -> bool:
        """
        Process all pygame events.
        
        Args:
            events: List of pygame events
            
        Returns:
            True to continue running, False to quit
        """
        running = True
        
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.VIDEORESIZE:
                self._handle_resize(event)
            
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
            
            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mousedown(event)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouseup(event)
            
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mousemotion(event)
        
        # Process terminal commands
        self._process_terminal_commands()
        
        return running
    
    def _handle_resize(self, event: pygame.event.Event):
        """Handle window resize event."""
        # Window resize is handled automatically by pygame
        # Could add custom resize logic here if needed
        pass
    
    def _handle_keydown(self, event: pygame.event.Event):
        """Handle key press event."""
        self.keys_pressed.add(event.key)
        
        # Check if a dialog is active
        if self.dialog_manager.has_active_dialog():
            self.dialog_manager.handle_key_event(event)
            return
        
        # Global hotkeys
        if event.key == pygame.K_ESCAPE:
            # Open menu or perform escape action
            pass
        
        elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
            # Ctrl+S: Open save dialog
            self.dialog_manager.show_save_dialog()
        
        elif event.key == pygame.K_h:
            # H: Show history for active NPC
            if self.game_display.active_npc_id:
                self.dialog_manager.show_history_dialog(self.game_display.active_npc_id)
        
        elif event.key == pygame.K_n:
            # N: Show NPC selection dialog
            self.dialog_manager.show_npc_selection_dialog()
        
        elif event.key == pygame.K_SPACE:
            # Space: Trigger AI for active NPC
            if self.game_display.active_npc_id:
                self.ai_processor.process_npc(self.game_display.active_npc_id)
        
        elif event.key == pygame.K_t:
            # T: Open text input for talking to NPC
            if self.game_display.active_npc_id:
                self.dialog_manager.show_text_input_dialog(
                    "Talk to NPC:",
                    callback=self._handle_npc_talk
                )
    
    def _handle_keyup(self, event: pygame.event.Event):
        """Handle key release event."""
        if event.key in self.keys_pressed:
            self.keys_pressed.remove(event.key)
    
    def _handle_mousedown(self, event: pygame.event.Event):
        """Handle mouse button press event."""
        self.mouse_buttons[event.button - 1] = True
        
        # Check if clicking on UI elements
        if self.ui_manager.handle_click(event.pos):
            return
        
        # Check if a dialog is active
        if self.dialog_manager.has_active_dialog():
            self.dialog_manager.handle_mouse_event(event)
            return
        
        # Handle world clicks (e.g., selecting NPCs or items)
        self._handle_world_click(event.pos)
    
    def _handle_mouseup(self, event: pygame.event.Event):
        """Handle mouse button release event."""
        if event.button <= 3:
            self.mouse_buttons[event.button - 1] = False
    
    def _handle_mousemotion(self, event: pygame.event.Event):
        """Handle mouse motion event."""
        self.mouse_pos = event.pos
        
        # Update UI hover states
        self.ui_manager.update_hover(event.pos)
    
    def _handle_world_click(self, pos: tuple):
        """
        Handle clicks on the game world.
        
        Args:
            pos: Mouse position
        """
        # Convert screen coordinates to world coordinates
        # Check if clicking on an NPC
        # Check if clicking on an item
        # etc.
        pass
    
    def _handle_npc_talk(self, text: str):
        """
        Handle talking to an NPC.
        
        Args:
            text: User input text
        """
        if self.game_display.active_npc_id and text:
            self.ai_processor.process_npc_with_input(
                self.game_display.active_npc_id, 
                text
            )
    
    def _process_terminal_commands(self):
        """Process any pending terminal commands."""
        command = self.terminal_interface.get_pending_command()
        
        if command:
            parts = command.strip().split()
            if not parts:
                return
            
            cmd = parts[0].lower()
            
            if cmd == 'quit':
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            
            elif cmd == 'p':
                # Print history command
                if len(parts) > 1:
                    npc_name = ' '.join(parts[1:])
                    self.terminal_interface.print_npc_history(npc_name)
                else:
                    # Print active NPC history
                    if self.game_display.active_npc_id:
                        self.terminal_interface.print_npc_history(
                            self.game_display.active_npc_id
                        )
            
            elif cmd == 'save':
                # Save command
                if len(parts) > 1:
                    filename = parts[1]
                    self.game_display.backend_api.save_world(filename)
                else:
                    self.dialog_manager.show_save_dialog()
            
            elif cmd == 'help':
                # Show help
                self.terminal_interface.print_help()