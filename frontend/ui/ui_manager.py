"""
UIManager - Manages UI overlay elements

This class handles buttons, info panels, and other UI elements.
"""

import pygame
from typing import List, Tuple, Optional, Callable

from interfaces import WorldDisplayData


class Button:
    """Simple button class for UI."""
    
    def __init__(self, rect: pygame.Rect, text: str, callback: Callable):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.hovered = False
        self.pressed = False


class UIManager:
    """
    Manages UI overlay elements.
    
    This includes:
    1. Info panel
    2. Buttons
    3. Status indicators
    """
    
    def __init__(self, screen: pygame.Surface, info_font: pygame.font.Font,
                 button_font: pygame.font.Font):
        """
        Initialize the UI manager.
        
        Args:
            screen: Pygame surface
            info_font: Font for info text
            button_font: Font for buttons
        """
        self.screen = screen
        self.info_font = info_font
        self.button_font = button_font
        
        # UI elements
        self.buttons: List[Button] = []
        self.info_lines: List[str] = []
        
        # Visual settings
        self.panel_color = (40, 40, 40)
        self.panel_alpha = 200
        self.button_color = (60, 60, 60)
        self.button_hover_color = (80, 80, 80)
        self.button_press_color = (100, 100, 100)
        self.text_color = (255, 255, 255)
        
        # Initialize default UI
        self._init_default_ui()
    
    def _init_default_ui(self):
        """Initialize default UI elements."""
        self.info_lines = [
            "【功能說明】",
            "H: 查看NPC對話歷史",
            "N: 選擇NPC",
            "T: 與NPC對話",
            "Space: 觸發AI思考",
            "Ctrl+S: 儲存世界",
            "ESC: 選單"
        ]
    
    def update(self, world_data: WorldDisplayData):
        """Update UI based on world data."""
        # Could update status indicators, etc.
        pass
    
    def render(self):
        """Render all UI elements."""
        self._render_info_panel()
        self._render_buttons()
    
    def _render_info_panel(self):
        """Render the info panel on the right side."""
        panel_width = 300
        panel_height = self.screen.get_height()
        panel_x = self.screen.get_width() - panel_width
        
        # Create semi-transparent surface
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(self.panel_alpha)
        panel_surface.fill(self.panel_color)
        self.screen.blit(panel_surface, (panel_x, 0))
        
        # Draw info text
        y = 20
        for line in self.info_lines:
            text_surface = self.info_font.render(line, True, self.text_color)
            self.screen.blit(text_surface, (panel_x + 10, y))
            y += self.info_font.get_linesize()
    
    def _render_buttons(self):
        """Render all buttons."""
        for button in self.buttons:
            # Determine button color
            if button.pressed:
                color = self.button_press_color
            elif button.hovered:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            # Draw button
            pygame.draw.rect(self.screen, color, button.rect)
            pygame.draw.rect(self.screen, self.text_color, button.rect, 2)
            
            # Draw button text
            text_surface = self.button_font.render(button.text, True, self.text_color)
            text_rect = text_surface.get_rect()
            text_rect.center = button.rect.center
            self.screen.blit(text_surface, text_rect)
    
    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """
        Handle mouse click.
        
        Args:
            pos: Mouse position
            
        Returns:
            True if a UI element was clicked
        """
        for button in self.buttons:
            if button.rect.collidepoint(pos):
                button.callback()
                return True
        return False
    
    def update_hover(self, pos: Tuple[int, int]):
        """Update hover states based on mouse position."""
        for button in self.buttons:
            button.hovered = button.rect.collidepoint(pos)