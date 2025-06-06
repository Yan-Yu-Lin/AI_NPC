"""
DialogManager - Manages dialog windows

This class handles save dialogs, NPC selection, history display, etc.
"""

import pygame
from typing import Optional, Callable, List

from interfaces import BackendAPI


class DialogManager:
    """
    Manages modal dialog windows.
    
    This includes:
    1. Save dialog
    2. NPC selection dialog
    3. History display dialog
    4. Text input dialog
    """
    
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Initialize the dialog manager.
        
        Args:
            screen: Pygame surface
            font: Font for dialog text
        """
        self.screen = screen
        self.font = font
        
        # Active dialog state
        self.active_dialog = None
        self.dialog_result = None
        
        # Visual settings
        self.bg_color = (20, 20, 20)
        self.dialog_color = (50, 50, 50)
        self.border_color = (200, 200, 200)
        self.text_color = (255, 255, 255)
        self.selection_color = (100, 100, 200)
    
    def has_active_dialog(self) -> bool:
        """Check if a dialog is currently active."""
        return self.active_dialog is not None
    
    def render_active_dialog(self):
        """Render the currently active dialog if any."""
        if self.active_dialog:
            # Render semi-transparent background
            overlay = pygame.Surface(self.screen.get_size())
            overlay.set_alpha(128)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            # Render the dialog
            self.active_dialog()
    
    def handle_key_event(self, event: pygame.event.Event):
        """Handle keyboard events for active dialog."""
        # Dialog-specific key handling
        pass
    
    def handle_mouse_event(self, event: pygame.event.Event):
        """Handle mouse events for active dialog."""
        # Dialog-specific mouse handling
        pass
    
    def show_save_dialog(self):
        """Show the save world dialog."""
        self.active_dialog = self._render_save_dialog
    
    def show_npc_selection_dialog(self):
        """Show the NPC selection dialog."""
        self.active_dialog = self._render_npc_selection
    
    def show_history_dialog(self, npc_id: str):
        """Show the history dialog for an NPC."""
        self.active_dialog = lambda: self._render_history(npc_id)
    
    def show_text_input_dialog(self, prompt: str, callback: Callable[[str], None],
                              default_text: str = ""):
        """Show a text input dialog."""
        self.active_dialog = lambda: self._render_text_input(prompt, callback, default_text)
    
    def close_dialog(self):
        """Close the currently active dialog."""
        self.active_dialog = None
        self.dialog_result = None
    
    def _render_save_dialog(self):
        """Render save dialog implementation."""
        # Placeholder - would implement full save dialog
        dialog_rect = pygame.Rect(200, 150, 400, 300)
        pygame.draw.rect(self.screen, self.dialog_color, dialog_rect)
        pygame.draw.rect(self.screen, self.border_color, dialog_rect, 2)
        
        title = self.font.render("Save World", True, self.text_color)
        title_rect = title.get_rect()
        title_rect.centerx = dialog_rect.centerx
        title_rect.top = dialog_rect.top + 20
        self.screen.blit(title, title_rect)
    
    def _render_npc_selection(self):
        """Render NPC selection dialog implementation."""
        # Placeholder
        pass
    
    def _render_history(self, npc_id: str):
        """Render history dialog implementation."""
        # Placeholder
        pass
    
    def _render_text_input(self, prompt: str, callback: Callable[[str], None],
                          default_text: str):
        """Render text input dialog implementation."""
        # Placeholder
        pass